# CryptoRotation: Estrategia Multi-Activo de Rotación

## Resumen

CryptoRotation es una estrategia genuinamente multi-activo que selecciona ganadores y perdedores relativos dentro de un universo de criptomonedas, generando señales BUY para símbolos top-ranked y SELL para símbolos bottom-ranked basado en fuerza relativa, retornos o ratios Sharpe.

## Características Principales

### Multi-Activo Real
- **Carga múltiples símbolos** del universo simultáneamente
- **Alinea timestamps** entre todos los símbolos para comparación justa
- **Rankea símbolos** por múltiples métricas (fuerza relativa, retornos, Sharpe)
- **Genera señales relativas** - solo señala cuando hay divergencia suficiente entre símbolos

### Métodos de Ranking

1. **`strength`** (default): Fuerza relativa vs EMA
   - Calcula `(close / EMA - 1)` para cada símbolo
   - Rankea por valor más reciente
   
2. **`returns`**: Retornos sobre períodos
   - Calcula retornos porcentuales sobre N períodos
   - Rankea por retorno más reciente
   
3. **`sharpe`**: Ratio de Sharpe (return / volatility)
   - Calcula retorno medio y volatilidad (std de retornos)
   - Rankea por ratio Sharpe

### Lógica de Señales

- **BUY (signal = 1)**: Cuando el símbolo actual está en el **top N** del ranking y la divergencia entre top/bottom es ≥ `min_divergence`
- **SELL (signal = -1)**: Cuando el símbolo actual está en el **bottom N** del ranking y la divergencia es suficiente
- **HOLD (signal = 0)**: Cuando no hay divergencia suficiente o el símbolo está en el medio

### Rebalanceo

La estrategia re-evalúa rankings cada `rebalance_periods` períodos:
- Cierra posiciones si el símbolo sale de top/bottom N
- Re-evalúa si debe mantener posición basado en nuevas señales
- Permite rotación activa entre símbolos

## Parámetros de Configuración

Ver `backend/services/strategy_registry.py` y `backend/config/strategies.json` para valores por defecto:

```python
{
    "lookback": 50,              # Período EMA o ventana para cálculos
    "universe": [                # Lista de símbolos en el universo
        "BTCUSDT", 
        "ETHUSDT", 
        "BNBUSDT", 
        "SOLUSDT", 
        "ADAUSDT"
    ],
    "ranking_method": "strength", # "strength" | "returns" | "sharpe"
    "min_divergence": 0.02,      # Divergencia mínima requerida (2%)
    "top_n": 1,                  # Número de símbolos top para BUY
    "bottom_n": 1,               # Número de símbolos bottom para SELL
    "rebalance_periods": 5       # Re-evaluar rankings cada N períodos
}
```

### Variables de Entorno

- `ROTATION_UNIVERSE`: Símbolos separados por comas (override del universo por defecto)
  ```bash
  export ROTATION_UNIVERSE="BTCUSDT,ETHUSDT,BNBUSDT,SOLUSDT"
  ```

## Requisitos de Datos

### Símbolos Soportados (Por Defecto)

La estrategia soporta los siguientes símbolos por defecto:

- **BTCUSDT**: Bitcoin/USDT
- **ETHUSDT**: Ethereum/USDT
- **BNBUSDT**: Binance Coin/USDT
- **SOLUSDT**: Solana/USDT
- **ADAUSDT**: Cardano/USDT

### Personalización del Universo

El universo puede personalizarse mediante:

1. **Variable de entorno `ROTATION_UNIVERSE`**:
   ```bash
   export ROTATION_UNIVERSE="BTCUSDT,ETHUSDT,BNBUSDT,XRPUSDT"
   ```

2. **Configuración en `backend/config/strategies.json`**:
   ```json
   {
     "crypto_rotation": {
       "universe": ["BTCUSDT", "ETHUSDT", "BNBUSDT"]
     }
   }
   ```

3. **Parámetro en código**:
   ```python
   strategy = CryptoRotationStrategy(universe=["BTCUSDT", "ETHUSDT"])
   ```

### Estructura de Archivos

Los datos deben estar en formato CSV en `data/ohlcv/` con el patrón:
```
data/ohlcv/{SYMBOL}_{TIMEFRAME}.csv
```

**Ubicación completa** (desde la raíz del proyecto):
```
data/
  ohlcv/
    BTCUSDT_1h.csv
    BTCUSDT_4h.csv
    BTCUSDT_1d.csv
    ETHUSDT_1h.csv
    ETHUSDT_4h.csv
    ETHUSDT_1d.csv
    BNBUSDT_1h.csv
    ...
```

Ejemplos de rutas absolutas:
- `C:\Users\...\Black_Trade\data\ohlcv\BTCUSDT_1h.csv` (Windows)
- `/path/to/Black_Trade/data/ohlcv/BTCUSDT_1h.csv` (Linux/macOS)

### Columnas Requeridas

Cada CSV debe tener exactamente estas columnas (nombres sensibles a mayúsculas):
- `timestamp`: Fecha/hora en formato parseable (ISO 8601 recomendado: `YYYY-MM-DD HH:MM:SS`)
- `open`, `high`, `low`, `close`: Precios OHLC (números decimales)
- `volume`: Volumen de transacciones (número decimal)

**Formato de ejemplo**:
```csv
timestamp,open,high,low,close,volume
2024-01-01 00:00:00,50000.0,50100.0,49900.0,50050.0,1000.5
2024-01-01 01:00:00,50050.0,50200.0,50000.0,50150.0,1100.2
```

### Requisitos de Cobertura

- **Mínimo 2 símbolos** en el universo para rotación real (un solo símbolo activa modo fallback)
- **Timestamps comunes**: Los símbolos deben tener timestamps superpuestos para alineación
- **Datos suficientes**: Mínimo 50 períodos por símbolo para cálculos estables de EMA
- **Validación automática**: El loader valida columnas requeridas y rechaza datos inválidos

### Comportamiento con Universo Incompleto

Cuando no se pueden cargar todos los símbolos del universo, la estrategia maneja la situación de la siguiente manera:

#### Modo Estricto (`strict=True`)

- **Errores lanzados**:
  - `ValueError`: Si falta un símbolo requerido o tiene datos inválidos
  - `RuntimeError`: Si se cargan menos de 2 símbolos (insuficiente para rotación)
  
- **Uso recomendado**: Backtesting, validación de datos, despliegues en producción donde se requiere universo completo

#### Modo No Estricto (`strict=False`, default)

- **Advertencias registradas**: Se registran warnings en logs para símbolos faltantes o inválidos
- **Fallback a modo single-asset**: Si hay menos de 2 símbolos disponibles, la estrategia degrada a lógica EMA simple del símbolo actual
- **Telemetría**: Se registran métricas sobre participación:
  - `universe_symbols_count`: Cuántos símbolos participaron
  - `universe_participation`: Porcentaje de participación (símbolos cargados / total universo)
  - `rotation_available`: Boolean indicando si rotación multi-activo está disponible
  - `rotation_mode`: `'multi_asset'` o `'fallback'`
  - `rotation_rank`: Ranking del símbolo actual (o `-1` en modo fallback)

#### Ejemplos de Comportamiento

**Escenario 1: Todos los símbolos disponibles**
```
Universe: ["BTCUSDT", "ETHUSDT", "BNBUSDT"]
Cargados: 3/3 (100%)
Resultado: Rotación multi-activo activa, modo 'multi_asset'
```

**Escenario 2: Un símbolo faltante**
```
Universe: ["BTCUSDT", "ETHUSDT", "BNBUSDT"]
Cargados: 2/3 (66.7%) - FALTA: BNBUSDT
Resultado: Rotación multi-activo activa con 2 símbolos, modo 'multi_asset'
Log: WARNING - Missing symbols (1/3): ['BNBUSDT']
```

**Escenario 3: Solo un símbolo disponible**
```
Universe: ["BTCUSDT", "ETHUSDT", "BNBUSDT"]
Cargados: 1/3 (33.3%) - FALTAN: ETHUSDT, BNBUSDT
Resultado: Fallback a modo single-asset, modo 'fallback'
Log: WARNING - Rotation requires at least 2 symbols, but only 1 loaded
Log: WARNING - CryptoRotation fallback to single-symbol mode
```

**Escenario 4: Todos los símbolos faltantes**
```
Universe: ["BTCUSDT", "ETHUSDT", "BNBUSDT"]
Cargados: 0/3 (0%)
Resultado: Fallback a modo single-asset, modo 'fallback'
Log: ERROR - No data loaded for universe [...]
Log: WARNING - CryptoRotation fallback to single-symbol mode
```

## Uso en Backtests

### Escenario Básico

```python
from backtest.scenarios.rotation_orderflow import run_rotation_scenario

# Ejecutar con símbolos por defecto
results = run_rotation_scenario(timeframe="1h")

# Con parámetros personalizados
results = run_rotation_scenario(
    symbols=["BTCUSDT", "ETHUSDT", "BNBUSDT"],
    timeframe="4h",
    ranking_method="sharpe",
    min_divergence=0.015
)

print(f"Total trades: {results['total_trades']}")
print(f"Average win rate: {results['average_win_rate']:.2%}")
print(f"Net PnL: {results['net_pnl']:.2f}")
```

### Configuración YAML

Ver `backtest/scenarios/rotation.yaml` para configuración:

```yaml
symbols:
  - BTCUSDT
  - ETHUSDT
  - BNBUSDT
  - SOLUSDT
  - ADAUSDT
timeframe: 1h
crypto_rotation:
  lookback: 50
  ranking_method: strength
  min_divergence: 0.02
  top_n: 1
  bottom_n: 1
  rebalance_periods: 5
```

## Ejemplo de Resultados

### Salida del Backtest

```python
{
    "total_symbols": 5,
    "total_trades": 23,
    "average_win_rate": 0.52,
    "net_pnl": 1250.45,
    "symbol_results": [
        {
            "symbol": "BTCUSDT",
            "total_trades": 5,
            "win_rate": 0.60,
            "net_pnl": 450.20
        },
        {
            "symbol": "ETHUSDT",
            "total_trades": 8,
            "win_rate": 0.50,
            "net_pnl": 320.15
        },
        # ... más símbolos
    ]
}
```

## Limitaciones Conocidas

### 1. Alineación de Timestamps

- **Limitación**: Requiere timestamps superpuestos entre símbolos
- **Impacto**: Si los símbolos tienen cobertura temporal muy diferente, el universo alineado puede ser pequeño
- **Mitigación**: La función `align_universe_timestamps` usa intersección de timestamps; considera sincronizar datos antes de usar la estrategia

### 2. Divergencia Mínima

- **Limitación**: Si todos los símbolos se mueven en la misma dirección sin divergencia, no se generan señales
- **Impacto**: Puede haber períodos sin trades cuando los mercados están correlacionados
- **Ajuste**: Reducir `min_divergence` para más señales (puede aumentar falsos positivos)

### 3. Ranking Estático

- **Limitación**: El ranking se calcula una vez por período; no anticipa cambios futuros
- **Impacto**: Puede entrar tarde en tendencias o salir tarde de reversiones
- **Mitigación**: Ajustar `rebalance_periods` para re-evaluar más frecuentemente

### 4. Un Símbolo a la Vez

- **Limitación**: La estrategia actualmente genera señales para un símbolo a la vez basado en su ranking relativo
- **Impacto**: No diversifica automáticamente entre múltiples posiciones simultáneas
- **Extensión futura**: Podría implementarse lógica para mantener múltiples posiciones simultáneas en top N símbolos

### 5. Sin Reequilibrio Automático de Capital

- **Limitación**: No asigna capital proporcionalmente al ranking (todos los símbolos se tratan igual)
- **Impacto**: Perdemos optimización de asignación de capital basada en fuerza relativa
- **Extensión futura**: Implementar asignación de capital ponderada por score de ranking

## Supuestos

1. **Mercados correlacionados pero divergentes**: Los símbolos del universo deben estar correlacionados en general, pero con divergencias periódicas que permiten rotación
2. **Liquidez uniforme**: Se asume que todos los símbolos tienen suficiente liquidez para entrar/salir sin slippage significativo
3. **Costos simétricos**: Comisiones y slippage son iguales para todos los símbolos (puede no ser realista)
4. **Datos sincronizados**: Los datos deben estar sincronizados temporalmente; retrasos pueden afectar rankings

## Posibles Extensiones

### 1. Reequilibrio Periódico de Capital

Asignar capital proporcionalmente al score de ranking:
```python
# Ejemplo conceptual
capital_weights = {
    symbol: score / total_score 
    for symbol, score in ranked[:top_n]
}
```

### 2. Múltiples Posiciones Simultáneas

Mantener posiciones en top N símbolos simultáneamente en lugar de solo el #1:
```python
# Ya soportado con top_n > 1, pero requiere lógica adicional
# para gestionar múltiples posiciones por símbolo
```

### 3. Ranking Dinámico con Peso Histórico

Usar ranking ponderado por historial de rendimiento:
```python
# Ponderar scores actuales con rendimiento histórico
weighted_score = current_score * 0.7 + historical_performance * 0.3
```

### 4. Filtrado por Correlación

Solo incluir símbolos con correlación suficiente pero permitir divergencia:
```python
# Filtrar símbolos por correlación mínima
filtered_universe = [s for s in universe if correlation(s, universe) > 0.5]
```

### 5. Stop Loss y Take Profit Adaptativos

Ajustar niveles SL/TP basados en volatilidad relativa entre símbolos:
```python
# SL más amplio para símbolos más volátiles
atr_ratio = current_atr / universe_avg_atr
adaptive_sl = base_sl * atr_ratio
```

## Testing

Ver `tests/strategies/test_rotation.py` para:
- Tests de inicialización
- Tests de ranking por diferentes métodos
- Tests de generación de señales con/sin divergencia
- Tests de generación de trades
- Tests de lógica de rebalanceo

Ejecutar tests:
```bash
python -m pytest tests/strategies/test_rotation.py -v
```

## Comparación con Versión Anterior

### Versión Anterior (Proxy Single-Symbol)

- ❌ Solo trabajaba con un símbolo a la vez
- ❌ No comparaba con otros símbolos
- ❌ Generaba señales basadas en EMA absoluta, no relativa

### Versión Actual (Multi-Activo Genuino)

- ✅ Carga y compara múltiples símbolos
- ✅ Alinea timestamps para comparación justa
- ✅ Rankea símbolos relativamente
- ✅ Solo señala cuando hay divergencia suficiente
- ✅ Re-evalúa rankings periódicamente
- ✅ Soporta múltiples métodos de ranking

## Referencias

- `strategies/crypto_rotation_strategy.py`: Implementación de la estrategia
- `data/feeds/rotation_loader.py`: Utilidades para carga y alineación de datos
- `backtest/scenarios/rotation_orderflow.py`: Escenarios de backtest
- `backtest/scenarios/rotation.yaml`: Configuración YAML
- `backend/services/strategy_registry.py`: Registro y configuración
