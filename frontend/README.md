# Black Trade Frontend

React + Vite frontend for the Black Trade crypto trading recommendation system.

## Features

- **Dashboard**: Real-time BTC/USDT price display and trading recommendations
- **Strategy Performance**: Detailed metrics for all 5 strategies across multiple timeframes
- **Minimal UI**: Clean dark theme interface focused on essential information
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

- **Dashboard**: Main page with trading recommendation and price
- **Strategies**: Performance metrics table with timeframe selector

## API Integration

The frontend communicates with the backend API at `http://localhost:8000` by default. Change this in `src/services/api.js` or set the `VITE_API_URL` environment variable.


