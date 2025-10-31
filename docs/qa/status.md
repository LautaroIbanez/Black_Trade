# QA Status

**Última ejecución:** Pendiente de reactivación  
**Estado:** ⚠️ QA Pipeline en reactivación  
**Comando:** `python -m pytest -q` o `python qa/generate_status.py`

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

<details>
<summary>Último resumen (click para expandir)</summary>

```
Ejecución pendiente. El pipeline de QA está siendo reactivado.
```

</details>

### Conteo de Tests

- ✅ Pasados: Por determinar
- ❌ Fallidos: Por determinar
- ⚠️  Errores: Por determinar
- ⏭️  Omitidos: Por determinar

### Problemas Conocidos

Los siguientes problemas han sido identificados y están siendo corregidos:

1. **Tests de Backtesting**
   - `test_split_and_walk_forward`: KeyError en cierre forzado de posiciones
   - `test_cost_calculation`: Desajuste en expectativas del modelo de costos

2. **Tests de Sincronización**
   - `test_continuity_across_timeframes`: Falta campo `records_count` en validación

3. **Tests de Endpoints**
   - `test_recommendation_includes_new_timeframes`: Timeframes nuevos no aparecen en detalles

### Correcciones en Progreso

- ✅ Firmas de `StrategySignal` corregidas (requieren `entry_range` y `risk_targets`)
- ✅ Métodos obsoletos reemplazados (`_calculate_position_size_by_risk` → `_calculate_position_size`)
- ✅ Imports corregidos (`backtest.engine.analysis` → `backtest.analysis`)
- ⚠️  Normalización de confianza/consenso: Implementada, pendiente validación completa
- ⚠️  Cierre de posiciones en walk-forward: Requiere ajuste en manejo de índices

## Próximos Pasos

1. **Ejecutar suite completa**: `python qa/generate_status.py`
2. **Corregir tests fallidos**: Priorizar tests críticos de funcionalidad core
3. **Validar normalización**: Verificar límites de confianza y consenso
4. **Documentar resultados**: Este archivo se actualizará automáticamente

## Notas Técnicas

- Los tests deben ejecutarse desde la raíz del repositorio
- Las variables de entorno opcionales pueden afectar algunos tests:
  - `ACCOUNT_CAPITAL`: Capital por defecto para cálculos de sizing (default: 10000)
  - `TIMEFRAMES`: Lista de timeframes separados por comas
  - `TRADING_PAIRS`: Par de trading por defecto (default: BTCUSDT)
- Ver `qa/README.md` para documentación completa sobre ejecución y solución de problemas
