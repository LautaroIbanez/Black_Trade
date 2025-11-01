# Checklist Operativo: Verificación de Estrategias Multi-Activo

Este checklist debe ejecutarse antes de cada despliegue o backtest para garantizar que las estrategias multi-activo tienen datos suficientes y coherentes.

## CryptoRotation Strategy

### Pre-Despliegue / Pre-Backtest

#### 1. Verificación de Datos del Universo

- [ ] **Ubicación de datos verificada**: Confirmar que los CSV están en `data/ohlcv/` con formato `{SYMBOL}_{TIMEFRAME}.csv`
  ```bash
  ls -la data/ohlcv/*.csv  # Linux/macOS
  dir data\ohlcv\*.csv     # Windows
  ```

- [ ] **Símbolos requeridos presentes**: Verificar que existen archivos para todos los símbolos del universo configurado
  ```bash
  # Verificar símbolos del universo
  grep -r "universe" backend/config/strategies.json
  # O variable de entorno
  echo $ROTATION_UNIVERSE
  ```

- [ ] **Columnas requeridas presentes**: Cada CSV debe tener: `timestamp`, `open`, `high`, `low`, `close`, `volume`
  ```bash
  # Verificar columnas de un archivo de ejemplo
  head -1 data/ohlcv/BTCUSDT_1h.csv
  # Debe mostrar: timestamp,open,high,low,close,volume
  ```

- [ ] **Datos suficientes**: Cada símbolo debe tener al menos 50 períodos de datos
  ```python
  import pandas as pd
  df = pd.read_csv('data/ohlcv/BTCUSDT_1h.csv')
  assert len(df) >= 50, f"Insufficient data: {len(df)} < 50"
  ```

#### 2. Validación de Timestamps

- [ ] **Timestamps comunes verificados**: Los símbolos deben tener timestamps superpuestos
  ```python
  from data.feeds.rotation_loader import load_rotation_universe, align_universe_timestamps
  
  symbols = ["BTCUSDT", "ETHUSDT", "BNBUSDT"]
  universe = load_rotation_universe(symbols, timeframe="1h")
  aligned = align_universe_timestamps(universe)
  
  # Verificar que hay timestamps comunes
  if aligned:
      first_symbol = list(aligned.keys())[0]
      common_timestamps = len(aligned[first_symbol])
      assert common_timestamps > 0, "No common timestamps found"
  ```

#### 3. Verificación de Configuración

- [ ] **Universo configurado correctamente**: Verificar en `backend/config/strategies.json` o variable de entorno
  ```python
  from data.feeds.rotation_loader import default_universe
  universe = default_universe()
  assert len(universe) >= 2, f"Universe must have at least 2 symbols, got {len(universe)}"
  ```

- [ ] **Parámetros válidos**: Verificar que `min_divergence`, `top_n`, `bottom_n` son razonables
  - `top_n + bottom_n <= len(universe)`
  - `min_divergence > 0`

#### 4. Prueba de Carga (Dry Run)

- [ ] **Loader funciona sin errores**: Ejecutar carga con modo estricto desactivado
  ```python
  from data.feeds.rotation_loader import load_rotation_universe
  
  symbols = ["BTCUSDT", "ETHUSDT", "BNBUSDT"]
  universe = load_rotation_universe(symbols, timeframe="1h", strict=False)
  assert len(universe) >= 2, f"Loaded only {len(universe)} symbols, need at least 2"
  ```

- [ ] **Estrategia genera señales**: Verificar que la estrategia puede generar señales sin errores
  ```python
  from strategies.crypto_rotation_strategy import CryptoRotationStrategy
  
  strategy = CryptoRotationStrategy(
      universe=["BTCUSDT", "ETHUSDT", "BNBUSDT"],
      lookback=20,
      ranking_method="strength"
  )
  
  # Cargar datos de prueba
  import pandas as pd
  df = pd.read_csv('data/ohlcv/BTCUSDT_1h.csv')
  signals = strategy.generate_signals(df, timeframe="1h", current_symbol="BTCUSDT")
  
  assert not signals.empty, "Strategy failed to generate signals"
  assert 'signal' in signals.columns, "Missing 'signal' column"
  assert 'rotation_mode' in signals.columns, "Missing telemetry columns"
  ```

#### 5. Verificación de Telemetría

- [ ] **Telemetría presente**: Verificar que las métricas de telemetría están presentes en las señales
  ```python
  required_telemetry = [
      'universe_symbols_count',
      'universe_participation',
      'rotation_available',
      'rotation_mode'
  ]
  
  for col in required_telemetry:
      assert col in signals.columns, f"Missing telemetry column: {col}"
  ```

- [ ] **Modo correcto verificado**: Si hay ≥2 símbolos, debe estar en modo `'multi_asset'`, no `'fallback'`
  ```python
  if signals['universe_symbols_count'].iloc[0] >= 2:
      assert all(signals['rotation_mode'] == 'multi_asset'), \
          "Expected multi_asset mode but got fallback"
  ```

### Post-Backtest / Post-Despliegue

#### 6. Verificación de Resultados

- [ ] **Porcentaje de decisiones multi-activo**: Calcular porcentaje de decisiones basadas en ≥2 símbolos
  ```python
  multi_asset_decisions = (signals['rotation_mode'] == 'multi_asset').sum()
  total_decisions = len(signals)
  participation_pct = (multi_asset_decisions / total_decisions) * 100
  
  print(f"Multi-asset decisions: {participation_pct:.1f}%")
  # Idealmente >80% para estrategia multi-activo genuina
  ```

- [ ] **Logs revisados**: Verificar que no hay warnings excesivos sobre símbolos faltantes
  ```bash
  # Revisar logs para warnings
  grep -i "missing symbols" logs/*.log
  grep -i "fallback" logs/*.log
  ```

- [ ] **Participación promedio**: Verificar que el porcentaje promedio de participación del universo es alto
  ```python
  avg_participation = signals['universe_participation'].mean()
  print(f"Average universe participation: {avg_participation:.1%}")
  # Idealmente >70% para indicar buena cobertura
  ```

## Script de Verificación Automatizada

Ejecutar el siguiente script Python para verificar todos los checks:

```python
#!/usr/bin/env python3
"""Verificación automatizada de datos para CryptoRotation."""
import sys
from pathlib import Path
import pandas as pd
from data.feeds.rotation_loader import load_rotation_universe, default_universe

def check_rotation_universe(timeframe="1h", strict=False):
    """Ejecuta checklist completo."""
    print("=== CryptoRotation Data Checklist ===\n")
    
    # 1. Verificar universo
    universe = default_universe()
    print(f"1. Universe configured: {len(universe)} symbols")
    print(f"   Symbols: {universe}\n")
    
    # 2. Verificar archivos
    data_dir = Path("data/ohlcv")
    missing_files = []
    for sym in universe:
        filepath = data_dir / f"{sym}_{timeframe}.csv"
        if not filepath.exists():
            missing_files.append(str(filepath))
    
    if missing_files:
        print(f"2. ❌ Missing files ({len(missing_files)}):")
        for f in missing_files:
            print(f"   - {f}")
        print()
    else:
        print(f"2. ✅ All {len(universe)} files present\n")
    
    # 3. Verificar columnas
    required_cols = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
    invalid_files = []
    for sym in universe:
        filepath = data_dir / f"{sym}_{timeframe}.csv"
        if filepath.exists():
            try:
                df = pd.read_csv(filepath, nrows=1)
                missing = [c for c in required_cols if c not in df.columns]
                if missing:
                    invalid_files.append((sym, missing))
            except Exception as e:
                invalid_files.append((sym, str(e)))
    
    if invalid_files:
        print(f"3. ❌ Invalid files ({len(invalid_files)}):")
        for sym, issue in invalid_files:
            print(f"   - {sym}: {issue}")
        print()
    else:
        print(f"3. ✅ All files have required columns\n")
    
    # 4. Verificar datos suficientes
    insufficient_data = []
    for sym in universe:
        filepath = data_dir / f"{sym}_{timeframe}.csv"
        if filepath.exists():
            try:
                df = pd.read_csv(filepath)
                if len(df) < 50:
                    insufficient_data.append((sym, len(df)))
            except Exception as e:
                insufficient_data.append((sym, str(e)))
    
    if insufficient_data:
        print(f"4. ❌ Insufficient data ({len(insufficient_data)}):")
        for sym, count in insufficient_data:
            print(f"   - {sym}: {count} rows (< 50 required)")
        print()
    else:
        print(f"4. ✅ All symbols have sufficient data (≥50 rows)\n")
    
    # 5. Intentar cargar universo
    try:
        loaded = load_rotation_universe(universe, timeframe, strict=strict)
        loaded_count = len(loaded)
        print(f"5. Loaded {loaded_count}/{len(universe)} symbols ({loaded_count/len(universe)*100:.1f}%)")
        
        if loaded_count < 2:
            print("   ❌ Insufficient symbols for rotation (need ≥2)")
            return False
        elif loaded_count < len(universe):
            missing = set(universe) - set(loaded.keys())
            print(f"   ⚠️  Missing symbols: {missing}")
        else:
            print("   ✅ All symbols loaded successfully")
        print()
        
        return loaded_count >= 2
        
    except Exception as e:
        print(f"5. ❌ Error loading universe: {e}\n")
        return False

if __name__ == "__main__":
    timeframe = sys.argv[1] if len(sys.argv) > 1 else "1h"
    strict = "--strict" in sys.argv
    
    success = check_rotation_universe(timeframe, strict)
    sys.exit(0 if success else 1)
```

### Uso del Script

```bash
# Verificación básica
python qa/strategy_checklist.py 1h

# Modo estricto (falla si falta algún símbolo)
python qa/strategy_checklist.py 1h --strict
```

## Notas

- **Antes de producción**: Ejecutar en modo estricto (`--strict`) para asegurar universo completo
- **Para backtesting**: Modo no estricto aceptable si se quiere probar con datos parciales
- **Monitoreo continuo**: Ejecutar este checklist periódicamente para detectar datos faltantes o corruptos
- **Integración CI/CD**: Incluir este checklist en pipeline de CI antes de despliegue

## Referencias

- `docs/strategies/rotation_orderflow.md` - Documentación completa de la estrategia
- `data/feeds/rotation_loader.py` - Código del loader con validaciones
- `strategies/crypto_rotation_strategy.py` - Implementación de la estrategia

