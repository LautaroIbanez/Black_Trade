# QA Execution Guide

## Prerrequisitos

1. **Python 3.10+** requerido
2. **Entorno virtual** activado (`.venv`)
3. **Dependencias instaladas**

### Instalación Paso a Paso

#### Opción A: Instalación Completa (Recomendada)

```bash
# 1. Crear/activar entorno virtual
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Linux/Mac:
source .venv/bin/activate

# 2. Instalar todas las dependencias de desarrollo
pip install -r requirements-dev.txt
```

Esto instalará todas las dependencias incluyendo las requeridas para QA.

#### Opción B: Solo Dependencias de QA

Si solo necesitas ejecutar tests:

```bash
# Instalar solo dependencias de QA
pip install -r qa/requirements.txt
```

**Nota**: `requirements-dev.txt` incluye `qa/requirements.txt`, por lo que la Opción A es preferible.

### Dependencias Principales

Las dependencias clave para QA incluyen:
- `pytest==7.4.4` - Framework de testing
- `pandas==2.1.4` - Manipulación de datos
- `python-dotenv==1.0.0` - Carga de variables de entorno
- `numpy==1.26.2` - Operaciones numéricas
- `fastapi==0.109.0`, `httpx==0.26.0` - Para tests de API
- `pytest-asyncio==0.23.3` - Soporte para tests asíncronos

**Nota importante**: `ta-lib` está excluido de `requirements-dev.txt` para evitar problemas de compilación nativa. No es requerido para ejecutar la suite de tests.

## Configuración del Entorno

### Estructura de Módulos

Desde la raíz del repositorio, los tests importan `backend`, `backtest`, `strategies`, etc. Esto funciona porque:

1. **`conftest.py`** (en la raíz):
   - Añade automáticamente la raíz del repositorio a `sys.path`
   - Se ejecuta antes de cualquier test

2. **`pytest.ini`**:
   - Define `pythonpath = .` para que Python encuentre los módulos
   - Especifica rutas de descubrimiento: `testpaths = backtest/tests backend/tests tests`
   - Configura opciones por defecto: `addopts = -q` (modo quiet)

### Rutas de Módulos Soportadas

Los tests pueden importar desde:
- `backend.services.*` → `backend/services/`
- `backend.services.recommendation_service` → `backend/services/recommendation_service.py`
- `backtest.analysis.*` → `backtest/analysis/`
- `backtest.data_loader` → `backtest/data_loader.py`
- `strategies.*` → `strategies/`
- `data.feeds.*` → `data/feeds/`

### Verificación de Configuración

Para verificar que la configuración es correcta:

```bash
# Verificar que pytest puede encontrar los módulos
python -m pytest --collect-only -q

# Si no hay errores, la configuración está correcta
# Si hay errores de importación, verifica:
# 1. Estás en la raíz del repositorio
# 2. conftest.py existe en la raíz
# 3. pytest.ini tiene pythonpath = .
```

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

### Comandos Oficiales de Ejecución

#### Comando Principal (Recomendado)

```bash
# Ejecutar toda la suite en modo quiet
python -m pytest -q
```

Este es el comando estándar usado por el script de actualización automática de QA.

#### Otros Comandos Útiles

```bash
# Modo verbose (detalles completos)
python -m pytest -v

# Modo muy verbose con output de print statements
python -m pytest -vv -s

# Ejecutar solo tests que fallen
python -m pytest -q --lf  # last-failed

# Ejecutar solo tests que fallaron previamente y sus dependencias
python -m pytest -q --ff  # failed-first

# Ejecutar un archivo específico
python -m pytest backend/tests/test_recommendation_service.py

# Ejecutar una clase de test específica
python -m pytest backend/tests/test_recommendation_service.py::TestRecommendationService

# Ejecutar un test específico
python -m pytest backend/tests/test_recommendation_service.py::TestRecommendationService::test_strategy_signal_creation

# Ejecutar tests con marcadores específicos (si existen)
python -m pytest -q -m "not slow"  # Excluir tests marcados como "slow"

# Mostrar coverage (si pytest-cov está instalado)
python -m pytest -q --cov=backend --cov=backtest --cov-report=term-missing
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

#### Paso 1: Preparar Entorno

```bash
# Crear entorno virtual (si no existe)
python -m venv .venv

# Activar entorno virtual
# Windows:
.venv\Scripts\activate
# Linux/Mac:
source .venv/bin/activate

# Instalar dependencias
pip install -r requirements-dev.txt
```

#### Paso 2: Verificar Configuración

```bash
# Verificar que pytest puede encontrar todos los tests sin errores
python -m pytest --collect-only

# Si hay errores, revisa:
# - Estás en la raíz del repositorio
# - El entorno virtual está activado
# - Las dependencias están instaladas
```

#### Paso 3: Ejecutar Tests y Actualizar Estado

**Opción A: Ejecución Automática (Recomendada)**

```bash
# Ejecuta tests y actualiza docs/qa/status.md automáticamente
python qa/generate_status.py
```

Este script:
- Ejecuta `pytest -q --tb=short`
- Captura stdout y stderr
- Extrae el resumen
- Actualiza `docs/qa/status.md` con timestamp, estado y resultados

**Opción B: Ejecución Manual**

```bash
# Ejecutar tests
python -m pytest -q

# Luego actualizar estado manualmente o ejecutar el script
python qa/generate_status.py
```

#### Paso 4: Verificar Resultados

```bash
# Ver el estado actualizado
cat docs/qa/status.md  # Linux/Mac
type docs\qa\status.md  # Windows CMD
Get-Content docs\qa\status.md  # Windows PowerShell
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

**Última actualización**: Ver `docs/qa/status.md` para el estado más reciente de los tests.

**Estado típico**: 136+ passed, 1-2 failed (tests no críticos relacionados con estrategias específicas)

### Tests Principales Operativos

✅ **Tests de consenso y agregación**: Todos pasando, incluyendo escenarios mixtos (2 BUY / 1 SELL / 1 HOLD)  
✅ **Tests de walk-forward**: Corregido bug de índice fuera de rango en `close_all_positions`  
✅ **Tests de costes**: Corregidas expectativas del modelo de cálculo de costes  
✅ **Tests end-to-end**: Nuevo test `test_e2e_minimal.py` cubriendo pipeline completo  
✅ **Tests de normalización**: Validación completa de consenso y confianza  

### Tests Pendientes (No Críticos)

⚠️ **test_recommendation_includes_new_timeframes**: Error en generación de señales para Mean_Reversion, Ichimoku_ADX, RSIDivergence, Stochastic ('bool' object is not iterable). Este error es de las estrategias específicas, no del pipeline de QA.

## Próximos Pasos

1. **Corregir error en estrategias**: Revisar Mean_Reversion, Ichimoku_ADX, RSIDivergence, Stochastic para corregir 'bool' object is not iterable
2. **Aumentar cobertura**: Añadir tests para casos edge y escenarios no cubiertos
3. **CI/CD Integration**: Integrar el pipeline de QA en CI/CD para ejecución automática

## Notas Adicionales

- El archivo `docs/qa/status.md` se actualiza automáticamente después de cada ejecución de `qa/generate_status.py`
- Los tests deben poder ejecutarse sin dependencias externas (APIs, bases de datos reales)
- Usa fixtures y mocks para aislar tests de dependencias externas
- **Dependencias actualizadas**: `qa/requirements.txt` ahora incluye `python-binance==1.0.19`
- **PYTHONPATH configurado**: `pytest.ini` y `conftest.py` aseguran que todos los módulos sean importables desde la raíz
