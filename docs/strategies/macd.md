### Estrategia MACD Crossover

**Resumen**: La estrategia abre posiciones cuando `MACD` cruza su `Signal` en la dirección correspondiente y, opcionalmente, exige confirmación con cruce de línea cero. Ahora permite cerrar posiciones cuando el histograma (`MACD - Signal`) regresa/cruza a cero en contra de la posición, incluso si no hay una señal opuesta explícita.

### Parámetros
- **fast_period**: periodo EMA rápido (por defecto 12)
- **slow_period**: periodo EMA lento (por defecto 26)
- **signal_period**: periodo de la línea signal (por defecto 9)
- **histogram_threshold**: umbral mínimo absoluto del histograma para validar entradas; valores muy altos pueden anular demasiadas señales (por defecto 0.001)
- **zero_line_cross**: si es true, requiere `MACD > 0` para largos y `MACD < 0` para cortos en el momento de entrada

### Lógica de entrada
- Largo: `MACD > Signal` y, si `zero_line_cross`, además `MACD > 0`
- Corto: `MACD < Signal` y, si `zero_line_cross`, además `MACD < 0`
- Si `abs(Histogram) < histogram_threshold`, se evita abrir nuevas entradas en esa vela (pero no fuerza cierres)

### Lógica de salida
- Cierre por señal opuesta: cuando aparece señal contraria a la posición actual
- Cierre por histograma en cero: si el histograma cruza a cero en contra de la posición, se cierra la posición aunque no exista aún señal contraria explícita

### Escenarios en los que puede desactivarse o dar pocas operaciones
- **`histogram_threshold` demasiado alto**: puede filtrar casi todas las entradas si el mercado está lateral
- **`zero_line_cross = true` en mercados con `MACD` cercano a cero**: puede impedir entradas frecuentes
- **Datasets muy cortos o sin tendencias claras**: pocos cruces válidos

### Recomendaciones
- Para backtests iniciales, usar `histogram_threshold = 0.0` para comprobar apertura/cierre básico; luego ajustar según el activo y timeframe
- Validar en varios timeframes y activos; en cripto volátil, considerar elevar ligeramente el umbral y mantener `zero_line_cross = true`


