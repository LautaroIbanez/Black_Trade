# Investor Summary

Este documento resume el estado actual del sistema, sus limitaciones y el plan de trabajo para los próximos hitos, con el objetivo de mantener una comunicación clara y verificable con stakeholders.

## Estado Actual y Limitaciones

- Confianza y Consenso:
  - No se aplican floors/boosts artificiales: la confianza proviene de señales reales (0–1) y el consenso está acotado a [0,1].
  - **Consenso refleja explícitamente incertidumbre**: 
    - **100% HOLD = 0% Consenso (Incertidumbre)**: Cuando todas las estrategias están en HOLD, el consenso es 0.0, reflejando indecisión del mercado, no convicción total.
    - **Señales mixtas con predominio de HOLD**: Cuando hay señales activas (BUY/SELL) pero predominan los neutrals (>50%), el consenso se escala hacia abajo automáticamente para reflejar la incertidumbre subyacente.
    - Esto previene falsa convicción cuando la mayoría de estrategias están indecisas.
  - **Consenso en escenarios mixtos (BUY/SELL/HOLD)**:
    - **Principio fundamental**: Cuando BUY y SELL coexisten (p. ej., 2 BUY / 1 SELL / 1 HOLD), el consenso se modera automáticamente mediante un límite configurable (`mixed_consensus_cap`, default: 0.60). Esto refleja que señales opuestas indican incertidumbre del mercado, no alta convicción.
    - **Interpretación para inversores**: Un consenso de ~0.50-0.60 con señales opuestas (BUY/SELL) indica una recomendación **moderada y cautelosa**, no alta confianza. Aunque la dirección pueda estar clara (por ejemplo, más BUY que SELL), la presencia de oposición significa que el mercado está dividido.
    - **Escenarios típicos**:
      - **2 BUY / 1 SELL / 1 HOLD**: Consenso ~0.60 (moderado). Interpretación: Señal BUY con cautela debido a oposición.
      - **1 BUY / 1 SELL / 3 HOLD**: Consenso ~0.15-0.25 (bajo). Interpretación: Alta incertidumbre, esperar confirmación.
      - **3 BUY / 0 SELL / 1 HOLD**: Consenso ~0.75-0.85 (alto). Interpretación: Alta convicción BUY sin oposición.
    - **Recomendación de uso**: En escenarios mixtos con consenso 0.50-0.60, considere:
      - Reducir tamaño de posición vs. señales de consenso >0.70
      - Establecer stop-loss más estricto
      - Monitorear señales adicionales antes de comprometerse completamente
      - Interpretar como "oportunidad moderada" no "oportunidad de alta convicción"
  - Posible baja confianza en escenarios de señales débiles o conflictivas.
  - Ver `docs/architecture/recommendation.md` y `docs/recommendation/timeframes.md` para detalles del cálculo y ejemplos numéricos.
- Estrategias en ajuste:
  - MACD: se corrigió el filtro de línea cero; genera trades en datasets con cruces. Aún requiere calibración fina por timeframe.
  - CryptoRotation y OrderFlow: habilitadas con parámetros conservadores; requieren universo multi-símbolo actualizado y más calibración de triggers para mayor diversificación.
  - **CryptoRotation - Dependencia Multi-Activo y Fallo Controlado**: 
    - **Dependencia de datos**: La estrategia requiere datos OHLCV para múltiples símbolos (mínimo 2, recomendado 5+). Los archivos CSV deben estar en `data/ohlcv/` con formato `{SYMBOL}_{TIMEFRAME}.csv`.
    - **Lista de símbolos requeridos por defecto**: BTCUSDT, ETHUSDT, BNBUSDT, SOLUSDT, ADAUSDT. Ver `docs/strategies/rotation_orderflow.md` para lista completa y rutas exactas.
    - **Fallo controlado**: Cuando faltan datos, la estrategia:
      - **Modo estricto** (`strict=True`): Falla inmediatamente con excepciones claras si faltan símbolos requeridos. Recomendado para backtesting y validación previa a producción.
      - **Modo no estricto** (`strict=False`, default): Registra alertas en logs y degrada a modo single-asset EMA cuando universo < 2 símbolos, pero continúa operando.
    - **Telemetría y monitoreo**: La estrategia registra métricas sobre participación:
      - `universe_symbols_count`: Número exacto de símbolos que participaron en cada decisión
      - `universe_participation`: Porcentaje de participación (símbolos cargados / total universo esperado)
      - `rotation_available`: Boolean indicando si rotación multi-activo está disponible (≥2 símbolos)
      - `rotation_mode`: `'multi_asset'` (rotación activa) o `'fallback'` (EMA single-asset degradado)
    - **Métricas de calidad**: Calcular porcentaje de decisiones basadas en ≥2 símbolos para monitorear calidad del universo:
      ```python
      # Ejemplo: Calcular porcentaje de decisiones multi-activo
      multi_asset_decisions = (signals['rotation_mode'] == 'multi_asset').sum()
      total_decisions = len(signals)
      participation_pct = (multi_asset_decisions / total_decisions) * 100
      # Idealmente >80% para estrategia multi-activo genuina
      ```
    - **Recomendación**: Antes de usar CryptoRotation, verificar disponibilidad de datos con `qa/strategy_checklist.md`. En producción, monitorear `universe_participation` y `rotation_mode` para detectar degradación a fallback.
    - Ver `docs/strategies/rotation_orderflow.md` para detalles completos sobre símbolos, rutas, comportamiento exacto en modo estricto/no estricto, y garantías de fallo controlado.
- Gestión de riesgo:
  - SL/TP validado con buffer dinámico (ATR × perfil). Fallback porcentual solo si no hay ATR.
- QA y transparencia:
  - Advertencia: La suite de QA está en expansión; algunas pruebas integrales y de regresión están en progreso. Consulte `docs/qa/status.md` para el estado más reciente.
  - Advertencia: Varias estrategias se encuentran en calibración activa (umbrales y parámetros pueden cambiar entre versiones menores).
  - Pesos por timeframe documentados y verificados; nuevas temporalidades integradas.

### Limitaciones actuales

- La confianza agregada puede superar la señal más débil en escenarios desbalanceados; la normalización está en curso para capear por media y mínimo activo.
- MACD, CryptoRotation y OrderFlow en calibración fina; parámetros sujetos a ajuste hasta cerrar la epic.
- QA end-to-end en progreso; ver ejecución real en `docs/qa/status.md`.

## Roadmap (próximos 4–6 semanas)

- Multi-símbolo y datos:
  - Consolidar universo (`ROTATION_UNIVERSE`) y refresco automático por símbolo/timeframe en `/refresh`.
  - Validaciones de continuidad y frescura por símbolo con alertas.
- Calibraciones y backtesting:
  - MACD: barrido de parámetros por timeframe (8/17/6, 12/26/9) con evaluación OOS.
  - OrderFlow: sensibilidad de `vol_mult` por régimen de volatilidad.
  - CryptoRotation: ranking multi-factor (EMA/RSI/volatilidad) y rotación multi-activo.
- Monitorización y reporting:
  - Reporte quincenal en `docs/reports/strategy_performance.md` (trades, win-rate, DD, retorno) + alertas automáticas (actividad nula, win-rate anómalo).
  - Panel de calibración con top estrategias/temporalidades y gaps de datos.
- Frontend/UX:
  - Placeholders consistentes para campos opcionales y mensajes de estado.
  - Indicadores visuales de contribución por timeframe y por estrategia.

## Dependencias y Riesgos

- Datos externos:
  - Calidad y disponibilidad de OHLCV por símbolo/timeframe (Binance). Mitigación: paginación + detección y relleno de huecos.
- Cobertura QA:
  - Aumentar pruebas de integración y escenarios sintéticos. Mitigación: ampliar suites y publicar estado tras cada release.
- Sobreajuste:
  - Evitar calibración exclusiva in-sample. Mitigación: walk-forward y OOS por defecto en evaluaciones clave.

## Próxima Auditoría

- Fecha objetivo: dentro de 14 días hábiles a partir de la publicación de este documento.
- Hitos:
  - QA status actualizado (`docs/qa/status.md`) con suite completa verde.
  - Reporte de desempeño (`docs/reports/strategy_performance.md`) con snapshot comparativo (últimas 2 semanas).
  - Resultados de calibración MACD y OrderFlow por timeframe con notas de decisión.
- Responsables:
  - Datos/Sync: Responsable de datos
  - Estrategias/Calibración: Responsable de I+D
  - QA/Reporting: Responsable de QA

## Cómo verificar

- Ejecutar QA y publicar estado:
```
python -m pytest -q && python qa/generate_status.py
```
- Revisar timeframes y pesos: `docs/recommendation/timeframes.md`
- Revisar riesgo y buffers: `docs/recommendation/risk.md`
