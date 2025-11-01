# Changelog

Todas las mejoras notables de este proyecto serán documentadas en este archivo.

El formato está basado en [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
y este proyecto adhiere a [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Sistema de visualización interactiva con gráficos de velas
- API de gráficos con endpoints para datos y señales
- Componente SignalChart con renderizado Canvas
- Selector de timeframes en el dashboard
- Overlays de señales y niveles de trading
- Tooltips informativos en gráficos
- Sistema de recomendaciones visuales integrado
- **Script de actualización automática de QA** (`qa/generate_status.py`)
- **Tests end-to-end del pipeline de agregación** (`tests/recommendation/test_e2e_aggregator.py`)
- **Documentación completa de QA** (`qa/README.md`)

### Changed
- Dashboard completamente rediseñado con layout responsive
- Integración de gráficos en tiempo real
- Mejora en la presentación de recomendaciones
- Optimización de la experiencia de usuario
- **Normalización de confianza y consenso**: Implementada con límites dinámicos (capped por mínimo y media de señales activas)
- **Ponderación dinámica de señales neutrales**: Evita sobreconfianza cuando hay pocas señales activas
- **Documentación técnica actualizada**: Comandos multiplataforma, estado real de QA, limitaciones conocidas

### Fixed
- Corrección de errores de serialización Pydantic
- Mejora en el manejo de errores del frontend
- Optimización de rendimiento en visualizaciones
- **Firmas de StrategySignal en tests**: Todos los tests actualizados para incluir `entry_range` y `risk_targets`
- **Imports obsoletos**: Corregidos (`backtest.engine.analysis` → `backtest.analysis`)
- **Métodos obsoletos**: Reemplazados (`_calculate_position_size_by_risk` → `_calculate_position_size`)

### Documentation
- **Actualización de documentación técnica**: Alineada con el estado actual del sistema, eliminando afirmaciones ficticias
- **`docs/qa/status.md`**: Actualizado con procedimiento real de ejecución, reflejando que puede contener fallos residuales documentados
- **`docs/recommendation/timeframes.md`**: 
  - Eliminadas afirmaciones de "tests verdes"
  - Añadida sección "Limitaciones Actuales" que referencia la epic de reactivación de QA
  - Clarificación de que las pruebas de temporalidades dependen del pipeline de QA
- **`docs/api/recommendation.md`**: Añadidas secciones sobre última ejecución de QA y cobertura actual
- **`README.md`**: 
  - Sección "Limitaciones Actuales" añadida con referencias a QA y estrategias en calibración
  - Enlaces a documentación relevante para transparencia
- **`qa/README.md`**: Documentación completa de instalación, configuración, ejecución y solución de problemas

### Correcciones Documentales (Transparencia)

- **Eliminación de afirmaciones ficticias**: Todas las referencias a "tests verdes" o estados inexistentes han sido eliminadas
- **Documentación de estado real**: Todos los documentos ahora reflejan el estado actual verificable, incluyendo fallos conocidos
- **Procedimientos reproducibles**: Instrucciones paso a paso para ejecutar QA y verificar resultados
- **Enlaces a epic correspondiente**: Referencias cruzadas entre documentos para navegación fácil

### Known Limitations

> ⚠️ **QA Pipeline Reactivado**: La suite de QA está reactivada y operativa. Puede contener fallos residuales que están documentados para transparencia. Ver `docs/qa/status.md` para estado actual y resultados de ejecuciones reales.

#### Tests Pendientes de Corrección

1. **Backtesting**:
   - `test_split_and_walk_forward`: KeyError en cierre forzado de posiciones (requiere ajuste en manejo de índices)
   - `test_cost_calculation`: Desajuste en expectativas del modelo de costos

2. **Sincronización de Datos**:
   - `test_continuity_across_timeframes`: Campo `records_count` falta en diccionario de validación

3. **Endpoints**:
   - `test_recommendation_includes_new_timeframes`: Timeframes nuevos pueden no aparecer en `strategy_details` cuando hay datos disponibles

#### Limitaciones Funcionales

1. **Inclusión de Timeframes**: El endpoint de recomendaciones puede no incluir todos los timeframes disponibles en `strategy_details` cuando hay datos para múltiples timeframes (corrección pendiente).

2. **Validación de Datos**: El campo `records_count` no está incluido en el diccionario de validación retornado por `data_loader.load_data` (requiere actualización en `data/sync_service.py`).

3. **Walk-Forward Testing**: El manejo de índices en cierre forzado de posiciones durante splits necesita ajuste para evitar KeyError.

#### Próximas Correcciones

- Implementar campo `records_count` en validación de datos
- Ajustar manejo de índices en walk-forward testing
- Asegurar inclusión de todos los timeframes en `strategy_details`
- **Validación completamente implementada**: La normalización de confianza y consenso está implementada y validada con tests. El consenso refleja explícitamente incertidumbre (100% HOLD = 0% consenso).

### Pendientes Críticos Relacionados con QA y Consenso

#### QA Pipeline
- **Estado**: Reactivado y operativo
- **Acción requerida**: Ejecutar `python qa/generate_status.py` para obtener resultados actuales
- **Documentación**: Ver `docs/qa/status.md` para procedimiento completo y problemas conocidos

#### Consenso Neutral
- **Estado**: ✅ Implementado y validado
- **Comportamiento**: 100% HOLD ahora resulta en consenso = 0.0 (incertidumbre), no 1.0
- **Validación**: Tests en `tests/recommendation/test_aggregator.py` verifican:
  - `test_all_hold_reflects_uncertainty_zero_consensus`
  - `test_consensus_never_reaches_one_when_neutrals_predominate`
  - `test_mixed_signals_2buy_1sell_rest_hold_consensus_within_weighted_average`
- **Documentación**: Ver `docs/architecture/recommendation.md` y `docs/recommendation/timeframes.md`

## [1.6.0] - 2024-01-15

### Added
- **Epic 5: Gobernanza y frescura de datos**
- Sistema de sincronización robusto con paginación automática
- Detección y completado automático de huecos en datos
- Validación de calidad de datos con métricas de frescura
- Job programado para sincronización automática (`sync_job.py`)
- DataLoader con verificación de continuidad temporal
- Logs estructurados para monitoreo de calidad
- Métricas de auditoría en formato JSONL
- Integración de validación en endpoint `/refresh`
- Tests unitarios para validación de datos

### Changed
- Mejora significativa en la confiabilidad de datos
- Optimización de la sincronización con Binance API
- Reducción de errores por datos faltantes
- Mejor manejo de límites de API

### Fixed
- Corrección de problemas de continuidad temporal
- Mejora en el manejo de datos faltantes
- Optimización de la carga de datos históricos

## [1.5.0] - 2024-01-10

### Added
- **Epic 4: Stop Loss y Take Profit adaptativos**
- Sistema de gestión de riesgo adaptativa
- Cálculo dinámico de SL/TP basado en ATR y volatilidad
- Detección automática de niveles de soporte/resistencia
- Módulo de análisis de pivot points y fractales
- Servicio de agregación de niveles de riesgo
- Integración de zonas de soporte/resistencia en estrategias
- Documentación completa de gestión de riesgo

### Changed
- Todas las estrategias ahora incluyen cálculo de niveles de riesgo
- Mejora en la precisión de niveles de entrada
- Optimización de la gestión de riesgo por volatilidad

### Fixed
- Corrección de cálculos de ATR en estrategias
- Mejora en la detección de niveles de soporte/resistencia

## [1.4.0] - 2024-01-05

### Added
- **Epic 3: Cálculo y exposición de rangos de entrada dinámicos**
- Método `entry_range` en todas las estrategias
- Cálculo de rangos de entrada basado en ATR y volatilidad
- Integración de rangos dinámicos en recomendaciones
- Actualización del modelo de datos de recomendaciones
- Documentación de rangos de entrada por estrategia

### Changed
- Mejora en la precisión de niveles de entrada
- Optimización de la presentación de rangos de entrada
- Actualización de la API de recomendaciones

### Fixed
- Corrección de cálculos de volatilidad
- Mejora en la consistencia de rangos de entrada

## [1.3.0] - 2024-01-01

### Added
- **Epic 2: Recomendación en tiempo real con múltiples estrategias**
- Sistema de generación de señales en tiempo real
- Método `generate_signal` en todas las estrategias
- Servicio de recomendaciones con agregación inteligente
- Ponderación de señales por confianza y consistencia
- Exposición de detalles de estrategias en recomendaciones
- Tests unitarios para servicio de recomendaciones
- Documentación de API de recomendaciones

### Changed
- Migración de backtesting a señales en tiempo real
- Mejora en la precisión de recomendaciones
- Optimización de la agregación de señales

### Fixed
- Corrección de errores de serialización en recomendaciones
- Mejora en el manejo de señales de múltiples estrategias

## [1.2.0] - 2023-12-28

### Added
- **Epic 1: Robustecer el motor de estrategias y backtesting**
- Sistema de gestión de costos (comisiones y slippage)
- Cierre automático de posiciones al final del backtest
- Registro configurable de estrategias
- Tests unitarios para motor de backtesting
- Documentación de estrategias y hooks disponibles
- Endpoint de recarga de configuraciones de estrategias

### Changed
- Mejora significativa en la precisión del backtesting
- Optimización del cálculo de métricas
- Mejor manejo de posiciones abiertas

### Fixed
- Corrección de sesgos en métricas de backtesting
- Mejora en el cálculo de PnL neto
- Optimización de la gestión de memoria

## [1.1.0] - 2023-12-20

### Added
- Sistema de recomendaciones básico
- Dashboard con métricas de estrategias
- Integración con Binance API
- Motor de backtesting inicial
- 5 estrategias de trading implementadas

### Changed
- Migración de arquitectura monolítica a modular
- Mejora en la organización del código
- Optimización de la interfaz de usuario

### Fixed
- Corrección de errores de conexión con Binance
- Mejora en el manejo de datos históricos

## [1.0.0] - 2023-12-15

### Added
- **Lanzamiento inicial del sistema Black Trade**
- Arquitectura base del sistema
- Motor de estrategias básico
- Interfaz web inicial
- Documentación básica

### Features
- Sistema de trading algorítmico para BTC/USDT
- Análisis multi-timeframe (1h, 4h, 1d, 1w)
- Backtesting con métricas básicas
- Interfaz web responsive
- Integración con Binance API

## [0.9.0] - 2023-12-10

### Added
- **Versión beta del sistema**
- Implementación inicial de estrategias
- Motor de backtesting básico
- Interfaz de usuario prototipo

### Changed
- Desarrollo inicial del sistema
- Configuración de infraestructura
- Implementación de funcionalidades core

## [0.8.0] - 2023-12-05

### Added
- **Versión alpha del sistema**
- Arquitectura inicial
- Prototipos de estrategias
- Configuración de desarrollo

### Changed
- Desarrollo temprano del sistema
- Investigación de tecnologías
- Diseño de arquitectura

---

## Convenciones de Versionado

### Formato de Versión
- **Major.Minor.Patch** (ej: 1.2.3)
- **Major**: Cambios incompatibles en la API
- **Minor**: Nuevas funcionalidades compatibles
- **Patch**: Correcciones de bugs compatibles

### Tipos de Cambios
- **Added**: Nuevas funcionalidades
- **Changed**: Cambios en funcionalidades existentes
- **Deprecated**: Funcionalidades marcadas para eliminación
- **Removed**: Funcionalidades eliminadas
- **Fixed**: Corrección de bugs
- **Security**: Mejoras de seguridad

### Categorías de Features
- **Epic X**: Implementaciones de epics completos
- **Feature**: Funcionalidades individuales
- **Enhancement**: Mejoras a funcionalidades existentes
- **Bugfix**: Correcciones de bugs
- **Documentation**: Actualizaciones de documentación
- **Performance**: Mejoras de rendimiento
- **Security**: Mejoras de seguridad

## Roadmap

### Versión 1.7.0 (Próxima)
- **Epic 7: Comunicación y documentación**
- Documentación completa del sistema
- Guías de usuario y desarrollador
- Checklist de QA
- Release notes detalladas

### Versión 1.8.0 (Futuro)
- **Epic 8: Optimización y escalabilidad**
- Optimización de rendimiento
- Escalabilidad horizontal
- Caching avanzado
- Monitoreo en tiempo real

### Versión 2.0.0 (Futuro)
- **Epic 9: Funcionalidades avanzadas**
- Trading automático
- Machine Learning
- Análisis de sentimiento
- Integración con múltiples exchanges

## Notas de Migración

### Migración de 1.5.0 a 1.6.0
- **Breaking Changes**: Ninguno
- **Nuevas Dependencias**: Ninguna
- **Configuración**: Actualizar variables de entorno para sincronización
- **Datos**: Ejecutar `/refresh` para sincronizar datos con nueva validación

### Migración de 1.4.0 a 1.5.0
- **Breaking Changes**: Ninguno
- **Nuevas Dependencias**: Ninguna
- **Configuración**: Ninguna
- **Datos**: Ninguna

### Migración de 1.3.0 a 1.4.0
- **Breaking Changes**: Ninguno
- **Nuevas Dependencias**: Ninguna
- **Configuración**: Ninguna
- **Datos**: Ninguna

### Migración de 1.2.0 a 1.3.0
- **Breaking Changes**: Cambio en formato de respuesta de `/recommendation`
- **Nuevas Dependencias**: Ninguna
- **Configuración**: Actualizar clientes que consuman la API
- **Datos**: Ninguna

### Migración de 1.1.0 a 1.2.0
- **Breaking Changes**: Ninguno
- **Nuevas Dependencias**: Ninguna
- **Configuración**: Actualizar archivo de configuración de estrategias
- **Datos**: Ninguna

## Contribuciones

### Cómo Contribuir
1. Fork del repositorio
2. Crear branch para feature (`git checkout -b feature/nueva-funcionalidad`)
3. Commit de cambios (`git commit -am 'Agregar nueva funcionalidad'`)
4. Push al branch (`git push origin feature/nueva-funcionalidad`)
5. Crear Pull Request

### Estándares de Código
- Seguir PEP 8 para Python
- Usar TypeScript para frontend
- Documentar todas las funciones públicas
- Incluir tests unitarios
- Actualizar documentación

### Proceso de Release
1. Actualizar CHANGELOG.md
2. Incrementar versión en package.json y setup.py
3. Crear tag de versión
4. Generar release notes
5. Desplegar en producción

## Contacto

- **Desarrollador Principal**: [Tu Nombre]
- **Email**: [tu-email@ejemplo.com]
- **GitHub**: [tu-usuario-github]
- **Documentación**: [docs/README.md](docs/README.md)

## Licencia

Este proyecto está licenciado bajo la Licencia MIT - ver el archivo [LICENSE](LICENSE) para detalles.
