import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import SignalChart from '../components/SignalChart';

// Mock fetch
global.fetch = jest.fn();

// Mock canvas context
HTMLCanvasElement.prototype.getContext = jest.fn(() => ({
  fillRect: jest.fn(),
  strokeRect: jest.fn(),
  beginPath: jest.fn(),
  moveTo: jest.fn(),
  lineTo: jest.fn(),
  arc: jest.fn(),
  fill: jest.fn(),
  stroke: jest.fn(),
  setLineDash: jest.fn(),
  fillText: jest.fn(),
  measureText: jest.fn(() => ({ width: 100 })),
  save: jest.fn(),
  restore: jest.fn(),
  translate: jest.fn(),
  scale: jest.fn(),
  rotate: jest.fn(),
  clearRect: jest.fn(),
  getImageData: jest.fn(),
  putImageData: jest.fn(),
  createImageData: jest.fn(),
  setTransform: jest.fn(),
  drawImage: jest.fn(),
  createLinearGradient: jest.fn(),
  createRadialGradient: jest.fn(),
  createPattern: jest.fn(),
  addColorStop: jest.fn(),
  globalAlpha: 1,
  globalCompositeOperation: 'source-over',
  strokeStyle: '#000000',
  fillStyle: '#000000',
  lineWidth: 1,
  lineCap: 'butt',
  lineJoin: 'miter',
  miterLimit: 10,
  shadowOffsetX: 0,
  shadowOffsetY: 0,
  shadowBlur: 0,
  shadowColor: 'rgba(0, 0, 0, 0)',
  font: '10px sans-serif',
  textAlign: 'start',
  textBaseline: 'alphabetic',
  direction: 'ltr',
  imageSmoothingEnabled: true,
  imageSmoothingQuality: 'low',
}));

// Mock getBoundingClientRect
Element.prototype.getBoundingClientRect = jest.fn(() => ({
  width: 800,
  height: 400,
  top: 0,
  left: 0,
  bottom: 400,
  right: 800,
  x: 0,
  y: 0,
}));

// Mock chart data
const mockChartData = {
  symbol: 'BTCUSDT',
  timeframe: '1h',
  candles: [
    {
      timestamp: 1698768000000,
      open: 50000.0,
      high: 51000.0,
      low: 49500.0,
      close: 50500.0,
      volume: 1234.56,
      datetime: '2023-10-31T00:00:00'
    },
    {
      timestamp: 1698771600000,
      open: 50500.0,
      high: 51500.0,
      low: 50000.0,
      close: 51000.0,
      volume: 1456.78,
      datetime: '2023-10-31T01:00:00'
    }
  ],
  signals: [
    {
      price: 50200.0,
      level_type: 'entry',
      strategy: 'EMA_RSI',
      confidence: 0.85,
      reason: 'EMA Crossover BUY'
    },
    {
      price: 49800.0,
      level_type: 'stop_loss',
      strategy: 'EMA_RSI',
      confidence: 0.85,
      reason: 'EMA_RSI SL'
    },
    {
      price: 51200.0,
      level_type: 'take_profit',
      strategy: 'EMA_RSI',
      confidence: 0.85,
      reason: 'EMA_RSI TP'
    }
  ],
  current_price: 50500.0,
  recommendation: {
    action: 'BUY',
    confidence: 0.75,
    entry_range: { min: 50200.0, max: 50800.0 },
    stop_loss: 49800.0,
    take_profit: 51200.0,
    current_price: 50500.0,
    primary_strategy: 'EMA_RSI',
    risk_level: 'MEDIUM'
  },
  metadata: {
    total_candles: 2,
    date_range: { start: '2023-10-31T00:00:00', end: '2023-10-31T01:00:00' },
    timeframe_minutes: 60,
    data_freshness_hours: 0.5,
    signals_count: 3
  }
};

describe('SignalChart', () => {
  beforeEach(() => {
    (fetch as jest.Mock).mockClear();
  });

  it('renders loading state initially', () => {
    (fetch as jest.Mock).mockImplementation(() => new Promise(() => {})); // Never resolves
    
    render(<SignalChart symbol="BTCUSDT" timeframe="1h" />);
    
    expect(screen.getByText('Loading chart data...')).toBeInTheDocument();
    expect(document.querySelector('.signal-chart__spinner')).toBeInTheDocument();
  });

  it('renders error state when fetch fails', async () => {
    (fetch as jest.Mock).mockRejectedValueOnce(new Error('Network error'));
    
    render(<SignalChart symbol="BTCUSDT" timeframe="1h" />);
    
    await waitFor(() => {
      expect(screen.getByText('Error Loading Chart')).toBeInTheDocument();
      expect(screen.getByText('Network error')).toBeInTheDocument();
      expect(screen.getByText('Retry')).toBeInTheDocument();
    });
  });

  it('renders no data state when no data available', async () => {
    (fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      json: async () => ({ candles: [], signals: [] })
    });
    
    render(<SignalChart symbol="BTCUSDT" timeframe="1h" />);
    
    await waitFor(() => {
      expect(screen.getByText('No Data Available')).toBeInTheDocument();
      expect(screen.getByText('No chart data available for BTCUSDT 1h')).toBeInTheDocument();
    });
  });

  it('renders chart with data successfully', async () => {
    (fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      json: async () => mockChartData
    });
    
    render(<SignalChart symbol="BTCUSDT" timeframe="1h" />);
    
    await waitFor(() => {
      expect(screen.getByText('BTCUSDT - 1h')).toBeInTheDocument();
      expect(screen.getByText('$50,500.00')).toBeInTheDocument();
      expect(screen.getByText('2 candles')).toBeInTheDocument();
      expect(screen.getByText('3 signals')).toBeInTheDocument();
      expect(screen.getByText('Fresh')).toBeInTheDocument();
    });
  });

  it('displays recommendation when available', async () => {
    (fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      json: async () => mockChartData
    });
    
    render(<SignalChart symbol="BTCUSDT" timeframe="1h" showRecommendation={true} />);
    
    await waitFor(() => {
      expect(screen.getByText('Current Recommendation')).toBeInTheDocument();
      expect(screen.getByText('BUY')).toBeInTheDocument();
      expect(screen.getByText('75.0%')).toBeInTheDocument();
      expect(screen.getByText('$50,200.00 - $50,800.00')).toBeInTheDocument();
      expect(screen.getByText('$49,800.00')).toBeInTheDocument();
      expect(screen.getByText('$51,200.00')).toBeInTheDocument();
      expect(screen.getByText('EMA_RSI')).toBeInTheDocument();
      expect(screen.getByText('MEDIUM')).toBeInTheDocument();
    });
  });

  it('hides recommendation when showRecommendation is false', async () => {
    (fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      json: async () => mockChartData
    });
    
    render(<SignalChart symbol="BTCUSDT" timeframe="1h" showRecommendation={false} />);
    
    await waitFor(() => {
      expect(screen.queryByText('Current Recommendation')).not.toBeInTheDocument();
    });
  });

  it('displays legend with correct items', async () => {
    (fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      json: async () => mockChartData
    });
    
    render(<SignalChart symbol="BTCUSDT" timeframe="1h" />);
    
    await waitFor(() => {
      expect(screen.getByText('Bullish')).toBeInTheDocument();
      expect(screen.getByText('Bearish')).toBeInTheDocument();
      expect(screen.getByText('Entry')).toBeInTheDocument();
      expect(screen.getByText('Stop Loss')).toBeInTheDocument();
      expect(screen.getByText('Take Profit')).toBeInTheDocument();
    });
  });

  it('handles retry button click', async () => {
    (fetch as jest.Mock)
      .mockRejectedValueOnce(new Error('Network error'))
      .mockResolvedValueOnce({
        ok: true,
        json: async () => mockChartData
      });
    
    render(<SignalChart symbol="BTCUSDT" timeframe="1h" />);
    
    await waitFor(() => {
      expect(screen.getByText('Error Loading Chart')).toBeInTheDocument();
    });
    
    fireEvent.click(screen.getByText('Retry'));
    
    await waitFor(() => {
      expect(screen.getByText('BTCUSDT - 1h')).toBeInTheDocument();
    });
  });

  it('calls onDataLoad callback when data loads', async () => {
    const onDataLoad = jest.fn();
    (fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      json: async () => mockChartData
    });
    
    render(<SignalChart symbol="BTCUSDT" timeframe="1h" onDataLoad={onDataLoad} />);
    
    await waitFor(() => {
      expect(onDataLoad).toHaveBeenCalledWith(mockChartData);
    });
  });

  it('calls onError callback when error occurs', async () => {
    const onError = jest.fn();
    (fetch as jest.Mock).mockRejectedValueOnce(new Error('Network error'));
    
    render(<SignalChart symbol="BTCUSDT" timeframe="1h" onError={onError} />);
    
    await waitFor(() => {
      expect(onError).toHaveBeenCalledWith('Network error');
    });
  });

  it('handles mouse hover events', async () => {
    (fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      json: async () => mockChartData
    });
    
    render(<SignalChart symbol="BTCUSDT" timeframe="1h" />);
    
    await waitFor(() => {
      expect(screen.getByText('BTCUSDT - 1h')).toBeInTheDocument();
    });
    
    const canvas = screen.getByRole('img', { hidden: true }) || document.querySelector('canvas');
    if (canvas) {
      fireEvent.mouseMove(canvas, { clientX: 100, clientY: 100 });
      // Tooltip should appear (implementation depends on canvas positioning)
    }
  });

  it('handles mouse leave events', async () => {
    (fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      json: async () => mockChartData
    });
    
    render(<SignalChart symbol="BTCUSDT" timeframe="1h" />);
    
    await waitFor(() => {
      expect(screen.getByText('BTCUSDT - 1h')).toBeInTheDocument();
    });
    
    const canvas = screen.getByRole('img', { hidden: true }) || document.querySelector('canvas');
    if (canvas) {
      fireEvent.mouseLeave(canvas);
      // Tooltip should disappear
    }
  });

  it('updates when props change', async () => {
    const { rerender } = render(<SignalChart symbol="BTCUSDT" timeframe="1h" />);
    
    (fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      json: async () => mockChartData
    });
    
    await waitFor(() => {
      expect(screen.getByText('BTCUSDT - 1h')).toBeInTheDocument();
    });
    
    // Change timeframe
    (fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      json: async () => ({ ...mockChartData, timeframe: '4h' })
    });
    
    rerender(<SignalChart symbol="BTCUSDT" timeframe="4h" />);
    
    await waitFor(() => {
      expect(screen.getByText('BTCUSDT - 4h')).toBeInTheDocument();
    });
  });

  it('applies custom className', async () => {
    (fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      json: async () => mockChartData
    });
    
    render(<SignalChart symbol="BTCUSDT" timeframe="1h" className="custom-chart" />);
    
    await waitFor(() => {
      const chartElement = document.querySelector('.signal-chart.custom-chart');
      expect(chartElement).toBeInTheDocument();
    });
  });

  it('handles different symbol and timeframe combinations', async () => {
    (fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      json: async () => ({ ...mockChartData, symbol: 'ETHUSDT', timeframe: '4h' })
    });
    
    render(<SignalChart symbol="ETHUSDT" timeframe="4h" />);
    
    await waitFor(() => {
      expect(screen.getByText('ETHUSDT - 4h')).toBeInTheDocument();
    });
  });

  it('displays stale data warning when data is old', async () => {
    const staleData = {
      ...mockChartData,
      metadata: {
        ...mockChartData.metadata,
        data_freshness_hours: 5.5
      }
    };
    
    (fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      json: async () => staleData
    });
    
    render(<SignalChart symbol="BTCUSDT" timeframe="1h" />);
    
    await waitFor(() => {
      expect(screen.getByText('5.5h ago')).toBeInTheDocument();
    });
  });

  it('handles empty signals array', async () => {
    const dataWithoutSignals = {
      ...mockChartData,
      signals: []
    };
    
    (fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      json: async () => dataWithoutSignals
    });
    
    render(<SignalChart symbol="BTCUSDT" timeframe="1h" />);
    
    await waitFor(() => {
      expect(screen.getByText('0 signals')).toBeInTheDocument();
    });
  });

  it('handles missing recommendation', async () => {
    const dataWithoutRecommendation = {
      ...mockChartData,
      recommendation: null
    };
    
    (fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      json: async () => dataWithoutRecommendation
    });
    
    render(<SignalChart symbol="BTCUSDT" timeframe="1h" showRecommendation={true} />);
    
    await waitFor(() => {
      expect(screen.queryByText('Current Recommendation')).not.toBeInTheDocument();
    });
  });
});

// Snapshot tests
describe('SignalChart Snapshots', () => {
  it('matches loading state snapshot', () => {
    (fetch as jest.Mock).mockImplementation(() => new Promise(() => {}));
    
    const { container } = render(<SignalChart symbol="BTCUSDT" timeframe="1h" />);
    expect(container.firstChild).toMatchSnapshot();
  });

  it('matches error state snapshot', async () => {
    (fetch as jest.Mock).mockRejectedValueOnce(new Error('Network error'));
    
    const { container } = render(<SignalChart symbol="BTCUSDT" timeframe="1h" />);
    
    await waitFor(() => {
      expect(screen.getByText('Error Loading Chart')).toBeInTheDocument();
    });
    
    expect(container.firstChild).toMatchSnapshot();
  });

  it('matches chart with data snapshot', async () => {
    (fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      json: async () => mockChartData
    });
    
    const { container } = render(<SignalChart symbol="BTCUSDT" timeframe="1h" />);
    
    await waitFor(() => {
      expect(screen.getByText('BTCUSDT - 1h')).toBeInTheDocument();
    });
    
    expect(container.firstChild).toMatchSnapshot();
  });
});
