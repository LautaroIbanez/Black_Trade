# Guía: Cómo Agregar una Nueva Estrategia de Trading

Esta guía te llevará paso a paso para crear e integrar una nueva estrategia de trading en el sistema Black Trade.

## 📋 Prerrequisitos

- Conocimiento básico de Python
- Entendimiento de análisis técnico
- Familiaridad con pandas y numpy
- Acceso al código fuente del proyecto

## 🏗️ Estructura de una Estrategia

Todas las estrategias deben heredar de `StrategyBase` y implementar los métodos requeridos:

```python
from strategies.strategy_base import StrategyBase
from typing import Dict, List, Any
import pandas as pd

class MiNuevaEstrategia(StrategyBase):
    def __init__(self, param1: int = 10, param2: float = 0.5, **kwargs):
        super().__init__("MI_ESTRATEGIA", {"param1": param1, "param2": param2}, **kwargs)
        self.param1 = param1
        self.param2 = param2
    
    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        # Implementar lógica de generación de señales
        pass
    
    def generate_trades(self, df: pd.DataFrame) -> List[Dict]:
        # Implementar lógica de generación de trades
        pass
    
    def _generate_signal_reason(self, df: pd.DataFrame, latest_row: pd.Series) -> str:
        # Implementar explicación de la señal
        pass
    
    def entry_range(self, df: pd.DataFrame, signal: int) -> Dict[str, float]:
        # Implementar cálculo de rango de entrada
        pass
    
    def risk_targets(self, df: pd.DataFrame, signal: int, current_price: float) -> Dict[str, float]:
        # Implementar cálculo de SL/TP
        pass
```

## 📝 Paso a Paso

### Paso 1: Crear el Archivo de la Estrategia

1. **Crear archivo en `strategies/`**:
   ```bash
   touch strategies/mi_nueva_estrategia.py
   ```

2. **Importar dependencias necesarias**:
   ```python
   import pandas as pd
   import numpy as np
   from typing import Dict, List, Any
   from strategies.strategy_base import StrategyBase
   ```

### Paso 2: Implementar la Clase Base

```python
class MiNuevaEstrategia(StrategyBase):
    def __init__(self, 
                 periodo: int = 20, 
                 multiplicador: float = 2.0,
                 commission: float = 0.001, 
                 slippage: float = 0.0005):
        """
        Inicializar la estrategia.
        
        Args:
            periodo: Período para el indicador principal
            multiplicador: Multiplicador para bandas
            commission: Comisión por trade (0.1%)
            slippage: Slippage por trade (0.05%)
        """
        super().__init__(
            name="MI_ESTRATEGIA",
            params={"periodo": periodo, "multiplicador": multiplicador},
            commission=commission,
            slippage=slippage
        )
        self.periodo = periodo
        self.multiplicador = multiplicador
```

### Paso 3: Implementar generate_signals()

Este método debe calcular los indicadores técnicos y generar señales:

```python
def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
    """
    Generar señales de trading basadas en la estrategia.
    
    Args:
        df: DataFrame con datos OHLCV
        
    Returns:
        DataFrame con señales y indicadores
    """
    df = df.copy()
    
    # Calcular indicadores técnicos
    df['sma'] = df['close'].rolling(window=self.periodo).mean()
    df['std'] = df['close'].rolling(window=self.periodo).std()
    df['upper_band'] = df['sma'] + (df['std'] * self.multiplicador)
    df['lower_band'] = df['sma'] - (df['std'] * self.multiplicador)
    
    # Calcular RSI
    df['rsi'] = self._calculate_rsi(df['close'], 14)
    
    # Generar señales
    df['signal'] = 0
    
    # Condiciones de compra
    buy_condition = (
        (df['close'] > df['upper_band']) & 
        (df['rsi'] < 70) &
        (df['close'].shift(1) <= df['upper_band'].shift(1))
    )
    
    # Condiciones de venta
    sell_condition = (
        (df['close'] < df['lower_band']) & 
        (df['rsi'] > 30) &
        (df['close'].shift(1) >= df['lower_band'].shift(1))
    )
    
    df.loc[buy_condition, 'signal'] = 1
    df.loc[sell_condition, 'signal'] = -1
    
    return df
```

### Paso 4: Implementar generate_trades()

Este método convierte las señales en trades ejecutables:

```python
def generate_trades(self, df: pd.DataFrame) -> List[Dict]:
    """
    Generar lista de trades basados en las señales.
    
    Args:
        df: DataFrame con señales
        
    Returns:
        Lista de diccionarios con información de trades
    """
    trades = []
    position = None
    
    for i, row in df.iterrows():
        signal = row['signal']
        price = row['close']
        timestamp = row['timestamp']
        
        if signal == 1 and position is None:  # Señal de compra
            position = {
                'entry_time': timestamp,
                'entry_price': price,
                'side': 'long',
                'quantity': 1.0
            }
            
        elif signal == -1 and position is not None:  # Señal de venta
            trade = {
                'entry_time': position['entry_time'],
                'exit_time': timestamp,
                'entry_price': position['entry_price'],
                'exit_price': price,
                'side': position['side'],
                'quantity': position['quantity'],
                'pnl': (price - position['entry_price']) * position['quantity'],
                'duration': timestamp - position['entry_time']
            }
            trades.append(trade)
            position = None
    
    # Cerrar posición abierta al final
    if position:
        final_trade = self.close_all_positions(df, position, df.iloc[-1]['close'], len(df) - 1)
        if final_trade:
            trades.append(final_trade)
    
    return trades
```

### Paso 5: Implementar _generate_signal_reason()

Este método proporciona explicaciones humanas de las señales:

```python
def _generate_signal_reason(self, df: pd.DataFrame, latest_row: pd.Series) -> str:
    """
    Generar explicación de la señal actual.
    
    Args:
        df: DataFrame completo
        latest_row: Fila actual con la señal
        
    Returns:
        String con explicación de la señal
    """
    signal = self._convert_numpy_type(latest_row.get('signal', 0), int)
    close = self._convert_numpy_type(latest_row.get('close', 0), float)
    upper_band = self._convert_numpy_type(latest_row.get('upper_band', 0), float)
    lower_band = self._convert_numpy_type(latest_row.get('lower_band', 0), float)
    rsi = self._convert_numpy_type(latest_row.get('rsi', 50), float)
    
    if signal == 1:
        return f"BUY: Price ({close:.2f}) broke above upper band ({upper_band:.2f}), RSI ({rsi:.1f}) < 70"
    elif signal == -1:
        return f"SELL: Price ({close:.2f}) broke below lower band ({lower_band:.2f}), RSI ({rsi:.1f}) > 30"
    else:
        return f"WAIT: Price ({close:.2f}) between bands ({lower_band:.2f}-{upper_band:.2f}), RSI ({rsi:.1f})"
```

### Paso 6: Implementar entry_range()

Este método calcula el rango de entrada óptimo:

```python
def entry_range(self, df: pd.DataFrame, signal: int) -> Dict[str, float]:
    """
    Calcular rango de entrada dinámico.
    
    Args:
        df: DataFrame con datos
        signal: Señal actual (1, -1, 0)
        
    Returns:
        Diccionario con min y max del rango de entrada
    """
    if df.empty or signal == 0:
        current_price = float(df['close'].iloc[-1]) if not df.empty else 0.0
        return {"min": current_price, "max": current_price}
    
    current_price = float(df['close'].iloc[-1])
    
    # Calcular ATR para volatilidad
    atr = self._calculate_atr(df, 14)
    atr_value = float(atr.iloc[-1]) if not atr.empty else current_price * 0.01
    
    # Calcular rango basado en bandas
    df_temp = df.copy()
    df_temp['sma'] = df_temp['close'].rolling(window=self.periodo).mean()
    df_temp['std'] = df_temp['close'].rolling(window=self.periodo).std()
    df_temp['upper_band'] = df_temp['sma'] + (df_temp['std'] * self.multiplicador)
    df_temp['lower_band'] = df_temp['sma'] - (df_temp['std'] * self.multiplicador)
    
    upper_band = float(df_temp['upper_band'].iloc[-1])
    lower_band = float(df_temp['lower_band'].iloc[-1])
    band_width = upper_band - lower_band
    
    # Rango de entrada basado en volatilidad
    range_buffer = max(atr_value * 0.5, band_width * 0.1)
    
    if signal == 1:  # Compra
        min_price = current_price - range_buffer * 0.5
        max_price = current_price + range_buffer * 1.5
    else:  # Venta
        min_price = current_price - range_buffer * 1.5
        max_price = current_price + range_buffer * 0.5
    
    return {"min": min_price, "max": max_price}
```

### Paso 7: Implementar risk_targets()

Este método calcula stop loss y take profit:

```python
def risk_targets(self, df: pd.DataFrame, signal: int, current_price: float) -> Dict[str, float]:
    """
    Calcular niveles de riesgo adaptativos.
    
    Args:
        df: DataFrame con datos
        signal: Señal actual
        current_price: Precio actual
        
    Returns:
        Diccionario con stop_loss y take_profit
    """
    if df.empty or signal == 0:
        return {"stop_loss": current_price, "take_profit": current_price}
    
    # Calcular ATR para volatilidad
    atr = self._calculate_atr(df, 14)
    atr_value = float(atr.iloc[-1]) if not atr.empty else current_price * 0.02
    
    # Calcular bandas para niveles de referencia
    df_temp = df.copy()
    df_temp['sma'] = df_temp['close'].rolling(window=self.periodo).mean()
    df_temp['std'] = df_temp['close'].rolling(window=self.periodo).std()
    df_temp['upper_band'] = df_temp['sma'] + (df_temp['std'] * self.multiplicador)
    df_temp['lower_band'] = df_temp['sma'] - (df_temp['std'] * self.multiplicador)
    
    upper_band = float(df_temp['upper_band'].iloc[-1])
    lower_band = float(df_temp['lower_band'].iloc[-1])
    sma = float(df_temp['sma'].iloc[-1])
    
    if signal == 1:  # Compra
        # Stop loss: debajo de la banda inferior o ATR
        stop_loss = max(lower_band * 0.98, current_price - (atr_value * 2))
        # Take profit: arriba de la banda superior o ATR
        take_profit = min(upper_band * 1.02, current_price + (atr_value * 3))
    else:  # Venta
        # Stop loss: arriba de la banda superior o ATR
        stop_loss = min(upper_band * 1.02, current_price + (atr_value * 2))
        # Take profit: debajo de la banda inferior o ATR
        take_profit = max(lower_band * 0.98, current_price - (atr_value * 3))
    
    return {"stop_loss": stop_loss, "take_profit": take_profit}
```

### Paso 8: Registrar la Estrategia

1. **Agregar al `__init__.py`**:
   ```python
   # strategies/__init__.py
   from .mi_nueva_estrategia import MiNuevaEstrategia
   ```

2. **Actualizar el registro de estrategias**:
   ```json
   // backend/config/strategies.json
   {
     "MI_ESTRATEGIA": {
       "name": "MI_ESTRATEGIA",
       "class_name": "MiNuevaEstrategia",
       "enabled": true,
       "parameters": {
         "periodo": 20,
         "multiplicador": 2.0
       },
       "commission": 0.001,
       "slippage": 0.0005,
       "description": "Estrategia personalizada basada en bandas y RSI"
     }
   }
   ```

### Paso 9: Crear Tests

Crear archivo de tests en `backtest/tests/test_mi_nueva_estrategia.py`:

```python
import unittest
import pandas as pd
from datetime import datetime
from strategies.mi_nueva_estrategia import MiNuevaEstrategia

class TestMiNuevaEstrategia(unittest.TestCase):
    def setUp(self):
        self.strategy = MiNuevaEstrategia()
        # Crear datos de prueba
        self.sample_data = self._create_sample_data()
    
    def _create_sample_data(self):
        # Implementar datos de prueba
        pass
    
    def test_generate_signals(self):
        # Test generación de señales
        pass
    
    def test_generate_trades(self):
        # Test generación de trades
        pass
    
    def test_entry_range(self):
        # Test cálculo de rango de entrada
        pass
    
    def test_risk_targets(self):
        # Test cálculo de niveles de riesgo
        pass

if __name__ == '__main__':
    unittest.main()
```

### Paso 10: Validar la Estrategia

1. **Ejecutar tests**:
   ```bash
   python -m backtest.tests.test_mi_nueva_estrategia
   ```

2. **Probar en el sistema**:
   ```bash
   # Iniciar el servidor
   python -m uvicorn backend.app:app --reload --port 8000
   
   # Probar endpoint de refresh
   curl -X POST http://localhost:8000/refresh
   ```

3. **Verificar en el frontend**:
   - Abrir http://localhost:5173
   - Verificar que la estrategia aparece en la lista
   - Revisar métricas de rendimiento

## 🔧 Configuración Avanzada

### Parámetros Personalizables

```python
# En el constructor de la estrategia
def __init__(self, 
             periodo: int = 20,
             multiplicador: float = 2.0,
             rsi_period: int = 14,
             rsi_oversold: int = 30,
             rsi_overbought: int = 70,
             **kwargs):
    super().__init__(
        name="MI_ESTRATEGIA",
        params={
            "periodo": periodo,
            "multiplicador": multiplicador,
            "rsi_period": rsi_period,
            "rsi_oversold": rsi_oversold,
            "rsi_overbought": rsi_overbought
        },
        **kwargs
    )
```

### Indicadores Técnicos Personalizados

```python
def _calculate_custom_indicator(self, prices: pd.Series, period: int) -> pd.Series:
    """
    Calcular indicador técnico personalizado.
    
    Args:
        prices: Serie de precios
        period: Período del indicador
        
    Returns:
        Serie con valores del indicador
    """
    # Implementar lógica del indicador
    return prices.rolling(window=period).mean()
```

### Gestión de Riesgo Personalizada

```python
def _calculate_volatility_adjustment(self, df: pd.DataFrame) -> float:
    """
    Calcular ajuste de volatilidad para niveles de riesgo.
    
    Args:
        df: DataFrame con datos
        
    Returns:
        Factor de ajuste de volatilidad
    """
    atr = self._calculate_atr(df, 14)
    current_atr = float(atr.iloc[-1]) if not atr.empty else 0.01
    current_price = float(df['close'].iloc[-1])
    
    # Ajustar según volatilidad relativa
    volatility_ratio = current_atr / current_price
    
    if volatility_ratio > 0.05:  # Alta volatilidad
        return 1.5
    elif volatility_ratio < 0.01:  # Baja volatilidad
        return 0.7
    else:  # Volatilidad normal
        return 1.0
```

## 📊 Mejores Prácticas

### 1. **Validación de Datos**
- Siempre verificar que el DataFrame no esté vacío
- Manejar valores NaN en indicadores
- Validar rangos de parámetros

### 2. **Manejo de Errores**
- Usar try-catch para operaciones críticas
- Proporcionar valores por defecto
- Logging de errores para debugging

### 3. **Optimización de Rendimiento**
- Usar operaciones vectorizadas de pandas
- Evitar loops innecesarios
- Cachear cálculos costosos

### 4. **Documentación**
- Documentar todos los parámetros
- Explicar la lógica de la estrategia
- Incluir ejemplos de uso

### 5. **Testing**
- Crear tests para casos edge
- Validar con datos reales
- Probar diferentes configuraciones

## 🚀 Despliegue

### 1. **Validación Final**
```bash
# Ejecutar todos los tests
python -m backtest.tests.run_tests

# Verificar linting
flake8 strategies/mi_nueva_estrategia.py

# Verificar tipos
mypy strategies/mi_nueva_estrategia.py
```

### 2. **Actualizar Configuración**
```json
{
  "MI_ESTRATEGIA": {
    "enabled": true,
    "parameters": {
      "periodo": 20,
      "multiplicador": 2.0
    }
  }
}
```

### 3. **Monitoreo**
- Revisar logs de la estrategia
- Monitorear métricas de rendimiento
- Ajustar parámetros según sea necesario

## 🆘 Troubleshooting

### Problemas Comunes

1. **Error de importación**:
   - Verificar que el archivo esté en `strategies/`
   - Comprobar imports en `__init__.py`

2. **Señales no generadas**:
   - Verificar condiciones de la estrategia
   - Revisar datos de entrada
   - Comprobar parámetros

3. **Rendimiento pobre**:
   - Optimizar cálculos de indicadores
   - Reducir complejidad computacional
   - Usar operaciones vectorizadas

4. **Errores de tipo**:
   - Verificar conversiones de numpy a Python
   - Usar `_convert_numpy_type()` helper
   - Comprobar tipos de retorno

### Debugging

```python
# Agregar logging para debugging
import logging
logger = logging.getLogger(__name__)

def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
    logger.info(f"Generating signals for {len(df)} candles")
    # ... implementación
    logger.info(f"Generated {df['signal'].sum()} signals")
    return df
```

## 📚 Recursos Adicionales

- [Documentación de StrategyBase](strategies.md)
- [Guía de Backtesting](how_to_run_backtest.md)
- [API de Recomendaciones](api/recommendation.md)
- [Gestión de Riesgo](risk_management.md)

¡Tu nueva estrategia está lista para ser utilizada en el sistema Black Trade! 🚀
