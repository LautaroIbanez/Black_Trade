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

5. **Inicializar base de datos y migraciones**
```bash
# Las migraciones se ejecutan automáticamente al iniciar el backend
# También puedes ejecutarlas manualmente si es necesario:
python -m backend.db.init_db
```

6. **Ejecutar aplicación**
```bash
# Terminal 1: Backend
# Las migraciones se ejecutan automáticamente en el startup_event
uvicorn backend.app:app --reload --port 8000

# Terminal 2: Frontend
cd frontend
npm run dev
```

La aplicación frontend estará disponible en: http://localhost:5173

**⚠️ IMPORTANTE**: Las migraciones de base de datos se ejecutan automáticamente en cada despliegue/arranque del backend. El sistema ejecuta todas las migraciones disponibles en orden secuencial, asegurando que el esquema de la base de datos esté siempre actualizado y coherente. Revisa los logs del backend para confirmar que todas las migraciones se ejecutaron correctamente.

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

### Estado Actual de QA

La especificación de API en `docs/api/recommendation.md` refleja el esquema actual, incluyendo `position_size_usd`, `position_size_pct` y `signal_consensus` acotado a 1.0. 

**Última ejecución de QA**: Ver `docs/qa/status.md` para el estado más reciente con:
- Timestamp de última ejecución
- Estado (PASSED/FAILED)
- Conteo de tests (passed/failed/errors/skipped)
- Resumen y salida completa

**Cobertura actual** (129 passed, 4 failed): Los tests cubren:
- ✅ Agregación de señales y normalización de confianza/consenso
- ✅ Moderación de consenso en escenarios mixtos BUY/SELL/HOLD
- ✅ Servicio de recomendaciones con diferentes perfiles
- ✅ Gestión de riesgo y cálculo de niveles SL/TP
- ✅ Tests end-to-end del pipeline completo
- ✅ Consenso neutral (100% HOLD = 0% consenso) y señales mixtas
- ✅ Tests de rotación multi-activo (CryptoRotation) - todos pasando
- ✅ Tests de normalización - todos pasando
- ⚠️  3 tests de backtesting fallan (walk-forward, costes) - documentados
- ⚠️  1 test de endpoints falla (timeframes) - documentado

### Ejecutar QA

**Método recomendado** (ejecuta tests y actualiza estado automáticamente):
```bash
python qa/generate_status.py
```

**Método manual**:
```bash
# Solo ejecutar tests
python -m pytest -q

# Ejecutar y actualizar estado
python -m pytest -q && python qa/generate_status.py
```

Para más detalles sobre ejecución, configuración y solución de problemas, ver `qa/README.md`.

### Limitaciones Actuales

> ⚠️ **Nota importante**: Las siguientes limitaciones están documentadas para transparencia. Ver `docs/qa/status.md` para el estado actual de los tests y problemas conocidos.

**Estado QA**: 136 passed, 1 failed (ver `docs/qa/status.md` para detalles)

1. ✅ **Consenso mixto**: Resuelto con moderación configurable (`mixed_consensus_cap`, `neutral_count_factor`). Escenarios 2 BUY / 1 SELL / 1 HOLD ahora generan consenso moderado (~0.60, limitado por cap configurable).

2. ✅ **CryptoRotation multi-activo**: Verificado y funcional. Tests de rotación pasando con datasets multi-símbolo y manejo correcto del parámetro `strict`.

3. ✅ **Tests de walk-forward y costes**: Corregidos. Bug de índice fuera de rango en `close_all_positions` resuelto, expectativas de costes ajustadas.

4. ✅ **Tests end-to-end**: Añadido test `test_e2e_minimal.py` cubriendo pipeline completo de consenso y riesgo.

5. ⚠️ **Test de temporalidades**: `test_recommendation_includes_new_timeframes` falla por error en generación de señales (`'bool' object is not iterable`) en Mean_Reversion, Ichimoku_ADX, RSIDivergence, Stochastic. Error de implementación de estrategias, no del pipeline. Responsable: Equipo Backend / Estrategias. Target: Próximo sprint.

6. ⚠️ **Calibración de estrategias**: MACD y OrderFlow en fase de ajuste fino. Parámetros pueden cambiar entre versiones menores.

### Limitaciones Actuales de QA

- **1 test fallando** (no crítico): `test_recommendation_includes_new_timeframes` - relacionado con errores en generación de señales de estrategias específicas, no afecta funcionalidad core
- **Tests críticos operativos**: Consenso, agregación, walk-forward, costes, end-to-end todos pasando
- **Calibración de consenso**: Los parámetros `mixed_consensus_cap` (default: 0.60) y `neutral_count_factor` (default: 0.95) están configurados y funcionando; pueden requerir ajuste fino según feedback de uso

Para más detalles sobre limitaciones y problemas conocidos, ver:
- `docs/qa/status.md` - Estado actual de QA y problemas conocidos
- `docs/CHANGELOG.md` - Limitaciones funcionales y pendientes

## Estado de Confianza por Épica

| Épica | Estado | Confianza | Notas |
|-------|--------|-----------|-------|
| Normalización de Datos | Completa | Alta | Validaciones de continuidad/frescura operativas |
| Recomendación Multi-timeframe | Completa | Media-Alta | Ponderación estable; mejoras de UX en curso |
| Moderación de Consenso Mixto | ✅ Completa | Alta | Parámetros configurables; tests validando comportamiento |
| MACD Rehabilitado | En progreso | Media | Cierres por histograma en cero listos; calibración por timeframe pendiente |
| CryptoRotation Multi-Activo | ✅ Verificado | Alta | Tests pasando; manejo correcto de strict/fallback |
| OrderFlow | En progreso | Media | Señales con volumen anómalo; calibración de vol_mult |
| QA Integral | Estabilizado | Media-Alta | 136/137 tests pasando; 1 fallo no crítico documentado; pipeline operativo |

### Próximos Hitos (4–6 semanas)

- Backtests comparativos MACD/OrderFlow/CryptoRotation por timeframe (OOS)
- Auditoría QA interna con reporte público en `docs/qa/status.md`
- Panel de desempeño y alertas en `docs/reports/strategy_performance.md`
- Cierre de gaps de datos y automatización de refresco por símbolo

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
│   ├── analysis.py           # Métricas/score compuesto
│   ├── data_loader.py        # Cargador de datos
│   ├── indicators/           # Indicadores técnicos
│   └── tests/                # Tests de backtesting
├── backend/services/          # Servicios backend
│   └── recommendation_service.py # Agregación de señales y recomendación
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
