# Uso del Frontend: Porcentaje de Confianza

Este documento explica qué significa el porcentaje de confianza mostrado en la recomendación diaria, cómo se relaciona con el ranking histórico de estrategias y en qué condiciones puede bajar a valores cercanos a cero.

## ¿Qué es la “confianza”?
La confianza es un valor entre 0% y 100% que resume la calidad de la señal instantánea agregada por el sistema en función de:
- Intensidad de las señales activas (BUY/SELL) frente a neutrales (HOLD).
- Fortaleza de cada estrategia (strength) y su consistencia (confidence) en el timeframe evaluado.
- Peso del timeframe (mayor para 1w y 1d; intermedio para 4h; algo menor para 1h) para equilibrar fiabilidad y recencia.
- Desempeño histórico (ranking/score) de las estrategias que soportan la señal primaria.

## Cómo se calcula (visión de alto nivel)
1) Señales por timeframe
- Se pondera la confianza y la fortaleza por timeframe con pesos: 1w=1.0, 1d=0.9, 4h=0.7, 1h=0.5.
- Señales activas (BUY/SELL) reciben un impulso frente a HOLD. Las HOLD se atenúan con un factor máximo del 5% cuando hay señales activas.

2) Agregación de estrategias primarias
- Se identifican las estrategias primarias que apoyan la acción dominante (BUY/SELL o, si no hay dominancia, HOLD).
- La confianza base combina: confianza ponderada por timeframe × score histórico × impulso por fortaleza.
- Señales recientes fuertes en 1h/4h reciben un pequeño refuerzo adicional.

3) Vínculo con el ranking histórico
- Se calcula el promedio del score histórico de las estrategias primarias (o de las mejores disponibles si no hay primarias) y se añade un “historial boost” de hasta +0.25×score (capado a +0.25).
- Esto eleva la confianza cuando hay estrategias con buen ranking histórico respaldando la señal.

4) Umbrales mínimos (floors) para evitar valores ~0%
- BUY/SELL: se aplica un suelo mínimo (≥15%). Si hay ≥2 estrategias apoyando, se eleva a ~30%. Si hay alguna estrategia bien rankeada (score ≥0.7) con fortaleza media (≥0.4), el suelo es al menos ~25%.
- HOLD: si existen estrategias activas de buen ranking (score ≥0.7), la confianza no cae por debajo de ~10%.
- Estos pisos evitan que un HOLD débil reduzca la confianza hasta ~1% cuando hay evidencia de calidad histórica.

## Relación con el “ranking” en la pestaña de estrategias
- El ranking/score histórico proviene del backtest y pondera métricas como win rate, profit factor, PnL y expectancy. Se normaliza en [0,1].
- La confianza instantánea utiliza ese score como multiplicador de cada estrategia y además añade el “historial boost” agregado descrito arriba.
- En la UI, si ves estrategias con alto score respaldando la señal primaria, es esperable que la confianza sea mayor, incluso si el número de señales es moderado.

## ¿Cuándo puede bajar cerca de cero?
- No hay datos o no se generan señales válidas en ningún timeframe.
- Predominan HOLDs y no existen señales activas con buen ranking; en ese caso, el sistema puede mostrar valores bajos, aunque aplica suelos mínimos para evitar ~1% cuando hay historial fuerte.
- Señales contradictorias con baja fortaleza y puntajes históricos bajos en todas las estrategias.

## Notas prácticas
- Confianza alta (≥60–80%): acción respaldada por múltiples estrategias fuertes y buen historial.
- Confianza media (30–60%): evidencia razonable; gestionar riesgo con disciplina.
- Confianza baja (≤30%): contexto incierto o señales débiles/contradictorias.
