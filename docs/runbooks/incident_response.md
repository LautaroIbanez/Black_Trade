# Runbook: Respuesta a Incidentes

## Resumen

Este runbook describe los procedimientos estándar para responder a incidentes críticos en el sistema de trading automatizado.

## Clasificación de Incidentes

### Severidad CRÍTICA (P1)
- Sistema completamente inoperativo
- Pérdidas financieras en curso sin control
- Violaciones críticas de límites de riesgo
- Brechas de seguridad

**Tiempo de respuesta**: Inmediato  
**Tiempo de resolución objetivo**: 15 minutos

### Severidad ALTA (P2)
- Degradación significativa del sistema
- Alertas de riesgo continuas
- Errores persistentes en ejecución
- Degradación de estrategias

**Tiempo de respuesta**: 5 minutos  
**Tiempo de resolución objetivo**: 1 hora

### Severidad MEDIA (P3)
- Problemas menores que afectan operaciones
- Alertas de rendimiento
- Errores intermitentes

**Tiempo de respuesta**: 30 minutos  
**Tiempo de resolución objetivo**: 4 horas

## Procedimientos por Tipo de Incidente

### 1. Sistema Completamente Inoperativo

#### Síntomas
- API no responde
- Health checks fallan
- Base de datos no accesible
- Todas las métricas en cero/NaN

#### Acciones Inmediatas

1. **Verificar estado del servicio**
   ```bash
   curl http://localhost:8000/api/health
   ```

2. **Verificar logs**
   ```bash
   tail -f logs/app.log
   # O si usa Docker:
   docker logs -f black-trade-api
   ```

3. **Verificar recursos del sistema**
   ```bash
   # CPU y memoria
   top
   # O
   docker stats
   ```

4. **Verificar base de datos**
   ```bash
   psql -h localhost -U user -d black_trade -c "SELECT 1;"
   ```

5. **Restart del servicio si es necesario**
   ```bash
   # Si usa systemd
   sudo systemctl restart black-trade-api
   
   # Si usa Docker
   docker restart black-trade-api
   ```

#### Escalación
- Si no se resuelve en 15 minutos, escalar a equipo de infraestructura
- Notificar a todos los stakeholders

---

### 2. Violación Crítica de Límites de Riesgo

#### Síntomas
- Drawdown > límite máximo
- Pérdida diaria > límite
- Exposición > límite máximo
- Alertas críticas de riesgo

#### Acciones Inmediatas

1. **Verificar estado actual de riesgo**
   ```bash
   curl http://localhost:8000/api/risk/status \
     -H "Authorization: Bearer <token>"
   ```

2. **Revisar posiciones abiertas**
   ```bash
   curl http://localhost:8000/api/risk/positions \
     -H "Authorization: Bearer <token>"
   ```

3. **Pausar trading automático**
   ```python
   # Deshabilitar todas las estrategias
   from backend.services.strategy_registry import strategy_registry
   for strategy in strategy_registry.get_enabled_strategies():
       strategy_registry.disable_strategy(strategy.name)
   ```

4. **Cancelar todas las órdenes pendientes**
   ```bash
   # Listar órdenes pendientes
   curl http://localhost:8000/api/execution/orders?status=pending \
     -H "Authorization: Bearer <token>"
   
   # Cancelar cada orden (implementar bulk cancel si necesario)
   ```

5. **Evaluar cierre de posiciones**
   - Revisar P&L de cada posición
   - Decidir si cerrar posiciones para reducir exposición
   - Documentar decisión

#### Documentación Post-Incidente
- Registrar causa raíz
- Revisar ajustes de límites necesarios
- Actualizar procedimientos si aplica

---

### 3. Errores Persistentes de Ejecución de Órdenes

#### Síntomas
- Tasa alta de rechazo de órdenes
- Timeouts frecuentes
- Errores de conexión con exchange

#### Acciones Inmediatas

1. **Verificar métricas de ejecución**
   ```bash
   curl http://localhost:8000/api/metrics \
     -H "Authorization: Bearer <token>"
   ```

2. **Revisar journal de errores**
   ```bash
   curl http://localhost:8000/api/execution/journal?entry_type=error&limit=50 \
     -H "Authorization: Bearer <token>"
   ```

3. **Verificar conectividad con exchange**
   ```bash
   # Verificar balance
   curl http://localhost:8000/api/risk/status \
     -H "Authorization: Bearer <token>"
   ```

4. **Revisar credenciales API**
   - Verificar que API keys estén vigentes
   - Verificar límites de rate limits
   - Verificar permisos de API keys

5. **Pausar ejecución si es necesario**
   - Si tasa de error > 50%, pausar automático
   - Cambiar a modo manual hasta resolver

#### Escalación
- Si error persiste > 1 hora, contactar exchange
- Documentar errores específicos para soporte

---

### 4. Degradación de Estrategias

#### Síntomas
- Win rate disminuye significativamente
- Sharpe ratio negativo
- Recomendaciones inconsistentes
- Alertas de degradación de estrategia

#### Acciones Inmediatas

1. **Verificar performance de estrategias**
   ```bash
   curl http://localhost:8000/api/metrics \
     -H "Authorization: Bearer <token>" | jq '.strategy_performance'
   ```

2. **Revisar recomendaciones recientes**
   - Analizar calidad de señales
   - Verificar coherencia entre estrategias

3. **Deshabilitar estrategia degradada**
   ```python
   from backend.services.strategy_registry import strategy_registry
   strategy_registry.disable_strategy("StrategyName")
   ```

4. **Revisar datos de mercado**
   - Verificar si hay cambio de régimen de mercado
   - Verificar si hay problemas con datos históricos

#### Análisis Post-Incidente
- Revisar parámetros de estrategia
- Actualizar validaciones si necesario
- Considerar retraining del modelo

---

### 5. Alta Latencia del Sistema

#### Síntomas
- P95 latency > 1 segundo
- P99 latency > 2 segundos
- Timeouts en requests
- Degradación de experiencia de usuario

#### Acciones Inmediatas

1. **Verificar métricas de latencia**
   ```bash
   curl http://localhost:8000/api/metrics \
     -H "Authorization: Bearer <token>" | jq '.latency'
   ```

2. **Identificar endpoints lentos**
   - Revisar logs para requests específicos
   - Usar tracing (OpenTelemetry) para identificar bottlenecks

3. **Verificar recursos**
   - CPU usage
   - Memory usage
   - Database connections

4. **Revisar consultas a base de datos**
   - Verificar queries lentas
   - Revisar índices
   - Verificar pool de conexiones

5. **Escalar recursos si necesario**
   - Aumentar réplicas si usa Kubernetes
   - Aumentar recursos de base de datos

---

## Checklist de Respuesta a Incidentes

### Fase 1: Detección y Evaluación
- [ ] Confirmar que el incidente es real
- [ ] Clasificar severidad
- [ ] Notificar al equipo
- [ ] Crear ticket de incidente

### Fase 2: Contención
- [ ] Detener actividad que cause el problema
- [ ] Aislar componentes afectados
- [ ] Prevenir escalada

### Fase 3: Resolución
- [ ] Identificar causa raíz
- [ ] Implementar fix
- [ ] Verificar que el fix funciona
- [ ] Restaurar operaciones normales

### Fase 4: Post-Incidente
- [ ] Documentar incidente
- [ ] Realizar post-mortem
- [ ] Actualizar runbooks si necesario
- [ ] Implementar mejoras preventivas

## Comunicación

### Durante Incidente
- **Canal**: Slack #incidents
- **Frecuencia**: Actualizaciones cada 15 minutos para P1, cada hora para P2
- **Template de actualización**:
  ```
  [INCIDENT] <Título>
  Severidad: <P1/P2/P3>
  Estado: <Investigando/En Resolución/Resuelto>
  Impacto: <Descripción>
  Acciones tomadas: <Lista>
  Próximos pasos: <Lista>
  ```

### Post-Incidente
- **Reunión de post-mortem**: Dentro de 48 horas
- **Documento de post-mortem**: Incluir causa raíz, timeline, acciones preventivas

## Referencias

- [Operations Manual](../operations.md)
- [Risk Management Setup](../RISK_MANAGEMENT_SETUP.md)
- [Alert Configuration](./alerts.md)

