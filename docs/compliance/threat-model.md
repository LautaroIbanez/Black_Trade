# Threat Model - Black Trade Platform

## Resumen

Este documento describe el análisis de amenazas de seguridad para la plataforma Black Trade y las medidas de mitigación implementadas.

## Modelo de Amenazas

### Actores

#### 1. Usuarios Externos
- **Traders**: Usuarios legítimos del sistema
- **Atacantes Externos**: Individuos o grupos intentando comprometer el sistema
- **Bots/Scripts**: Automatización maliciosa

#### 2. Usuarios Internos
- **Operadores**: Personal autorizado
- **Desarrolladores**: Equipo técnico
- **Administradores**: Acceso completo al sistema

### Activos a Proteger

1. **Información Financiera**
   - Saldos de cuentas
   - Historial de transacciones
   - API keys de exchanges
   - Configuración de estrategias

2. **Datos Personales**
   - Información de usuarios (KYC/AML)
   - Credenciales de acceso
   - Logs de actividad

3. **Sistema de Trading**
   - Motor de ejecución
   - Límites de riesgo
   - Órdenes pendientes/activas

## Amenazas Identificadas

### STRIDE Analysis

#### 1. Spoofing (Suplantación)

**Amenazas**:
- Suplantación de usuarios legítimos
- Suplantación de APIs externas (exchanges)
- Suplantación de servicios internos

**Mitigaciones**:
- Autenticación robusta (JWT, OAuth2)
- Validación de certificados TLS para APIs externas
- Rate limiting por usuario/IP
- Logging de intentos de acceso fallidos

#### 2. Tampering (Manipulación)

**Amenazas**:
- Manipulación de órdenes en tránsito
- Modificación de límites de riesgo
- Alteración de datos históricos

**Mitigaciones**:
- TLS/HTTPS para todas las comunicaciones
- Firmas digitales para órdenes críticas
- Checksums para integridad de datos
- Logs inmutables para auditoría

#### 3. Repudiation (Repudio)

**Amenazas**:
- Negación de ejecución de órdenes
- Negación de cambios en configuración
- Negación de acceso a recursos

**Mitigaciones**:
- Logging completo de todas las acciones
- Firmas digitales en transacciones
- Auditoría de cambios críticos
- Timestamps verificables

#### 4. Information Disclosure (Divulgación)

**Amenazas**:
- Exposición de API keys
- Filtración de datos financieros
- Divulgación de información personal

**Mitigaciones**:
- Secret management (Vault, AWS Secrets Manager)
- Encriptación de datos sensibles en reposo
- Encriptación de datos en tránsito (TLS)
- Control de acceso basado en roles (RBAC)
- Sanitización de logs

#### 5. Denial of Service (DoS)

**Amenazas**:
- Sobrecarga de API
- Ataques DDoS
- Agotamiento de recursos

**Mitigaciones**:
- Rate limiting por IP/usuario
- Timeouts en requests
- Límites de recursos por usuario
- Circuit breakers
- Monitoreo y alertas

#### 6. Elevation of Privilege (Elevación)

**Amenazas**:
- Escalamiento de privilegios de usuarios
- Acceso no autorizado a funciones admin
- Bypass de controles de riesgo

**Mitigaciones**:
- Principio de menor privilegio
- Validación de permisos en cada endpoint
- Separación de roles y responsabilidades
- Auditoría de cambios de permisos

## Escenarios de Ataque

### Escenario 1: Compromiso de API Key

**Descripción**: Atacante obtiene acceso a API keys de exchange

**Impacto**: ALTO - Pérdidas financieras potenciales

**Mitigaciones**:
- Secret management seguro
- Rotación regular de keys
- IP whitelisting en exchange
- Monitoreo de actividad anómala
- Límites de retirada

### Escenario 2: Manipulación de Límites de Riesgo

**Descripción**: Usuario malicioso intenta modificar límites para aumentar exposición

**Impacto**: ALTO - Riesgo financiero

**Mitigaciones**:
- Control de acceso estricto (solo risk managers)
- Auditoría de todos los cambios
- Validación de límites antes de aplicar
- Alertas automáticas de cambios

### Escenario 3: Ataque de Rate Limiting

**Descripción**: Atacante satura API con requests

**Impacto**: MEDIO - Degradación de servicio

**Mitigaciones**:
- Rate limiting por IP/usuario
- CAPTCHA para requests sospechosos
- Blacklist de IPs
- Monitoreo y auto-bloqueo

### Escenario 4: Inyección SQL

**Descripción**: Atacante intenta inyectar código SQL malicioso

**Impacto**: ALTO - Compromiso de base de datos

**Mitigaciones**:
- Uso de ORM (SQLAlchemy) con parameterized queries
- Validación de entrada
- Principio de menor privilegio en DB
- Monitoreo de queries anómalas

### Escenario 5: XSS (Cross-Site Scripting)

**Descripción**: Atacante inyecta scripts maliciosos en frontend

**Impacto**: MEDIO - Compromiso de sesión de usuario

**Mitigaciones**:
- Sanitización de entrada
- Content Security Policy (CSP)
- HttpOnly cookies
- Validación de datos en frontend y backend

## Matriz de Riesgo

| Amenaza | Probabilidad | Impacto | Riesgo | Prioridad |
|---------|--------------|---------|--------|-----------|
| Compromiso de API Key | Media | Alto | Alto | 1 |
| Manipulación de Riesgo | Baja | Alto | Medio | 2 |
| DoS/DDoS | Alta | Medio | Medio | 3 |
| Inyección SQL | Baja | Alto | Medio | 4 |
| XSS | Media | Medio | Medio | 5 |
| Exposición de Datos | Media | Alto | Alto | 1 |

## Plan de Mitigación

### Fase 1: Crítico (Implementado)
- ✅ Secret management
- ✅ TLS/HTTPS
- ✅ Rate limiting
- ✅ Logging de auditoría
- ✅ Autenticación y autorización

### Fase 2: Importante (En progreso)
- 🔄 Rotación de secrets
- 🔄 Monitoreo de anomalías
- 🔄 Hardening de base de datos
- 🔄 Penetration testing

### Fase 3: Mejora Continua
- 📋 Revisiones periódicas de seguridad
- 📋 Actualización de dependencias
- 📋 Training de seguridad
- 📋 Bug bounty program

## Referencias

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [STRIDE Threat Modeling](https://docs.microsoft.com/en-us/azure/security/develop/threat-modeling-tool-threats)

