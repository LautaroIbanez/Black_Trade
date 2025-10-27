# Black Trade - Crypto Trading Recommendation System

Sistema inteligente de recomendaciones de trading para BTC/USDT basado en análisis multi-timeframe y estrategias algorítmicas.

## Descripción

Black Trade combina análisis técnico avanzado, backtesting multi-timeframe y un sistema de ranking dinámico para generar recomendaciones de trading automatizadas.

### Características Principales

- **Adquisición de datos en tiempo real**: Sincronización con Binance API para velas OHLCV (1h, 4h, 1d, 1w)
- **Motor de estrategias**: Framework modular con ≥5 estrategias de trading rentables
- **Backtesting avanzado**: Cálculo de métricas clave (Win Rate, Max Drawdown, PnL, Profit Factor)
- **Sistema de recomendaciones**: Agregación ponderada de señales con nivel de confianza
- **UI minimalista**: Interfaz web moderna con gráficos en vivo y métricas detalladas
- **Despliegue containerizado**: Docker Compose para entorno reproducible

## Instalación

### Requisitos

- Python 3.10+
- Node.js 18+ (para frontend)
- Docker y Docker Compose (opcional)

### Setup Manual

1. **Clonar repositorio**
```bash
git clone <repo-url>
cd Black_Trade
```

2. **Configurar credenciales**
```bash
cp .env.example .env
# Editar .env con tus credenciales de Binance
```

3. **Instalar dependencias backend**
```bash
pip install -r requirements.txt
```

4. **Instalar dependencias frontend**
```bash
cd frontend
npm install
```

5. **Ejecutar aplicación**
```bash
# Terminal 1: Backend
uvicorn backend.app:app --reload --port 8000

# Terminal 2: Frontend
cd frontend
npm run dev
```

La aplicación frontend estará disponible en: http://localhost:5173

### Setup con Docker

```bash
docker-compose up --build
```

## Uso

1. Acceder a la aplicación: http://localhost:5173
2. Click en "Refresh" para actualizar datos y generar recomendación
3. Ver métricas detalladas en pestaña "Estrategias"

## Estructura del Proyecto

```
Black_Trade/
├── backend/          # API FastAPI
├── frontend/         # UI React + Vite
├── data/            # Módulos de datos
├── strategies/      # Estrategias de trading
├── backtest/        # Motor de backtesting
├── recommendation/  # Sistema de recomendaciones
├── qa/             # Scripts de QA
└── docs/           # Documentación
```

## Licencia

MIT
