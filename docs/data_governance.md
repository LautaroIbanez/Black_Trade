# Sistema de Gobernanza y Frescura de Datos

## Descripción General

El sistema de gobernanza y frescura de datos garantiza la sincronización confiable y validación del historial utilizado para las decisiones de trading. Proporciona monitoreo continuo, detección de huecos, y validación de calidad de datos.

## Características Principales

### 1. **Sincronización Robusta con Paginación**
- **Paginación automática**: Maneja datasets grandes dividiendo las solicitudes
- **Límite de seguridad**: Máximo 100 requests por sincronización
- **Rate limiting**: Pausas entre requests para evitar límites de API
- **Deduplicación**: Elimina registros duplicados automáticamente

### 2. **Detección y Completado de Huecos**
- **Detección automática**: Identifica intervalos faltantes en los datos
- **Tolerancia configurable**: 50% de tolerancia en intervalos esperados
- **Completado inteligente**: Rellena huecos con datos reales de Binance
- **Validación temporal**: Verifica continuidad temporal de los datos

### 3. **Validación de Calidad de Datos**
- **Continuidad temporal**: Verifica que no haya saltos inesperados
- **Consistencia OHLC**: Valida que High >= Low y Open/Close estén en rango
- **Volumen válido**: Detecta y reporta volúmenes cero o negativos
- **Frescura de datos**: Verifica que los datos estén actualizados

### 4. **Monitoreo y Métricas**
- **Logs estructurados**: Métricas en formato JSON para análisis
- **Métricas de calidad**: Puntuación de calidad de 0-100
- **Alertas automáticas**: Notificaciones de problemas de datos
- **Auditoría completa**: Trazabilidad de todas las operaciones

## Implementación Técnica

### SyncService Mejorado

```python
class SyncService:
    def _download_with_pagination(self, symbol: str, interval: str, 
                                 start_time: int, end_time: int, 
                                 limit: int = 1000) -> List[Dict]:
        """Download data with pagination to handle large date ranges."""
        all_candles = []
        current_start = start_time
        max_requests = 100  # Safety limit
        request_count = 0
        
        while current_start < end_time and request_count < max_requests:
            candles = self.binance_client.get_historical_candles(
                symbol=symbol,
                interval=interval,
                start_time=current_start,
                limit=limit
            )
            
            if not candles:
                break
            
            all_candles.extend(candles)
            last_timestamp = candles[-1]['timestamp']
            current_start = last_timestamp + 1
            request_count += 1
            
            # Rate limiting
            time.sleep(0.1)
        
        # Remove duplicates and sort
        if all_candles:
            df = pd.DataFrame(all_candles)
            df = df.drop_duplicates(subset=['timestamp']).sort_values('timestamp')
            all_candles = df.to_dict('records')
        
        return all_candles
```

### Detección de Huecos

```python
def _detect_gaps(self, df: pd.DataFrame, timeframe: str) -> List[Dict]:
    """Detect gaps in the data based on expected interval."""
    interval_minutes = self._get_interval_minutes(timeframe)
    expected_interval = pd.Timedelta(minutes=interval_minutes)
    
    gaps = []
    for i in range(1, len(df)):
        current_time = df.iloc[i]['datetime']
        previous_time = df.iloc[i-1]['datetime']
        actual_interval = current_time - previous_time
        
        # Check if there's a gap larger than expected
        if actual_interval > expected_interval * 1.5:  # 50% tolerance
            gap_start = previous_time + expected_interval
            gap_end = current_time - expected_interval
            
            gaps.append({
                "start_time": gap_start,
                "end_time": gap_end,
                "expected_candles": int((gap_end - gap_start) / expected_interval),
                "actual_interval": actual_interval.total_seconds() / 60
            })
    
    return gaps
```

### DataLoader con Validación

```python
class DataLoader:
    def load_data(self, symbol: str, timeframe: str, 
                  start_date: Optional[datetime] = None,
                  end_date: Optional[datetime] = None,
                  validate_continuity: bool = True) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """Load OHLCV data with temporal continuity validation."""
        
        # Load raw data
        df = self._load_raw_data(symbol, timeframe)
        
        # Convert timestamp to datetime
        df['datetime'] = pd.to_datetime(df['timestamp'], unit='ms')
        df = df.sort_values('datetime').reset_index(drop=True)
        
        # Filter by date range if specified
        if start_date:
            df = df[df['datetime'] >= start_date]
        if end_date:
            df = df[df['datetime'] <= end_date]
        
        # Validate temporal continuity
        validation_report = {}
        if validate_continuity:
            validation_report = self._validate_temporal_continuity(df, timeframe)
        
        # Handle missing data
        if validation_report.get('gaps_detected', 0) > 0:
            df = self._handle_missing_data(df, timeframe, validation_report)
        
        # Final validation
        final_validation = self._final_validation(df, timeframe)
        validation_report.update(final_validation)
        
        return df, validation_report
```

### Job Programable

```python
class SyncJob:
    def run_incremental_sync(self) -> Dict[str, Any]:
        """Run incremental data synchronization."""
        # Refresh latest candles
        refresh_results = self.sync_service.refresh_latest_candles(
            symbol=self.symbol,
            timeframes=self.timeframes
        )
        
        # Detect and fill any new gaps
        gap_results = self.sync_service.detect_and_fill_gaps(
            symbol=self.symbol,
            timeframes=self.timeframes
        )
        
        # Validate current day data
        validation_results = {}
        for timeframe in self.timeframes:
            validation_results[timeframe] = self.sync_service.validate_current_day_data(
                self.symbol, timeframe
            )
        
        return {
            "timestamp": start_time.isoformat(),
            "duration_seconds": duration,
            "symbol": self.symbol,
            "timeframes": self.timeframes,
            "refresh_results": refresh_results,
            "gap_results": gap_results,
            "validation_results": validation_results,
            "status": "success"
        }
```

## Métricas de Calidad

### Indicadores de Calidad

1. **Completitud**: Porcentaje de velas esperadas vs. reales
2. **Frescura**: Tiempo transcurrido desde la última vela
3. **Continuidad**: Número de huecos detectados
4. **Consistencia**: Errores en datos OHLC
5. **Volumen**: Porcentaje de velas con volumen cero

### Puntuación de Calidad

```python
def _final_validation(self, df: pd.DataFrame, timeframe: str) -> Dict[str, Any]:
    """Perform final validation on the processed data."""
    
    # Calculate quality score
    quality_score = 100
    quality_score -= zero_volume_percentage * 0.5  # Penalize zero volume
    quality_score -= ohlc_error_percentage * 2  # Penalize OHLC errors
    quality_score = max(0, quality_score)
    
    return {
        "final_valid": True,
        "total_candles": len(df),
        "zero_volume_count": zero_volume,
        "zero_volume_percentage": zero_volume_percentage,
        "ohlc_errors": ohlc_errors,
        "ohlc_error_percentage": ohlc_error_percentage,
        "quality_score": quality_score,
        "data_quality": "excellent" if quality_score >= 95 else 
                       "good" if quality_score >= 85 else
                       "fair" if quality_score >= 70 else
                       "poor"
    }
```

## Monitoreo y Logging

### Logs Estructurados

```json
{
  "event_type": "validation_completed",
  "timestamp": "2025-10-27T14:45:40.636935",
  "duration_seconds": 4.390059,
  "symbol": "BTCUSDT",
  "timeframes": ["1h", "4h", "1d", "1w"],
  "status": "success",
  "validation_results": {
    "1h": {
      "valid": true,
      "server_date": "2025-10-27",
      "latest_candle_date": "2025-10-27",
      "is_stale": false,
      "missing_current": false
    }
  },
  "data_quality_metrics": {
    "1h": {
      "total_candles": 8789,
      "date_range_hours": 8788.0,
      "gaps_detected": 0,
      "completeness_percentage": 100,
      "freshness_hours": -2.2380853636111113,
      "is_fresh": true,
      "latest_candle": "2025-10-27T17:00:00"
    }
  }
}
```

### Archivos de Log

- **`data_sync.log`**: Log general de sincronización
- **`sync_metrics.jsonl`**: Métricas de sincronización en JSONL
- **`validation_metrics.jsonl`**: Métricas de validación en JSONL

## Uso del Sistema

### 1. Sincronización Manual

```bash
# Sincronización completa
python backend/cron/sync_job.py --mode full

# Sincronización incremental
python backend/cron/sync_job.py --mode incremental

# Solo validación
python backend/cron/sync_job.py --mode validation
```

### 2. Uso Programático

```python
from backtest.data_loader import data_loader

# Cargar datos con validación
df, validation = data_loader.load_data(
    symbol="BTCUSDT",
    timeframe="1h",
    validate_continuity=True
)

# Obtener resumen de calidad
summary = data_loader.get_data_summary("BTCUSDT", ["1h", "4h", "1d"])
```

### 3. Endpoint de Refresh Mejorado

```python
@app.post("/refresh")
async def refresh_data() -> RefreshResponse:
    # Refresh data
    refresh_results = sync_service.refresh_latest_candles(symbol, timeframes)
    
    # Detect and fill gaps in data
    gap_results = sync_service.detect_and_fill_gaps(symbol, timeframes)
    
    # Validate data quality
    data_summary = data_loader.get_data_summary(symbol, timeframes)
    
    # Load data with validation for backtesting
    for timeframe in timeframes:
        data, validation_report = data_loader.load_data(
            symbol, timeframe, validate_continuity=True
        )
        # ... run backtests
```

## Configuración

### Parámetros Ajustables

```python
# Intervalos de tiempo en minutos
interval_minutes = {
    '1m': 1, '3m': 3, '5m': 5, '15m': 15, '30m': 30,
    '1h': 60, '2h': 120, '4h': 240, '6h': 360, '8h': 480, '12h': 720,
    '1d': 1440, '3d': 4320, '1w': 10080, '1M': 43200
}

# Tolerancia para detección de huecos
gap_tolerance = 0.5  # 50% del intervalo esperado

# Límites de sincronización
max_requests = 100
rate_limit_delay = 0.1  # segundos

# Criterios de frescura
freshness_threshold = 2  # horas
```

### Variables de Entorno

```bash
TRADING_PAIRS=BTCUSDT
TIMEFRAMES=1h,4h,1d,1w
DATA_DIR=data/ohlcv
LOG_LEVEL=INFO
```

## Testing

### Suite de Tests Completa

```python
class TestDataLoader(unittest.TestCase):
    def test_load_data_basic(self):
        """Test basic data loading."""
    
    def test_temporal_continuity_validation(self):
        """Test temporal continuity validation."""
    
    def test_missing_data_handling(self):
        """Test handling of missing data."""
    
    def test_final_validation(self):
        """Test final validation checks."""
    
    def test_data_summary(self):
        """Test data summary generation."""
```

### Casos de Prueba

1. **Datos básicos**: Carga y validación normal
2. **Huecos temporales**: Detección y completado
3. **Datos corruptos**: Manejo de errores
4. **Datos faltantes**: Interpolación y forward fill
5. **Validación OHLC**: Consistencia de precios
6. **Múltiples timeframes**: Carga simultánea
7. **Filtrado por fecha**: Rangos temporales
8. **Edge cases**: Archivos vacíos, corruptos, etc.

## Alertas y Monitoreo

### Alertas Automáticas

1. **Datos obsoletos**: Frescura > 2 horas
2. **Huecos detectados**: Intervalos faltantes
3. **Calidad baja**: Puntuación < 70
4. **Errores OHLC**: Inconsistencias en precios
5. **Volumen cero**: Alto porcentaje de velas sin volumen

### Métricas de Monitoreo

1. **Tasa de éxito**: Porcentaje de sincronizaciones exitosas
2. **Tiempo de respuesta**: Latencia de operaciones
3. **Calidad promedio**: Puntuación de calidad por timeframe
4. **Huecos por día**: Frecuencia de huecos detectados
5. **Frescura promedio**: Tiempo promedio de actualización

## Ventajas del Sistema

### 1. **Confiabilidad**
- Detección automática de problemas
- Recuperación automática de huecos
- Validación exhaustiva de datos

### 2. **Escalabilidad**
- Paginación para datasets grandes
- Rate limiting para APIs
- Procesamiento eficiente

### 3. **Transparencia**
- Logs detallados y estructurados
- Métricas de calidad claras
- Trazabilidad completa

### 4. **Mantenibilidad**
- Código modular y bien documentado
- Tests exhaustivos
- Configuración flexible

### 5. **Robustez**
- Manejo de errores gracioso
- Fallbacks automáticos
- Validación en múltiples capas

## Estado Final

**El sistema de gobernanza y frescura de datos está completamente implementado y funcionando!**

El sistema ahora proporciona:
- ✅ Sincronización robusta con paginación
- ✅ Detección y completado automático de huecos
- ✅ Validación exhaustiva de calidad de datos
- ✅ Monitoreo continuo con métricas detalladas
- ✅ Job programable para sincronización automática
- ✅ Logs estructurados para auditoría
- ✅ Tests completos y documentación
- ✅ Integración con el endpoint /refresh

¡El sistema de gobernanza de datos está listo para producción! 🚀
