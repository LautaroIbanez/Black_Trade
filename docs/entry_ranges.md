# Rangos de Entrada Dinámicos

## Descripción General

El sistema de rangos de entrada dinámicos calcula niveles de entrada específicos para cada estrategia basándose en sus indicadores principales y la volatilidad del mercado. Esto proporciona una precisión mucho mayor en las recomendaciones de trading.

## Características Principales

### 1. **Cálculo Basado en Indicadores**
Cada estrategia utiliza sus indicadores específicos para determinar rangos de entrada óptimos:

- **EMA RSI**: Basado en la distancia entre EMAs y niveles de RSI
- **Momentum**: Utiliza la fuerza del histograma MACD y RSI
- **Breakout**: Considera el ancho de las bandas de Bollinger y ATR
- **Mean Reversion**: Usa la posición relativa a las bandas y RSI
- **Ichimoku**: Basado en el grosor de la nube y fuerza del ADX

### 2. **Ajuste por Volatilidad**
Todos los rangos se ajustan dinámicamente usando ATR (Average True Range) para reflejar las condiciones actuales del mercado.

### 3. **Diferenciación por Señal**
Los rangos se adaptan según el tipo de señal:
- **Señales de Compra**: Prefieren precios más altos
- **Señales de Venta**: Prefieren precios más bajos
- **Sin Señal**: Centrados en el precio actual

## Implementación Técnica

### Método Base: `entry_range()`

```python
def entry_range(self, df: pd.DataFrame, signal: int) -> Dict[str, float]:
    """
    Calculate dynamic entry range based on strategy-specific indicators and volatility.
    
    Args:
        df: DataFrame with OHLCV data and indicators
        signal: Signal value (-1, 0, 1)
        
    Returns:
        Dict with 'min' and 'max' entry prices
    """
```

### Estrategias Específicas

#### EMA RSI Strategy
```python
def entry_range(self, df: pd.DataFrame, signal: int) -> Dict[str, float]:
    # Calcula EMAs y RSI
    ema_fast = df['close'].ewm(span=self.fast_period).mean()
    ema_slow = df['close'].ewm(span=self.slow_period).mean()
    rsi = self._calculate_rsi(df['close'], self.rsi_period)
    
    # Rango base desde distancia entre EMAs
    ema_distance = abs(ema_fast - ema_slow)
    
    # Ajuste por momentum RSI
    if current_rsi > 70:  # Sobrecomprado - rango más estrecho
        rsi_multiplier = 0.5
    elif current_rsi < 30:  # Sobreventa - rango más amplio
        rsi_multiplier = 1.5
    else:
        rsi_multiplier = 1.0
    
    range_buffer = ema_distance * rsi_multiplier * 0.3
```

#### Momentum Strategy
```python
def entry_range(self, df: pd.DataFrame, signal: int) -> Dict[str, float]:
    # Calcula MACD y RSI
    macd_line, signal_line, histogram = self._calculate_macd(df['close'])
    rsi = self._calculate_rsi(df['close'], self.rsi_period)
    
    # Rango base desde fuerza del histograma MACD
    macd_strength = abs(current_histogram)
    
    # Ajuste por niveles extremos de RSI
    if current_rsi > 80:  # Muy sobrecomprado
        rsi_multiplier = 0.3
    elif current_rsi < 20:  # Muy sobreventa
        rsi_multiplier = 2.0
    # ... más niveles
    
    range_buffer = macd_strength * rsi_multiplier * 0.1
```

#### Breakout Strategy
```python
def entry_range(self, df: pd.DataFrame, signal: int) -> Dict[str, float]:
    # Calcula Bandas de Bollinger
    sma = df['close'].rolling(window=self.lookback).mean()
    std = df['close'].rolling(window=self.lookback).std()
    upper_band = sma + (std * self.multiplier)
    lower_band = sma - (std * self.multiplier)
    
    # Rango basado en ancho de bandas y ATR
    band_width = upper_band - lower_band
    range_buffer = atr_value * 0.3  # 30% del ATR
```

#### Mean Reversion Strategy
```python
def entry_range(self, df: pd.DataFrame, signal: int) -> Dict[str, float]:
    # Calcula Bandas de Bollinger y RSI
    sma = df['close'].rolling(window=self.period).mean()
    upper_band = sma + (std * self.bb_std)
    lower_band = sma - (std * self.bb_std)
    
    # Ajuste por extremos de RSI
    if current_rsi > 80:  # Espera reversión bajista
        rsi_multiplier = 0.8
    elif current_rsi < 20:  # Espera reversión alcista
        rsi_multiplier = 0.8
    # ... más niveles
    
    range_buffer = (band_width * 0.2) * rsi_multiplier
```

#### Ichimoku Strategy
```python
def entry_range(self, df: pd.DataFrame, signal: int) -> Dict[str, float]:
    # Calcula componentes Ichimoku
    tenkan_sen = (high.rolling(9).max() + low.rolling(9).min()) / 2
    kijun_sen = (high.rolling(26).max() + low.rolling(26).min()) / 2
    senkou_span_a = ((tenkan_sen + kijun_sen) / 2).shift(26)
    senkou_span_b = ((high.rolling(52).max() + low.rolling(52).min()) / 2).shift(26)
    
    # Rango basado en grosor de la nube
    cloud_thickness = cloud_top - cloud_bottom
    
    # Ajuste por fuerza del ADX
    if current_adx > 50:  # Tendencia fuerte - rango más estrecho
        adx_multiplier = 0.6
    elif current_adx > 30:  # Tendencia moderada
        adx_multiplier = 1.0
    else:  # Tendencia débil - rango más amplio
        adx_multiplier = 1.4
    
    range_buffer = (cloud_thickness * 0.3) * adx_multiplier
```

## Agregación de Rangos

El `RecommendationService` combina los rangos de entrada de múltiples estrategias usando ponderación:

```python
def _calculate_aggregated_entry_range(self, signals: List[StrategySignal]) -> Dict[str, float]:
    """Calculate aggregated entry range from multiple strategy signals."""
    weighted_min = 0.0
    weighted_max = 0.0
    total_weight = 0.0
    
    for signal in signals:
        weight = signal.confidence * signal.score
        weighted_min += signal.entry_range['min'] * weight
        weighted_max += signal.entry_range['max'] * weight
        total_weight += weight
    
    return {
        "min": weighted_min / total_weight,
        "max": weighted_max / total_weight
    }
```

## Uso en la API

### Endpoint `/recommendation`

La respuesta incluye rangos de entrada dinámicos:

```json
{
  "action": "BUY",
  "confidence": 0.85,
  "entry_range": {
    "min": 115092.34,
    "max": 115322.76
  },
  "stop_loss": 114055.47,
  "take_profit": 117511.70,
  "current_price": 115207.55,
  "strategy_details": [
    {
      "strategy_name": "EMA_RSI",
      "signal": 1,
      "strength": 1.0,
      "confidence": 0.9,
      "reason": "EMA Crossover BUY: Fast EMA (45020.50) > Slow EMA (44800.30), RSI (65.2) > 30",
      "entry_range": {
        "min": 115000.0,
        "max": 115400.0
      },
      "weight": 0.72
    }
  ]
}
```

## Ventajas

### 1. **Precisión Mejorada**
- Rangos específicos para cada estrategia
- Consideración de condiciones de mercado actuales
- Ajuste automático por volatilidad

### 2. **Flexibilidad**
- Diferentes rangos para señales de compra/venta
- Adaptación a extremos de mercado
- Consideración de múltiples timeframes

### 3. **Robustez**
- Validación de rangos (min < max)
- Fallbacks para datos insuficientes
- Manejo de errores gracioso

## Testing

Los rangos de entrada se validan con tests exhaustivos:

```python
def test_ema_rsi_entry_range(self):
    """Test EMA RSI entry range calculation."""
    range_buy = self.ema_rsi.entry_range(self.df, 1)
    self.assertIn('min', range_buy)
    self.assertIn('max', range_buy)
    self.assertLess(range_buy['min'], range_buy['max'])
    self.assertGreater(range_buy['min'], 0)
    self.assertGreater(range_buy['max'], 0)
```

## Configuración

Los rangos se pueden ajustar modificando los parámetros en cada estrategia:

- **Multiplicadores RSI**: Ajustan la sensibilidad a extremos
- **Porcentajes ATR**: Controlan el tamaño mínimo del rango
- **Factores de distancia**: Afectan la relación con indicadores técnicos

## Monitoreo

Los rangos se exponen en:
- Respuesta de la API `/recommendation`
- Detalles de cada estrategia
- Logs del sistema para debugging

Esto permite monitorear la efectividad de los rangos y ajustar parámetros según sea necesario.
