# Gestión de Riesgo: Buffer Dinámico con ATR

## Resumen
Se reemplaza el buffer fijo (1% del precio) por un buffer dinámico basado en ATR y el perfil de riesgo. Sólo se usa un fallback porcentual pequeño cuando ATR no está disponible.

## Lógica
- Perfil → `entry_buffer_atr_mult` (p. ej. balanced=0.7, swing=0.8)
- Buffer de entrada: `buffer = ATR * entry_buffer_atr_mult`
- Fallback si no hay ATR: `buffer = 0.5% * current_price`
- Se garantiza que `stop_loss` y `take_profit` queden fuera del rango de entrada por al menos `buffer`.

## Ejemplos

### Baja volatilidad
- `price=100`, `entry=[99, 101]`, `ATR=0.2`, perfil `balanced (0.7)`
- `buffer = 0.2 * 0.7 = 0.14`
- `SL_long >= 99 - 0.14 = 98.86`, `TP_long >= 101 + 0.14 = 101.14`

### Alta volatilidad
- `price=100`, `entry=[95, 105]`, `ATR=5.0`, perfil `swing (0.8)`
- `buffer = 5.0 * 0.8 = 4.0`
- `SL_long >= 95 - 4.0 = 91.0`, `TP_long >= 105 + 4.0 = 109.0`

## Implementación
- Código: `backend/services/risk_management.py::_ensure_levels_outside_entry_range`
- Config: `entry_buffer_atr_mult` por perfil en `_get_profile_risk_config`
- Pruebas: `tests/recommendation/test_risk_management.py`
