import React, { useState, useEffect, useRef, useCallback } from 'react';
import './SignalChart.css';

// Types
interface CandleData {
  timestamp: number;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
  datetime: string;
}

interface SignalLevel {
  price: number;
  level_type: 'entry' | 'stop_loss' | 'take_profit';
  strategy: string;
  confidence: number;
  reason: string;
}

interface ChartData {
  symbol: string;
  timeframe: string;
  candles: CandleData[];
  signals: SignalLevel[];
  current_price: number;
  recommendation?: {
    action: string;
    confidence: number;
    entry_range: { min: number; max: number };
    stop_loss: number;
    take_profit: number;
    current_price: number;
    primary_strategy: string;
    risk_level: string;
  };
  metadata: {
    total_candles: number;
    date_range: { start: string; end: string };
    timeframe_minutes: number;
    data_freshness_hours: number;
    signals_count: number;
  };
}

interface SignalChartProps {
  symbol?: string;
  timeframe?: string;
  limit?: number;
  showSignals?: boolean;
  showRecommendation?: boolean;
  onDataLoad?: (data: ChartData) => void;
  onError?: (error: string) => void;
  className?: string;
}

// Chart configuration
const CHART_CONFIG = {
  margin: { top: 20, right: 20, bottom: 60, left: 60 },
  candleWidth: 8,
  wickWidth: 1,
  signalLineWidth: 2,
  signalDotRadius: 4,
  colors: {
    bullish: '#26a69a',
    bearish: '#ef5350',
    entry: '#2196f3',
    stopLoss: '#f44336',
    takeProfit: '#4caf50',
    background: '#1e1e1e',
    grid: '#333333',
    text: '#ffffff'
  }
};

const SignalChart: React.FC<SignalChartProps> = ({
  symbol = 'BTCUSDT',
  timeframe = '1h',
  limit = 100,
  showSignals = true,
  showRecommendation = true,
  onDataLoad,
  onError,
  className = ''
}) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [chartData, setChartData] = useState<ChartData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [dimensions, setDimensions] = useState({ width: 800, height: 400 });
  const [hoveredCandle, setHoveredCandle] = useState<CandleData | null>(null);

  // Fetch chart data
  const fetchChartData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);

      const params = new URLSearchParams({
        limit: limit.toString(),
        include_signals: showSignals.toString(),
        include_recommendation: showRecommendation.toString()
      });

      const response = await fetch(`http://localhost:8000/api/chart/${symbol}/${timeframe}?${params}`);
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data: ChartData = await response.json();
      setChartData(data);
      onDataLoad?.(data);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to fetch chart data';
      setError(errorMessage);
      onError?.(errorMessage);
    } finally {
      setLoading(false);
    }
  }, [symbol, timeframe, limit, showSignals, showRecommendation, onDataLoad, onError]);

  // Load data on mount and when dependencies change
  useEffect(() => {
    fetchChartData();
  }, [fetchChartData]);

  // Handle window resize
  useEffect(() => {
    const handleResize = () => {
      if (canvasRef.current) {
        const rect = canvasRef.current.getBoundingClientRect();
        setDimensions({ width: rect.width, height: rect.height });
      }
    };

    window.addEventListener('resize', handleResize);
    handleResize();

    return () => window.removeEventListener('resize', handleResize);
  }, []);

  // Draw chart
  const drawChart = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas || !chartData) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const { width, height } = dimensions;
    const { margin } = CHART_CONFIG;
    
    // Set canvas size
    canvas.width = width;
    canvas.height = height;

    // Clear canvas
    ctx.fillStyle = CHART_CONFIG.colors.background;
    ctx.fillRect(0, 0, width, height);

    // Calculate chart area
    const chartWidth = width - margin.left - margin.right;
    const chartHeight = height - margin.top - margin.bottom;
    const chartX = margin.left;
    const chartY = margin.top;

    // Find price range
    const prices = chartData.candles.flatMap(c => [c.high, c.low]);
    const minPrice = Math.min(...prices);
    const maxPrice = Math.max(...prices);
    const priceRange = maxPrice - minPrice;
    const pricePadding = priceRange * 0.1;

    // Price to pixel conversion
    const priceToY = (price: number) => {
      return chartY + chartHeight - ((price - (minPrice - pricePadding)) / (priceRange + 2 * pricePadding)) * chartHeight;
    };

    // Time to pixel conversion
    const timeToX = (index: number) => {
      return chartX + (index / (chartData.candles.length - 1)) * chartWidth;
    };

    // Draw grid
    ctx.strokeStyle = CHART_CONFIG.colors.grid;
    ctx.lineWidth = 1;
    
    // Horizontal grid lines (price levels)
    for (let i = 0; i <= 5; i++) {
      const y = chartY + (i / 5) * chartHeight;
      ctx.beginPath();
      ctx.moveTo(chartX, y);
      ctx.lineTo(chartX + chartWidth, y);
      ctx.stroke();
    }

    // Vertical grid lines (time levels)
    for (let i = 0; i <= 5; i++) {
      const x = chartX + (i / 5) * chartWidth;
      ctx.beginPath();
      ctx.moveTo(x, chartY);
      ctx.lineTo(x, chartY + chartHeight);
      ctx.stroke();
    }

    // Draw candles
    chartData.candles.forEach((candle, index) => {
      const x = timeToX(index);
      const openY = priceToY(candle.open);
      const closeY = priceToY(candle.close);
      const highY = priceToY(candle.high);
      const lowY = priceToY(candle.low);

      const isBullish = candle.close >= candle.open;
      const color = isBullish ? CHART_CONFIG.colors.bullish : CHART_CONFIG.colors.bearish;

      // Draw wick
      ctx.strokeStyle = color;
      ctx.lineWidth = CHART_CONFIG.wickWidth;
      ctx.beginPath();
      ctx.moveTo(x, highY);
      ctx.lineTo(x, lowY);
      ctx.stroke();

      // Draw body
      const bodyHeight = Math.abs(closeY - openY);
      const bodyY = Math.min(openY, closeY);
      
      if (isBullish) {
        ctx.fillStyle = color;
        ctx.fillRect(x - CHART_CONFIG.candleWidth / 2, bodyY, CHART_CONFIG.candleWidth, bodyHeight);
      } else {
        ctx.strokeStyle = color;
        ctx.lineWidth = 2;
        ctx.strokeRect(x - CHART_CONFIG.candleWidth / 2, bodyY, CHART_CONFIG.candleWidth, bodyHeight);
      }
    });

    // Draw signals
    if (showSignals && chartData.signals.length > 0) {
      const signalsByType = {
        entry: chartData.signals.filter(s => s.level_type === 'entry'),
        stop_loss: chartData.signals.filter(s => s.level_type === 'stop_loss'),
        take_profit: chartData.signals.filter(s => s.level_type === 'take_profit')
      };

      // Draw entry signals
      signalsByType.entry.forEach(signal => {
        const y = priceToY(signal.price);
        ctx.fillStyle = CHART_CONFIG.colors.entry;
        ctx.beginPath();
        ctx.arc(chartX + chartWidth - 20, y, CHART_CONFIG.signalDotRadius, 0, 2 * Math.PI);
        ctx.fill();
      });

      // Draw stop loss signals
      signalsByType.stop_loss.forEach(signal => {
        const y = priceToY(signal.price);
        ctx.strokeStyle = CHART_CONFIG.colors.stopLoss;
        ctx.lineWidth = CHART_CONFIG.signalLineWidth;
        ctx.setLineDash([5, 5]);
        ctx.beginPath();
        ctx.moveTo(chartX, y);
        ctx.lineTo(chartX + chartWidth, y);
        ctx.stroke();
        ctx.setLineDash([]);
      });

      // Draw take profit signals
      signalsByType.take_profit.forEach(signal => {
        const y = priceToY(signal.price);
        ctx.strokeStyle = CHART_CONFIG.colors.takeProfit;
        ctx.lineWidth = CHART_CONFIG.signalLineWidth;
        ctx.setLineDash([3, 3]);
        ctx.beginPath();
        ctx.moveTo(chartX, y);
        ctx.lineTo(chartX + chartWidth, y);
        ctx.stroke();
        ctx.setLineDash([]);
      });
    }

    // Draw recommendation
    if (showRecommendation && chartData.recommendation) {
      const rec = chartData.recommendation;
      
      // Entry range
      const yA = priceToY(rec.entry_range.min);
      const yB = priceToY(rec.entry_range.max);
      const topY = Math.min(yA, yB);
      const heightY = Math.max(yA, yB) - topY;
      ctx.fillStyle = 'rgba(33, 150, 243, 0.2)';
      ctx.fillRect(chartX, topY, chartWidth, heightY);
      
      // Stop loss
      const stopLossY = priceToY(rec.stop_loss);
      ctx.strokeStyle = CHART_CONFIG.colors.stopLoss;
      ctx.lineWidth = 3;
      ctx.setLineDash([10, 5]);
      ctx.beginPath();
      ctx.moveTo(chartX, stopLossY);
      ctx.lineTo(chartX + chartWidth, stopLossY);
      ctx.stroke();
      ctx.setLineDash([]);
      
      // Take profit
      const takeProfitY = priceToY(rec.take_profit);
      ctx.strokeStyle = CHART_CONFIG.colors.takeProfit;
      ctx.lineWidth = 3;
      ctx.setLineDash([10, 5]);
      ctx.beginPath();
      ctx.moveTo(chartX, takeProfitY);
      ctx.lineTo(chartX + chartWidth, takeProfitY);
      ctx.stroke();
      ctx.setLineDash([]);
    }

    // Draw price labels
    ctx.fillStyle = CHART_CONFIG.colors.text;
    ctx.font = '12px Arial';
    ctx.textAlign = 'right';
    
    for (let i = 0; i <= 5; i++) {
      const price = minPrice - pricePadding + (i / 5) * (priceRange + 2 * pricePadding);
      const y = chartY + (i / 5) * chartHeight;
      ctx.fillText(price.toFixed(2), chartX - 10, y + 4);
    }

    // Draw time labels
    ctx.textAlign = 'center';
    ctx.fillStyle = CHART_CONFIG.colors.text;
    
    for (let i = 0; i <= 4; i++) {
      const index = Math.floor((i / 4) * (chartData.candles.length - 1));
      const candle = chartData.candles[index];
      const x = timeToX(index);
      const date = new Date(candle.datetime);
      const timeLabel = date.toLocaleTimeString('en-US', { 
        hour: '2-digit', 
        minute: '2-digit',
        hour12: false 
      });
      ctx.fillText(timeLabel, x, chartY + chartHeight + 20);
    }

    // Draw current price line
    const currentPriceY = priceToY(chartData.current_price);
    ctx.strokeStyle = '#ffeb3b';
    ctx.lineWidth = 2;
    ctx.setLineDash([2, 2]);
    ctx.beginPath();
    ctx.moveTo(chartX, currentPriceY);
    ctx.lineTo(chartX + chartWidth, currentPriceY);
    ctx.stroke();
    ctx.setLineDash([]);

    // Draw current price label
    ctx.fillStyle = '#ffeb3b';
    ctx.font = 'bold 14px Arial';
    ctx.textAlign = 'left';
    ctx.fillText(`$${chartData.current_price.toFixed(2)}`, chartX + 10, currentPriceY - 5);
  }, [chartData, dimensions, showSignals, showRecommendation]);

  // Redraw chart when data or dimensions change
  useEffect(() => {
    drawChart();
  }, [drawChart]);

  // Handle mouse events for hover effects
  const handleMouseMove = (event: React.MouseEvent<HTMLCanvasElement>) => {
    if (!chartData) return;

    const canvas = canvasRef.current;
    if (!canvas) return;

    const rect = canvas.getBoundingClientRect();
    const x = event.clientX - rect.left;
    const y = event.clientY - rect.top;

    const { margin } = CHART_CONFIG;
    const chartWidth = dimensions.width - margin.left - margin.right;
    const chartX = margin.left;

    if (x >= chartX && x <= chartX + chartWidth) {
      const index = Math.floor(((x - chartX) / chartWidth) * (chartData.candles.length - 1));
      const candle = chartData.candles[index];
      setHoveredCandle(candle);
    }
  };

  const handleMouseLeave = () => {
    setHoveredCandle(null);
  };

  if (loading) {
    return (
      <div className={`signal-chart signal-chart--loading ${className}`}>
        <div className="signal-chart__loading">
          <div className="signal-chart__spinner"></div>
          <p>Loading chart data...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className={`signal-chart signal-chart--error ${className}`}>
        <div className="signal-chart__error">
          <h3>Error Loading Chart</h3>
          <p>{error}</p>
          <button onClick={fetchChartData} className="signal-chart__retry-btn">
            Retry
          </button>
        </div>
      </div>
    );
  }

  if (!chartData) {
    return (
      <div className={`signal-chart signal-chart--no-data ${className}`}>
        <div className="signal-chart__no-data">
          <h3>No Data Available</h3>
          <p>No chart data available for {symbol} {timeframe}</p>
        </div>
      </div>
    );
  }

  return (
    <div className={`signal-chart ${className}`}>
      <div className="signal-chart__header">
        <div className="signal-chart__title">
          <h2>{chartData.symbol} - {chartData.timeframe}</h2>
          <span className="signal-chart__price">
            ${chartData.current_price.toFixed(2)}
          </span>
        </div>
        <div className="signal-chart__metadata">
          <span className="signal-chart__candles">
            {chartData.metadata.total_candles} candles
          </span>
          <span className="signal-chart__signals">
            {chartData.metadata.signals_count} signals
          </span>
          <span className="signal-chart__freshness">
            {chartData.metadata.data_freshness_hours < 1 
              ? 'Fresh' 
              : `${chartData.metadata.data_freshness_hours.toFixed(1)}h ago`
            }
          </span>
        </div>
      </div>

      <div className="signal-chart__canvas-container">
        <canvas
          ref={canvasRef}
          className="signal-chart__canvas"
          onMouseMove={handleMouseMove}
          onMouseLeave={handleMouseLeave}
        />
        
        {hoveredCandle && (
          <div className="signal-chart__tooltip">
            <div className="signal-chart__tooltip-content">
              <div className="signal-chart__tooltip-time">
                {new Date(hoveredCandle.datetime).toLocaleString()}
              </div>
              <div className="signal-chart__tooltip-ohlc">
                <div>O: ${hoveredCandle.open.toFixed(2)}</div>
                <div>H: ${hoveredCandle.high.toFixed(2)}</div>
                <div>L: ${hoveredCandle.low.toFixed(2)}</div>
                <div>C: ${hoveredCandle.close.toFixed(2)}</div>
              </div>
              <div className="signal-chart__tooltip-volume">
                Vol: {hoveredCandle.volume.toFixed(2)}
              </div>
            </div>
          </div>
        )}
      </div>

      {chartData.recommendation && (
        <div className="signal-chart__recommendation">
          <div className="signal-chart__recommendation-header">
            <h3>Current Recommendation</h3>
            <span className={`signal-chart__action signal-chart__action--${chartData.recommendation.action.toLowerCase()}`}>
              {chartData.recommendation.action}
            </span>
          </div>
          <div className="signal-chart__recommendation-details">
            <div className="signal-chart__recommendation-item">
              <span>Confidence:</span>
              <span>{(chartData.recommendation.confidence * 100).toFixed(1)}%</span>
            </div>
            <div className="signal-chart__recommendation-item">
              <span>Entry Range:</span>
              <span>${chartData.recommendation.entry_range.min.toFixed(2)} - ${chartData.recommendation.entry_range.max.toFixed(2)}</span>
            </div>
            <div className="signal-chart__recommendation-item">
              <span>Stop Loss:</span>
              <span>${chartData.recommendation.stop_loss.toFixed(2)}</span>
            </div>
            <div className="signal-chart__recommendation-item">
              <span>Take Profit:</span>
              <span>${chartData.recommendation.take_profit.toFixed(2)}</span>
            </div>
            <div className="signal-chart__recommendation-item">
              <span>Strategy:</span>
              <span>{chartData.recommendation.primary_strategy}</span>
            </div>
            <div className="signal-chart__recommendation-item">
              <span>Risk Level:</span>
              <span className={`signal-chart__risk signal-chart__risk--${chartData.recommendation.risk_level.toLowerCase()}`}>
                {chartData.recommendation.risk_level}
              </span>
            </div>
          </div>
        </div>
      )}

      <div className="signal-chart__legend">
        <div className="signal-chart__legend-item">
          <div className="signal-chart__legend-color signal-chart__legend-color--bullish"></div>
          <span>Bullish</span>
        </div>
        <div className="signal-chart__legend-item">
          <div className="signal-chart__legend-color signal-chart__legend-color--bearish"></div>
          <span>Bearish</span>
        </div>
        <div className="signal-chart__legend-item">
          <div className="signal-chart__legend-color signal-chart__legend-color--entry"></div>
          <span>Entry</span>
        </div>
        <div className="signal-chart__legend-item">
          <div className="signal-chart__legend-color signal-chart__legend-color--stop-loss"></div>
          <span>Stop Loss</span>
        </div>
        <div className="signal-chart__legend-item">
          <div className="signal-chart__legend-color signal-chart__legend-color--take-profit"></div>
          <span>Take Profit</span>
        </div>
      </div>
    </div>
  );
};

export default SignalChart;
