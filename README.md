# Black Trade - Advanced Crypto Trading System

Sistema avanzado de trading algorítmico para criptomonedas con análisis multi-timeframe, backtesting robusto, recomendaciones en tiempo real y visualizaciones interactivas.

## Descripción

Black Trade es una plataforma completa de trading algorítmico que combina análisis técnico avanzado, backtesting multi-timeframe, gestión de riesgo adaptativa y visualizaciones interactivas para generar recomendaciones de trading automatizadas y confiables.

### Arquitectura del Sistema

El sistema está construido con una arquitectura modular y escalable que incluye:

#### 🏗️ **Backend (FastAPI)**
- **Motor de Estrategias**: Framework extensible con 5+ estrategias de trading
- **Sistema de Backtesting**: Motor robusto con métricas avanzadas y gestión de costos
- **Servicio de Recomendaciones**: Agregación inteligente de señales multi-timeframe
- **API de Gráficos**: Endpoints para visualización de datos y señales
- **Gobernanza de Datos**: Sincronización confiable y validación de calidad
- **Gestión de Riesgo**: Cálculo dinámico de SL/TP y niveles de soporte/resistencia

#### 🎨 **Frontend (React + Vite)**
- **Dashboard Interactivo**: Interfaz moderna con gráficos de velas en tiempo real
- **Visualizaciones Avanzadas**: Overlays de señales, niveles de entrada y gestión de riesgo
- **Selector de Timeframes**: Navegación fluida entre diferentes marcos temporales
- **Recomendaciones Visuales**: Presentación clara de señales y niveles de confianza
- **Diseño Responsive**: Optimizado para desktop, tablet y móvil

#### 📊 **Motor de Datos**
- **Sincronización Robusta**: Paginación automática y completado de huecos
- **Validación de Calidad**: Verificación de continuidad temporal y frescura
- **Múltiples Fuentes**: Integración con Binance API y fuentes locales
- **Monitoreo Continuo**: Logs estructurados y métricas de calidad

### Características Principales

#### 🚀 **Estrategias de Trading Avanzadas**
- **EMA + RSI**: Crossover de medias móviles con indicador de momentum
- **Momentum**: Análisis de fuerza del movimiento con MACD y RSI
- **Breakout**: Detección de rupturas con Bandas de Bollinger
- **Mean Reversion**: Estrategias de reversión a la media
- **Ichimoku**: Análisis completo con nube de Ichimoku y ADX

#### 📈 **Backtesting Robusto**
- **Métricas Avanzadas**: Win Rate, Max Drawdown, Profit Factor, Sharpe Ratio
- **Gestión de Costos**: Comisiones y slippage realistas
- **Cierre de Posiciones**: Garantía de cierre al final del backtest
- **Ranking Dinámico**: Sistema de puntuación basado en rendimiento
- **Validación Temporal**: Verificación de continuidad de datos

#### 🎯 **Recomendaciones en Tiempo Real**
- **Señales Multi-Timeframe**: Análisis simultáneo de 1h, 4h, 1d, 1w
- **Agregación Inteligente**: Ponderación por confianza y consistencia
- **Niveles Dinámicos**: Cálculo adaptativo de entrada, SL y TP
- **Gestión de Riesgo**: Niveles de soporte/resistencia y volatilidad
- **Confianza Cuantificada**: Puntuación de 0-100% para cada recomendación

#### 📊 **Visualizaciones Interactivas**
- **Gráficos de Velas**: Renderizado Canvas de alto rendimiento
- **Overlays de Señales**: Niveles de entrada, stop loss y take profit
- **Recomendaciones Visuales**: Presentación clara de análisis
- **Tooltips Informativos**: Datos OHLCV y señales al hacer hover
- **Diseño Responsive**: Adaptable a diferentes dispositivos

#### 🛡️ **Gobernanza de Datos**
- **Sincronización Confiable**: Paginación automática para datasets grandes
- **Detección de Huecos**: Identificación y completado automático
- **Validación de Calidad**: Verificación de continuidad y consistencia
- **Monitoreo Continuo**: Logs estructurados y alertas automáticas
- **Auditoría Completa**: Trazabilidad de todas las operaciones

#### ⚙️ **Gestión de Riesgo Adaptativa**
- **SL/TP Dinámicos**: Cálculo basado en ATR y volatilidad
- **Soporte/Resistencia**: Detección automática de niveles clave
- **Análisis de Volatilidad**: Ajuste de niveles según condiciones del mercado
- **Múltiples Estrategias**: Agregación de niveles de diferentes enfoques
- **Validación de Niveles**: Verificación contra reglas de riesgo predefinidas

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

### 🚀 **Inicio Rápido**

1. **Acceder a la aplicación**: http://localhost:5173
2. **Actualizar datos**: Click en "Refresh" para sincronizar datos y generar recomendación
3. **Explorar gráficos**: Usar el selector de timeframes para analizar diferentes marcos temporales
4. **Ver recomendaciones**: Revisar señales, niveles de entrada y gestión de riesgo
5. **Monitorear estrategias**: Ver métricas detalladas y rendimiento histórico

### 📊 **Dashboard Principal**

- **Gráfico Interactivo**: Velas con overlays de señales y niveles
- **Selector de Timeframes**: 1h, 4h, 1d, 1w
- **Recomendación Actual**: Acción, confianza, niveles de riesgo
- **Información de Estrategia**: Estrategia principal y nivel de riesgo

### 🔧 **API Endpoints**

```bash
# Obtener recomendación actual
GET /recommendation

# Actualizar datos y ejecutar backtests
POST /refresh

# Datos de gráfico con señales
GET /api/chart/{symbol}/{timeframe}

# Información de estrategias
GET /strategies/info

# Estado del sistema
GET /api/chart/status
```

## QA y Transparencia

- La especificación de API en `docs/api/recommendation.md` refleja el esquema actual, incluyendo `position_size_usd`, `position_size_pct` y `signal_consensus` acotado a 1.0.
- Ejecutar QA y publicar estado:

```bash
python -m pytest -q && python qa/generate_status.py
```

- Revisa `docs/qa/status.md` para un resumen de resultados y `docs/qa/overview.md` para el alcance de QA.
- Usa `docs/qa/checklist.md` antes de cada release para auditar normalización, sizing y métricas de riesgo.

## Estructura del Proyecto

```
Black_Trade/
├── backend/                    # API FastAPI
│   ├── api/routes/            # Endpoints de API
│   │   ├── chart.py          # API de gráficos
│   │   └── recommendation.py # API de recomendaciones
│   ├── services/              # Servicios de negocio
│   │   ├── strategy_registry.py    # Registro de estrategias
│   │   ├── recommendation_service.py # Servicio de recomendaciones
│   │   └── risk_management.py      # Gestión de riesgo
│   ├── schemas/               # Modelos Pydantic
│   ├── config/                # Configuraciones
│   ├── cron/                  # Jobs programados
│   └── logs/                  # Logs del sistema
├── frontend/                   # UI React + Vite
│   ├── src/components/        # Componentes React
│   │   ├── SignalChart.tsx   # Gráfico de velas
│   │   ├── Dashboard.jsx     # Dashboard principal
│   │   └── Strategies.jsx    # Vista de estrategias
│   ├── src/services/          # Servicios de API
│   ├── src/__tests__/         # Tests del frontend
│   └── public/                # Assets estáticos
├── data/                      # Motor de datos
│   ├── binance_client.py     # Cliente de Binance
│   ├── sync_service.py       # Sincronización de datos
│   └── ohlcv/                # Datos históricos
├── strategies/                # Estrategias de trading
│   ├── strategy_base.py      # Clase base
│   ├── ema_rsi_strategy.py   # EMA + RSI
│   ├── momentum_strategy.py  # Momentum
│   ├── breakout_strategy.py  # Breakout
│   ├── mean_reversion_strategy.py # Mean Reversion
│   └── ichimoku_strategy.py  # Ichimoku
├── backtest/                  # Motor de backtesting
│   ├── engine.py             # Motor principal
│   ├── data_loader.py        # Cargador de datos
│   ├── indicators/           # Indicadores técnicos
│   └── tests/                # Tests de backtesting
├── recommendation/            # Sistema de recomendaciones
│   └── aggregator.py         # Agregador de señales
├── qa/                       # Scripts de QA
├── docs/                     # Documentación
│   ├── api/                  # Documentación de API
│   ├── strategies.md         # Guía de estrategias
│   ├── data_governance.md    # Gobernanza de datos
│   ├── visualization.md      # Sistema de visualización
│   └── how_to_*.md          # Guías paso a paso
└── requirements.txt           # Dependencias Python
```

## Arquitectura Técnica

### 🔄 **Flujo de Datos**

1. **Adquisición**: Binance API → SyncService → CSV Files
2. **Validación**: DataLoader → Continuity Check → Quality Metrics
3. **Análisis**: Strategies → Signal Generation → Risk Calculation
4. **Agregación**: RecommendationService → Multi-timeframe Analysis
5. **Visualización**: Chart API → SignalChart → Interactive Dashboard

### 🏗️ **Componentes Principales**

#### **Backend Services**
- **StrategyRegistry**: Gestión dinámica de estrategias
- **RecommendationService**: Agregación de señales
- **RiskManagementService**: Cálculo de niveles de riesgo
- **SyncService**: Sincronización y validación de datos
- **DataLoader**: Carga y validación de datos

#### **Frontend Components**
- **SignalChart**: Gráfico de velas interactivo
- **Dashboard**: Vista principal con recomendaciones
- **Strategies**: Vista de métricas de estrategias
- **API Services**: Comunicación con backend

### 📊 **Métricas y Monitoreo**

- **Logs Estructurados**: JSON logs para análisis
- **Métricas de Calidad**: Frescura, completitud, consistencia
- **Alertas Automáticas**: Notificaciones de problemas
- **Auditoría Completa**: Trazabilidad de operaciones

## Licencia

MIT
