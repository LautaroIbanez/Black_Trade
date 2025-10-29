# Black Trade Frontend

React + Vite frontend for the Black Trade crypto trading recommendation system.

## Features

- **Dashboard**: Real-time BTC/USDT price display and trading recommendations
- **Multi-Timeframe Consensus**: Timeframe participation, tooltips, and regime marker
- **Risk Transparency**: RR, position size, risk %, normalized weights
- **Contribution Breakdown**: Expandable panel (entry, SL, TP contributions)
- **Trading Profiles**: Day Trading, Swing, Balanced, Long Term
- **Monitoring**: Recalibration logs dashboard
- **Responsive**: Works on desktop and mobile devices

## Installation

```bash
npm install
```

## Development

```bash
npm run dev
```

Frontend will run on http://localhost:5173

## Build

```bash
npm run build
```

Production build will be in the `dist/` folder.

## Components

- **Dashboard**: Trading recommendation, consensus, risk transparency
- **Strategies**: Performance metrics table with timeframe selector
- **MonitoringDashboard**: Recalibration logs and status

## API Integration

The frontend communicates with the backend API at `http://localhost:8000` by default. Change this in `src/services/api.js` or set the `VITE_API_URL` environment variable.

## Docs
See the docs folder for details:
- `docs/signals_and_methodology.md`
- `docs/report_examples.md`
- `docs/dashboards.md`
- `docs/stakeholder_reporting.md`




