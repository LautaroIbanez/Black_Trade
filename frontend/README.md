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

### Contract and Optional Fields
The `GET /recommendation` response includes (subset):
- `action` (string), `confidence` (number 0–1), `entry_range` ({min,max}), `stop_loss` (number), `take_profit` (number), `current_price` (number)
- `risk_reward_ratio` (number), `risk_percentage` (number), `normalized_weights_sum` (number)
- `position_size_usd` (number), `position_size_pct` (number)
- `primary_strategy` (string), `supporting_strategies` (array), `strategy_details` (array)

Optional/nullable fields that the UI guards with placeholders:
- `entry_range`, `stop_loss`, `take_profit`, `current_price`, `risk_reward_ratio`, `risk_percentage`, `normalized_weights_sum`, `position_size_usd`, `position_size_pct`

UI behavior:
- When optional fields are missing or null, the UI displays `N/A` instead of failing.

## Docs
See the docs folder for details:
- `docs/signals_and_methodology.md`
- `docs/report_examples.md`
- `docs/dashboards.md`
- `docs/stakeholder_reporting.md`




