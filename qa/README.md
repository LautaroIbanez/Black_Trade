# QA Execution Guide

## Prerrequisitos

1. **Python 3.10+** requerido
2. **Entorno virtual** activado (`.venv`)
3. **Dependencias instaladas**:
   ```bash
   pip install -r requirements-dev.txt
   ```
   O específicamente para QA:
   ```bash
   pip install -r qa/requirements.txt
   ```

## Configuración del Entorno

Desde la raíz del repositorio, los tests importan `backend`, `backtest`, etc. Esto funciona porque:
- `conftest.py` añade automáticamente la raíz del repositorio a `sys.path`
- `pytest.ini` establece `pythonpath=.` y las rutas de descubrimiento de tests

### Variables de Entorno Opcionales

Si necesitas personalizar variables de entorno, expórtalas antes de ejecutar tests:
```bash
# Windows PowerShell
$env:ACCOUNT_CAPITAL="10000"
$env:TIMEFRAMES="15m,1h,4h,1d"
$env:TRADING_PAIRS="BTCUSDT"

# Linux/Mac
export ACCOUNT_CAPITAL=10000
export TIMEFRAMES="15m,1h,4h,1d"
export TRADING_PAIRS="BTCUSDT"
```

## Comandos

### Ejecutar Tests Manualmente

```bash
# Modo quiet (solo resumen)
python -m pytest -q

# Modo verbose (detalles completos)
python -m pytest -v

# Ejecutar un archivo específico
python -m pytest backend/tests/test_recommendation_service.py

# Ejecutar una clase de test específica
python -m pytest backend/tests/test_recommendation_service.py::TestRecommendationService

# Ejecutar un test específico
python -m pytest backend/tests/test_recommendation_service.py::TestRecommendationService::test_strategy_signal_creation
```

### Generar Estado de QA

El script `qa/generate_status.py` ejecuta pytest, captura la salida y actualiza `docs/qa/status.md`:

```bash
# Ejecutar y actualizar estado automáticamente
python qa/generate_status.py
```

Este script:
- Ejecuta `pytest -q --tb=short`
- Captura stdout y stderr
- Extrae el resumen
- Actualiza `docs/qa/status.md` con timestamp, estado, conteo de tests y salida completa

### Flujo Completo Recomendado

```bash
# 1. Activar entorno virtual (si no está activo)
.venv\Scripts\activate  # Windows
source .venv/bin/activate  # Linux/Mac

# 2. Verificar que se pueden recolectar los tests
python -m pytest --collect-only

# 3. Ejecutar tests y actualizar estado
python qa/generate_status.py
```

## Estructura de Tests

- `backend/tests/`: Tests para servicios del backend
  - `test_recommendation_service.py`: Tests del servicio de recomendaciones
  - `test_normalization.py`: Tests de normalización de confianza/consenso
  - `test_risk_management.py`: Tests de gestión de riesgo
  - `test_sync_continuity.py`: Tests de continuidad de datos

- `tests/recommendation/`: Tests específicos de recomendaciones
  - `test_aggregator.py`: Tests unitarios del agregador
  - `test_e2e_aggregator.py`: Tests end-to-end del pipeline completo

- `backtest/tests/`: Tests del motor de backtesting
  - `test_backtest_engine.py`: Tests del motor principal
  - `test_strategy_base.py`: Tests de la clase base de estrategias
  - `test_analysis.py`: Tests de análisis de resultados

## Solución de Problemas

### Import Errors

Si ves errores como `ModuleNotFoundError: No module named 'backend'`:
1. Verifica que estás en la raíz del repositorio
2. Verifica que `pytest.ini` tiene `pythonpath=.`
3. Verifica que `conftest.py` existe en la raíz

### Dependencias Faltantes

Si faltan módulos durante la ejecución:
```bash
pip install -r requirements-dev.txt
```

### Timeout en Tests

Algunos tests pueden tomar tiempo. El script `qa/generate_status.py` tiene un timeout de 5 minutos. Para tests individuales más largos, ejecútalos directamente:
```bash
python -m pytest backend/tests/test_specific.py -v
```

## Estado Actual

Ver `docs/qa/status.md` para el estado más reciente de los tests, incluyendo:
- Última ejecución
- Estado (PASSED/FAILED)
- Resumen de resultados
- Conteo de tests (passed/failed/errors/skipped)
- Salida completa

## Próximos Pasos

1. **Corregir tests fallidos**: Priorizar tests críticos que afectan funcionalidad core
2. **Aumentar cobertura**: Añadir tests para casos edge y escenarios no cubiertos
3. **CI/CD Integration**: Integrar el pipeline de QA en CI/CD para ejecución automática

## Notas Adicionales

- El archivo `docs/qa/status.md` se actualiza automáticamente después de cada ejecución de `qa/generate_status.py`
- Los tests deben poder ejecutarse sin dependencias externas (APIs, bases de datos reales)
- Usa fixtures y mocks para aislar tests de dependencias externas
