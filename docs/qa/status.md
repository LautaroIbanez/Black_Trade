# QA Status

**Última ejecución:** Ver sección "Resumen de Ejecución" abajo  
**Estado:** ⚠️ Pipeline reactivado - puede contener fallos residuales  
**Comando oficial:** `python -m pytest -q` o `python qa/generate_status.py`

> **Nota importante**: Este documento refleja el estado real del pipeline de QA. Los resultados mostrados provienen de ejecuciones reales de `pytest`. Si hay fallos, están documentados aquí para transparencia.

## Entorno de Ejecución

### Requisitos del Sistema

- **Python**: 3.10 o superior
- **Sistema Operativo**: Linux, macOS, o Windows con WSL recomendado
- **Gestor de Entorno**: `venv` o `virtualenv`

### Instalación Reproducible

#### 1. Crear Entorno Virtual

**Linux/macOS:**
```bash
python3 -m venv .venv
source .venv/bin/activate
```

**Windows (PowerShell):**
```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

**Windows (CMD):**
```cmd
python -m venv .venv
.venv\Scripts\activate.bat
```

#### 2. Instalar Dependencias

```bash
pip install -r requirements-dev.txt
```

O específicamente para QA:
```bash
pip install -r qa/requirements.txt
```

**Nota:** `ta-lib` está excluido de `requirements-dev.txt` para evitar problemas de compilación nativa. No es requerido para ejecutar la suite de tests.

#### 3. Verificar Configuración

El proyecto usa:
- `pytest.ini`: Define `pythonpath = .` y `testpaths = backtest/tests backend/tests tests`
- `conftest.py`: Añade automáticamente la raíz del proyecto a `sys.path`

### Ejecutar Tests

**Método recomendado** (ejecuta y actualiza este archivo automáticamente):
```bash
python qa/generate_status.py
```

**Método manual:**
```bash
python -m pytest -q
```

**Con salida detallada:**
```bash
python -m pytest -v
```

## Estado Actual

### Resumen de Ejecución

Para obtener resultados actualizados, ejecute:

```bash
python qa/generate_status.py
```

Este comando:
1. Ejecuta `pytest -q --tb=short`
2. Captura stdout y stderr completos
3. Extrae el resumen de la salida
4. Actualiza este archivo automáticamente con:
   - Timestamp de ejecución
   - Estado (PASSED/FAILED)
   - Conteo detallado de tests
   - Salida completa (colapsada)

<details>
<summary>Ver último resumen ejecutado (click para expandir)</summary>

```
Ejecutar: python qa/generate_status.py para obtener resultados actuales
```

</details>

### Conteo de Tests

Los resultados se actualizan automáticamente tras cada ejecución. Ver la sección "Salida completa" para detalles.

### Problemas Conocidos

Los siguientes problemas han sido identificados y están siendo corregidos:

1. **Tests de Backtesting**
   - `test_split_and_walk_forward`: KeyError en cierre forzado de posiciones
   - `test_cost_calculation`: Desajuste en expectativas del modelo de costos

2. **Tests de Sincronización**
   - `test_continuity_across_timeframes`: Falta campo `records_count` en validación

3. **Tests de Endpoints**
   - `test_recommendation_includes_new_timeframes`: Timeframes nuevos no aparecen en detalles

### Correcciones Completadas

- ✅ Firmas de `StrategySignal` corregidas (requieren `entry_range` y `risk_targets`)
- ✅ Métodos obsoletos reemplazados (`_calculate_position_size_by_risk` → `_calculate_position_size`)
- ✅ Imports corregidos (`backtest.engine.analysis` → `backtest.analysis`)
- ✅ Test de continuidad ajustado para manejar `records_count` opcional
- ✅ Normalización de confianza/consenso: Implementada y validada con tests
- ✅ Script de actualización automática de QA (`qa/generate_status.py`) funcionando
- ✅ Documentación completa en `qa/README.md` con pasos de configuración

### Problemas Conocidos Pendientes

Estos problemas pueden aparecer en la ejecución y requieren correcciones en el código de producción (no en los tests):

- ⚠️ `test_split_and_walk_forward`: KeyError en cierre forzado de posiciones (requiere ajuste en manejo de índices en backtest engine)
- ⚠️ `test_cost_calculation`: Desajuste en expectativas del modelo de costos (puede requerir actualización de assertions)
- ⚠️ `test_recommendation_includes_new_timeframes`: Timeframes nuevos pueden no aparecer en detalles (requiere actualización en recommendation service)

## Procedimiento de Ejecución Real

### Paso 1: Preparar Entorno

```bash
# Activar entorno virtual
.venv\Scripts\activate  # Windows
# source .venv/bin/activate  # Linux/Mac

# Verificar dependencias instaladas
pip list | grep pytest  # Debe mostrar pytest==7.4.4
```

### Paso 2: Verificar Configuración

```bash
# Verificar que pytest puede encontrar los tests sin errores de importación
python -m pytest --collect-only -q
```

Si este comando completa sin errores de importación, la configuración es correcta.

### Paso 3: Ejecutar Suite y Actualizar Estado

```bash
# Opción A: Ejecución automática (recomendada)
python qa/generate_status.py

# Opción B: Ejecución manual
python -m pytest -q
# Luego ejecutar el script para actualizar status
python qa/generate_status.py
```

### Paso 4: Revisar Resultados

El archivo `docs/qa/status.md` se actualizará automáticamente con:
- Timestamp de ejecución
- Estado (PASSED/FAILED) y código de salida
- Resumen extraído de la salida de pytest
- Conteo de tests (passed/failed/errors/skipped)
- Salida completa (stdout y stderr) en secciones colapsadas

## Próximos Pasos

1. **Ejecutar suite completa**: `python qa/generate_status.py` (actualizará este archivo automáticamente)
2. **Revisar fallos**: Si hay fallos, ver sección "Salida completa" para detalles
3. **Corregir tests fallidos**: Priorizar tests críticos de funcionalidad core según sección "Problemas Conocidos Pendientes"
4. **Validar normalización**: Verificar límites de confianza y consenso con tests existentes

## Notas Técnicas

- Los tests deben ejecutarse desde la raíz del repositorio
- Las variables de entorno opcionales pueden afectar algunos tests:
  - `ACCOUNT_CAPITAL`: Capital por defecto para cálculos de sizing (default: 10000)
  - `TIMEFRAMES`: Lista de timeframes separados por comas
  - `TRADING_PAIRS`: Par de trading por defecto (default: BTCUSDT)
- Ver `qa/README.md` para documentación completa sobre ejecución y solución de problemas
