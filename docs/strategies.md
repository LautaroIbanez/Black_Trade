# Guía de Calibración y Validación de Estrategias

## Resumen

Esta guía describe el proceso de calibración, validación y aceptación de estrategias de trading para asegurar que no dependan de parámetros estáticos y cuentan con validación continua.

## Proceso de Calibración

### 1. Definición de Espacio de Parámetros

Cada estrategia debe definir su espacio de parámetros optimizables:

```python
from strategies.strategy_config import EMARSIConfig

config = EMARSIConfig()
parameter_space = config.get_parameter_space()
# Returns: {
#     'fast_period': [8, 10, 12, 14, 16, 18, 20],
#     'slow_period': [20, 22, 24, 26, 28, 30, 32, 34],
#     ...
# }
```

**Principios**:
- Incluir rangos razonables basados en teoría/experiencia
- No sobre-extender rangos (evitar sobreajuste)
- Considerar combinaciones lógicas (fast < slow, etc.)

### 2. Walk-Forward Optimization

#### Configuración

```python
from backtest.walkforward.walk_forward import WalkForwardEngine

wf_engine = WalkForwardEngine(
    train_size=0.7,      # 70% training
    test_size=0.3,       # 30% validation
    step_size=0.1,       # Slide 10% each iteration
    min_train_periods=100,
)
```

#### Proceso

1. **Split temporal**: Dividir datos en train/validation
2. **Optimizar en train**: Encontrar parámetros óptimos
3. **Validar en validation**: Probar parámetros en datos no vistos
4. **Slide forward**: Mover ventana y repetir
5. **Agregar resultados**: Calcular métricas promedio

### 3. Evaluación en Múltiples Datasets

#### Datasets Sintéticos

```python
from backtest.evaluation.synthetic_data import SyntheticDataGenerator

generator = SyntheticDataGenerator(seed=42)
trending_df = generator.generate_trending(periods=1000)
ranging_df = generator.generate_ranging(periods=1000)
volatile_df = generator.generate_volatile(periods=1000)
```

#### Evaluación Automática

```python
from backtest.evaluation.evaluator import StrategyEvaluator

evaluator = StrategyEvaluator(walk_forward_engine=wf_engine)
results = evaluator.evaluate_on_synthetic(
    strategy_class=EMARSIStrategy,
    parameter_space=parameter_space,
)
```

## Criterios de Aceptación

### Mínimos Requeridos

Una estrategia debe cumplir TODOS estos criterios para ser aceptada:

| Métrica | Mínimo | Descripción |
|---------|--------|-------------|
| **Sharpe Ratio** | ≥ 1.0 | Retorno ajustado por riesgo aceptable |
| **Max Drawdown** | ≤ 30% | Pérdida máxima controlada |
| **Win Rate** | ≥ 45% | Más ganadores que perdedores |
| **Profit Factor** | ≥ 1.2 | Rentabilidad positiva |
| **Min Trades** | ≥ 20 | Suficiente actividad para estadística |

### Validación Walk-Forward

Adicionalmente, la estrategia debe mostrar:

1. **Consistencia**: 
   - Ratio OOS/IS > 0.7 (performance out-of-sample similar a in-sample)
   - Parámetros óptimos no cambian drásticamente entre períodos

2. **Robustez**:
   - Performance estable en diferentes condiciones de mercado
   - Funciona bien en datasets sintéticos variados

3. **Estabilidad**:
   - Consistency score > 0.6 (performance estable entre iteraciones)

### Ejemplo de Verificación

```python
from backtest.evaluation.evaluator import StrategyEvaluator

evaluator = StrategyEvaluator()
results = evaluator.evaluate_on_synthetic(...)

# Check acceptance
acceptance = evaluator.check_acceptance_criteria(
    metrics=results['summary'],
    criteria={
        'min_sharpe_ratio': 1.0,
        'max_drawdown_pct': 30.0,
        'min_win_rate': 0.45,
        'min_profit_factor': 1.2,
        'min_trades': 20,
    }
)

if acceptance['passed']:
    print("Strategy PASSED acceptance criteria")
else:
    print("Strategy FAILED:")
    for check, passed in acceptance['checks'].items():
        if not passed:
            print(f"  - {check}: FAILED")
```

## Interpretación de Métricas

### Sharpe Ratio

- **< 0**: Estrategia peor que riesgo libre
- **0-1**: Retorno marginal ajustado por riesgo
- **1-2**: Buen retorno ajustado por riesgo
- **> 2**: Excelente retorno ajustado por riesgo

### Calmar Ratio

- **< 0**: Pérdidas netas
- **0-1**: Retorno bajo vs. riesgo máximo
- **1-3**: Buen balance retorno/riesgo
- **> 3**: Excelente retorno vs. drawdown máximo

### Win Rate vs. Profit Factor

- **Alto Win Rate + Alto PF**: Ideal (muchos ganadores grandes)
- **Alto Win Rate + Bajo PF**: Muchos ganadores pequeños (riesgo)
- **Bajo Win Rate + Alto PF**: Pocos ganadores pero grandes (puede funcionar)
- **Bajo Win Rate + Bajo PF**: No viable

## Proceso de Validación Continua

### 1. Evaluación Periódica

Ejecutar evaluación completa periódicamente (semanal/mensual):

```python
# Run evaluation
results = evaluator.evaluate_on_historical(...)

# Save to database
repo = StrategyResultsRepository()
repo.save_backtest_result(...)
```

### 2. Monitoreo de Degradación

Comparar métricas actuales vs. históricas:

```python
# Get latest results
latest = repo.get_latest_results(strategy_name='EMA_RSI', limit=1)[0]
current_metrics = latest['metrics']

# Compare with baseline
baseline_metrics = {...}  # From initial validation

degradation = {
    'sharpe_drop': baseline_metrics['sharpe_ratio'] - current_metrics['sharpe_ratio'],
    'maxdd_increase': current_metrics['max_drawdown_pct'] - baseline_metrics['max_drawdown_pct'],
    ...
}

# Alert if significant degradation
if degradation['sharpe_drop'] > 0.5:
    alert("Strategy performance degraded significantly")
```

### 3. Re-calibración Automática

Si degradación detectada:

1. Re-ejecutar walk-forward optimization
2. Comparar nuevos parámetros óptimos con actuales
3. Si mejoran significativamente → actualizar
4. Validar en período adicional antes de usar en producción

## Mejores Prácticas

### 1. Evitar Sobreajuste

- **No optimizar en todo el dataset**: Usar walk-forward
- **No revisar múltiples parámetros a la vez**: Empezar con los más importantes
- **Validar en datos no vistos**: OOS es crítico
- **No buscar perfección**: Sharpe 1.5-2.0 es bueno, > 3.0 puede ser sobreajuste

### 2. Robustez sobre Optimización

- **Preferir estrategias consistentes**: Sharpe 1.2 estable > Sharpe 2.0 variable
- **Probar en múltiples condiciones**: Trending, ranging, volatile
- **Considerar diferentes timeframes**: Si funciona en 1h, probar 4h, 1d

### 3. Documentación

- **Documentar parámetros probados**: Guardar historial de optimizaciones
- **Explicar decisiones**: Por qué ciertos rangos fueron elegidos
- **Registrar cambios**: Trackear cuándo y por qué parámetros cambiaron

## Ejemplo Completo

```python
from strategies.ema_rsi_strategy import EMARSIStrategy
from strategies.strategy_config import EMARSIConfig
from backtest.walkforward.walk_forward import WalkForwardEngine
from backtest.evaluation.evaluator import StrategyEvaluator
from backtest.evaluation.reporter import StrategyReporter
from backend.repositories.strategy_results_repository import StrategyResultsRepository

# 1. Define parameter space
config = EMARSIConfig()
parameter_space = config.get_parameter_space()

# 2. Setup walk-forward engine
wf_engine = WalkForwardEngine(
    train_size=0.7,
    test_size=0.3,
    step_size=0.1,
)

# 3. Evaluate on synthetic datasets
evaluator = StrategyEvaluator(walk_forward_engine=wf_engine)
synthetic_results = evaluator.evaluate_on_synthetic(
    strategy_class=EMARSIStrategy,
    parameter_space=parameter_space,
)

# 4. Evaluate on historical data
historical_df = pd.read_csv('data/ohlcv/BTCUSDT_1h.csv')
historical_results = evaluator.evaluate_on_historical(
    strategy_class=EMARSIStrategy,
    parameter_space=parameter_space,
    historical_dfs=[historical_df],
    dataset_names=['BTCUSDT_1h'],
)

# 5. Check acceptance
acceptance = evaluator.check_acceptance_criteria(historical_results['summary'])

if acceptance['passed']:
    # 6. Save results
    repo = StrategyResultsRepository()
    for dataset in historical_results['datasets']:
        for iteration in dataset['walk_forward_result']['iterations']:
            repo.save_backtest_result(
                strategy_name='EMA_RSI',
                parameters=iteration['optimal_parameters'],
                metrics=iteration['metrics'],
                dataset_name=dataset['name'],
                period_start=datetime.fromisoformat(iteration['metrics']['period_start']),
                period_end=datetime.fromisoformat(iteration['metrics']['period_end']),
                split_type='oos',
            )
    
    # 7. Generate report
    reporter = StrategyReporter()
    reporter.generate_comparison_report(
        [synthetic_results, historical_results],
        output_file='strategy_evaluation_report.txt',
    )
    
    print("Strategy validation PASSED")
else:
    print("Strategy validation FAILED")
    print(acceptance)
```

## Referencias

- [Arquitectura de Validación](./architecture/strategy_validation.md)
- [Walk-Forward Analysis](https://en.wikipedia.org/wiki/Walk_forward_optimization)
- [Backtesting Best Practices](https://www.quantstart.com/articles/Backtesting-Systematic-Trading-Strategies-in-Python-Part-IV/)
