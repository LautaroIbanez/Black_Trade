# Sistema de Gestión de Riesgo Adaptativo

## Descripción General

El sistema de gestión de riesgo adaptativo calcula niveles de stop loss y take profit dinámicos que responden a la volatilidad del mercado y las zonas históricas de soporte/resistencia. Esto proporciona una gestión de riesgo más precisa y adaptada a las condiciones actuales del mercado.

## Características Principales

### 1. **Cálculo Adaptativo por Estrategia**
Cada estrategia utiliza sus indicadores específicos para determinar niveles de riesgo óptimos:

- **EMA RSI**: Basado en niveles de EMAs y momentum RSI
- **Momentum**: Utiliza fuerza del histograma MACD y RSI
- **Breakout**: Considera bandas de Bollinger y fuerza del breakout
- **Mean Reversion**: Usa extremos de RSI y distancia de la media
- **Ichimoku**: Basado en grosor de la nube y fuerza del ADX

### 2. **Análisis de Soporte y Resistencia**
Detección automática de niveles clave usando múltiples métodos:
- **Pivot Points**: Máximos y mínimos locales
- **Análisis Fractal**: Puntos de inflexión en múltiples timeframes
- **Perfil de Volumen**: Niveles con alta actividad de volumen
- **Medias Móviles**: Niveles de soporte/resistencia dinámicos

### 3. **Ajuste por Volatilidad**
Los niveles se adaptan automáticamente a las condiciones de volatilidad:
- **Alta Volatilidad**: Stops más amplios, targets más lejanos
- **Baja Volatilidad**: Stops más ajustados, targets más cercanos
- **Volatilidad Normal**: Niveles estándar

## Implementación Técnica

### Método Base: `risk_targets()`

```python
def risk_targets(self, df: pd.DataFrame, signal: int, current_price: float) -> Dict[str, float]:
    """
    Calculate adaptive risk targets based on strategy-specific indicators and volatility.
    
    Args:
        df: DataFrame with OHLCV data and indicators
        signal: Signal value (-1, 0, 1)
        current_price: Current market price
        
    Returns:
        Dict with 'stop_loss' and 'take_profit' levels
    """
```

### Estrategias Específicas

#### EMA RSI Strategy
```python
def risk_targets(self, df: pd.DataFrame, signal: int, current_price: float) -> Dict[str, float]:
    # Calcula EMAs y RSI
    ema_fast = df['close'].ewm(span=self.fast_period).mean()
    ema_slow = df['close'].ewm(span=self.slow_period).mean()
    rsi = self._calculate_rsi(df['close'], self.rsi_period)
    
    # Ajuste por momentum RSI
    if current_rsi > 80:  # Muy sobrecomprado - stops más ajustados
        rsi_multiplier = 0.7
    elif current_rsi < 20:  # Muy sobreventa - stops más amplios
        rsi_multiplier = 1.3
    # ... más niveles
    
    # Stop loss basado en EMA lenta o ATR
    if signal == 1:  # Buy signal
        ema_stop = ema_slow * 0.98  # 2% debajo de EMA lenta
        atr_stop = current_price - (atr_value * 2)  # 2 ATR debajo
        stop_loss = max(ema_stop, atr_stop)
        
        # Take profit basado en EMA rápida o ATR
        ema_target = ema_fast * 1.04  # 4% arriba de EMA rápida
        atr_target = current_price + (atr_value * 3)  # 3 ATR arriba
        take_profit = min(ema_target, atr_target)
```

#### Momentum Strategy
```python
def risk_targets(self, df: pd.DataFrame, signal: int, current_price: float) -> Dict[str, float]:
    # Calcula MACD y RSI
    macd_line, signal_line, histogram = self._calculate_macd(df['close'])
    rsi = self._calculate_rsi(df['close'], self.rsi_period)
    
    # Ajuste por fuerza del histograma MACD
    macd_strength = abs(current_histogram)
    macd_multiplier = min(macd_strength / (current_price * 0.01), 2.0)
    
    # Ajuste por extremos RSI
    if current_rsi > 85:  # Extremo sobrecomprado
        rsi_multiplier = 0.5
    elif current_rsi < 15:  # Extremo sobreventa
        rsi_multiplier = 1.5
    # ... más niveles
    
    # Stop loss basado en línea de señal MACD o ATR
    if signal == 1:  # Buy signal
        macd_stop = current_price - (macd_distance * 0.5)
        atr_stop = current_price - (atr_value * 2.5)
        stop_loss = max(macd_stop, atr_stop)
        
        # Take profit basado en fuerza MACD o ATR
        macd_target = current_price + (macd_strength * 2)
        atr_target = current_price + (atr_value * 4)
        take_profit = min(macd_target, atr_target)
```

#### Breakout Strategy
```python
def risk_targets(self, df: pd.DataFrame, signal: int, current_price: float) -> Dict[str, float]:
    # Calcula Bandas de Bollinger
    sma = df['close'].rolling(window=self.lookback).mean()
    std = df['close'].rolling(window=self.lookback).std()
    upper_band = sma + (std * self.multiplier)
    lower_band = sma - (std * self.multiplier)
    
    # Ajuste por ancho de bandas (volatilidad)
    band_width_pct = band_width / sma
    if band_width_pct > 0.05:  # Alta volatilidad
        volatility_multiplier = 1.5
    elif band_width_pct < 0.02:  # Baja volatilidad
        volatility_multiplier = 0.7
    
    # Ajuste por fuerza del breakout
    if signal == 1:  # Buy breakout
        breakout_strength = (current_price - upper_band) / upper_band
        if breakout_strength > 0.02:  # Breakout fuerte
            breakout_multiplier = 1.2
        elif breakout_strength < 0.005:  # Breakout débil
            breakout_multiplier = 0.8
    
    # Stop loss debajo del nivel de breakout
    if signal == 1:  # Buy breakout
        band_stop = upper_band * 0.98  # 2% debajo de banda superior
        atr_stop = current_price - (atr_value * 2)
        stop_loss = max(band_stop, atr_stop)
        
        # Take profit basado en ancho de bandas
        band_target = upper_band + (band_width * 0.5)
        atr_target = current_price + (atr_value * 3)
        take_profit = min(band_target, atr_target)
```

#### Mean Reversion Strategy
```python
def risk_targets(self, df: pd.DataFrame, signal: int, current_price: float) -> Dict[str, float]:
    # Calcula Bandas de Bollinger y RSI
    sma = df['close'].rolling(window=self.period).mean()
    upper_band = sma + (std * self.bb_std)
    lower_band = sma - (std * self.bb_std)
    
    # Ajuste por extremos RSI
    if current_rsi > 85:  # Extremo sobrecomprado - stops ajustados
        rsi_multiplier = 0.6
    elif current_rsi < 15:  # Extremo sobreventa - stops ajustados
        rsi_multiplier = 0.6
    # ... más niveles
    
    # Ajuste por distancia de la media
    distance_from_mean = abs(current_price - sma) / sma
    if distance_from_mean > 0.05:  # Lejos de la media - stops ajustados
        mean_multiplier = 0.7
    elif distance_from_mean < 0.01:  # Cerca de la media - stops amplios
        mean_multiplier = 1.3
    
    # Stop loss basado en bandas o ATR
    if signal == 1:  # Buy signal - reversión desde sobreventa
        band_stop = lower_band * 0.95  # 5% debajo de banda inferior
        atr_stop = current_price - (atr_value * 1.5)
        stop_loss = max(band_stop, atr_stop)
        
        # Take profit en la media o ATR
        sma_target = sma * 1.02  # 2% arriba de SMA
        atr_target = current_price + (atr_value * 2)
        take_profit = min(sma_target, atr_target)
```

#### Ichimoku Strategy
```python
def risk_targets(self, df: pd.DataFrame, signal: int, current_price: float) -> Dict[str, float]:
    # Calcula componentes Ichimoku
    tenkan_sen = (high.rolling(9).max() + low.rolling(9).min()) / 2
    kijun_sen = (high.rolling(26).max() + low.rolling(26).min()) / 2
    senkou_span_a = ((tenkan_sen + kijun_sen) / 2).shift(26)
    senkou_span_b = ((high.rolling(52).max() + low.rolling(52).min()) / 2).shift(26)
    
    # Calcula niveles de nube
    cloud_top = max(senkou_span_a, senkou_span_b)
    cloud_bottom = min(senkou_span_a, senkou_span_b)
    cloud_thickness = cloud_top - cloud_bottom
    
    # Ajuste por fuerza ADX
    if current_adx > 60:  # Tendencia muy fuerte - stops amplios
        adx_multiplier = 1.4
    elif current_adx > 40:  # Tendencia fuerte - stops normales
        adx_multiplier = 1.1
    elif current_adx > 25:  # Tendencia moderada - stops ajustados
        adx_multiplier = 0.9
    else:  # Tendencia débil - stops muy ajustados
        adx_multiplier = 0.7
    
    # Ajuste por grosor de nube
    cloud_thickness_pct = cloud_thickness / current_price
    if cloud_thickness_pct > 0.05:  # Nube gruesa - stops amplios
        cloud_multiplier = 1.3
    elif cloud_thickness_pct < 0.02:  # Nube delgada - stops ajustados
        cloud_multiplier = 0.8
    
    # Stop loss basado en nube o Tenkan-sen
    if signal == 1:  # Buy signal - arriba de nube
        cloud_stop = cloud_bottom * 0.98  # 2% debajo de nube
        tenkan_stop = tenkan_sen * 0.98  # 2% debajo de Tenkan-sen
        atr_stop = current_price - (atr_value * 2.5)
        stop_loss = max(cloud_stop, tenkan_stop, atr_stop)
        
        # Take profit arriba de nube o ATR
        cloud_target = cloud_top * 1.05  # 5% arriba de nube
        atr_target = current_price + (atr_value * 4)
        take_profit = min(cloud_target, atr_target)
```

## Servicio de Gestión de Riesgo

### RiskManagementService

```python
class RiskManagementService:
    """Service for managing risk targets across multiple strategies."""
    
    def aggregate_risk_targets(self, risk_targets: List[RiskTarget], 
                             historical_data: Optional[Dict[str, pd.DataFrame]] = None,
                             current_price: float = 0.0) -> AggregatedRiskTargets:
        """
        Aggregate risk targets from multiple strategies.
        
        Args:
            risk_targets: List of risk targets from individual strategies
            historical_data: Historical data for support/resistance analysis
            current_price: Current market price
            
        Returns:
            AggregatedRiskTargets object
        """
```

### Características del Servicio

1. **Agregación Ponderada**: Combina targets usando confianza y fuerza
2. **Análisis S/R**: Detecta niveles de soporte/resistencia relevantes
3. **Ajuste Automático**: Modifica niveles para evitar zonas fuertes
4. **Validación**: Verifica que los niveles cumplan reglas de riesgo
5. **Métricas**: Calcula ratios riesgo/recompensa y confianza

## Detección de Soporte y Resistencia

### SupportResistanceDetector

```python
class SupportResistanceDetector:
    """Detects support and resistance levels from price data."""
    
    def detect_levels(self, df: pd.DataFrame) -> List[SupportResistanceLevel]:
        """Detect support and resistance levels using multiple methods."""
```

### Métodos de Detección

1. **Pivot Points**: Máximos y mínimos locales
2. **Análisis Fractal**: Puntos de inflexión en múltiples timeframes
3. **Perfil de Volumen**: Niveles con alta actividad
4. **Medias Móviles**: Niveles dinámicos de soporte/resistencia

### SupportResistanceLevel

```python
@dataclass
class SupportResistanceLevel:
    price: float
    strength: float  # 0.0 to 1.0
    level_type: str  # 'support' or 'resistance'
    touches: int  # Number of times price touched this level
    last_touch: Optional[pd.Timestamp] = None
    volume_profile: Optional[float] = None
```

## Uso en la API

### Endpoint `/recommendation`

La respuesta incluye risk targets adaptativos:

```json
{
  "action": "BUY",
  "confidence": 0.85,
  "entry_range": {
    "min": 115092.34,
    "max": 115322.76
  },
  "stop_loss": 113925.18,
  "take_profit": 117377.46,
  "current_price": 115075.94,
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
      "risk_targets": {
        "stop_loss": 113500.0,
        "take_profit": 116800.0
      },
      "weight": 0.72
    }
  ],
  "support_resistance_analysis": {
    "levels": [...],
    "nearest_support": {...},
    "nearest_resistance": {...}
  }
}
```

## Validación de Niveles de Riesgo

### Reglas de Validación

```python
def validate_risk_levels(self, stop_loss: float, take_profit: float, 
                       current_price: float, risk_level: str = "MEDIUM") -> Dict[str, any]:
    """Validate risk levels against risk management rules."""
```

### Niveles de Riesgo

- **LOW**: Máximo 2% riesgo, mínimo 4% recompensa
- **MEDIUM**: Máximo 3% riesgo, mínimo 6% recompensa  
- **HIGH**: Máximo 5% riesgo, mínimo 10% recompensa

### Criterios de Validación

1. **Riesgo Válido**: Stop loss dentro del límite permitido
2. **Recompensa Válida**: Take profit cumple mínimo requerido
3. **Ratio Válido**: Relación riesgo/recompensa ≥ 1.5
4. **Zonas S/R**: Evita niveles de soporte/resistencia fuertes

## Testing

### Suite de Tests Completa

```python
class TestRiskManagementService(unittest.TestCase):
    def test_aggregate_risk_targets(self):
        """Test risk target aggregation."""
    
    def test_high_volatility_scenario(self):
        """Test risk management in high volatility scenario."""
    
    def test_low_volatility_scenario(self):
        """Test risk management in low volatility scenario."""
    
    def test_validate_risk_levels(self):
        """Test risk level validation."""
```

### Casos de Prueba

1. **Agregación Normal**: Múltiples estrategias con targets válidos
2. **Alta Volatilidad**: Stops más amplios, targets más lejanos
3. **Baja Volatilidad**: Stops ajustados, targets cercanos
4. **Validación**: Niveles que cumplen reglas de riesgo
5. **Soporte/Resistencia**: Detección y uso de niveles clave

## Configuración

### Parámetros Ajustables

- **Multiplicadores RSI**: Sensibilidad a extremos de momentum
- **Porcentajes ATR**: Tamaño mínimo de stops basado en volatilidad
- **Factores de Distancia**: Relación con indicadores técnicos
- **Umbrales S/R**: Sensibilidad para detectar niveles clave
- **Límites de Riesgo**: Máximos permitidos por nivel de riesgo

### Personalización por Estrategia

Cada estrategia puede tener sus propios parámetros:
- **EMA RSI**: Períodos de EMAs, niveles RSI
- **Momentum**: Parámetros MACD, extremos RSI
- **Breakout**: Multiplicador de bandas, fuerza de breakout
- **Mean Reversion**: Desviación estándar, extremos RSI
- **Ichimoku**: Períodos de componentes, umbral ADX

## Monitoreo y Alertas

### Métricas Clave

1. **Ratio Riesgo/Recompensa**: Efectividad de los targets
2. **Tasa de Acierto**: Porcentaje de stops/targets alcanzados
3. **Volatilidad Promedio**: Ajuste de niveles por condiciones
4. **Niveles S/R**: Frecuencia de uso de niveles clave

### Alertas Automáticas

- **Targets Inválidos**: Niveles que no cumplen reglas
- **Alta Volatilidad**: Requiere ajuste de parámetros
- **Niveles S/R Fuertes**: Zonas que requieren atención especial
- **Ratios Bajos**: Targets con pobre relación riesgo/recompensa

## Ventajas del Sistema

### 1. **Adaptabilidad**
- Respuesta automática a cambios de volatilidad
- Ajuste dinámico por condiciones de mercado
- Personalización por tipo de estrategia

### 2. **Precisión**
- Niveles basados en indicadores específicos
- Consideración de soporte/resistencia histórica
- Validación automática de reglas de riesgo

### 3. **Robustez**
- Múltiples métodos de detección S/R
- Fallbacks para datos insuficientes
- Manejo de errores gracioso

### 4. **Transparencia**
- Niveles expuestos en API
- Detalles de contribución por estrategia
- Análisis de soporte/resistencia incluido

### 5. **Flexibilidad**
- Configuración por estrategia
- Múltiples niveles de riesgo
- Fácil extensión para nuevas estrategias

## Estado Final

**El sistema de gestión de riesgo adaptativo está completamente implementado y funcionando!**

El sistema ahora proporciona:
- ✅ Risk targets adaptativos por estrategia
- ✅ Cálculo basado en indicadores específicos
- ✅ Análisis de soporte/resistencia automático
- ✅ Ajuste por volatilidad en tiempo real
- ✅ Agregación inteligente de múltiples estrategias
- ✅ Validación de reglas de riesgo
- ✅ API mejorada con risk targets detallados
- ✅ Tests completos y documentación

¡El sistema de gestión de riesgo adaptativo está listo para producción! 🚀
