# Guía de Uso - Black Trade

## Inicio Rápido

### 1. Prerrequisitos

- Python 3.10+
- Node.js 18+
- PostgreSQL (para persistencia de usuarios y KYC)
- Git

### 2. Configuración Inicial

```bash
# 1. Clonar el repositorio (si aún no lo tienes)
git clone <repo-url>
cd Black_Trade

# 2. Crear archivo .env con configuración
cp .env.example .env
# Editar .env y configurar:
# - DATABASE_URL (ej: postgresql://user:password@localhost:5432/black_trade)
# - JWT_SECRET (clave secreta para tokens)
# - BINANCE_API_KEY (opcional, para datos reales)
# - BINANCE_API_SECRET (opcional)
```

### 3. Instalación de Dependencias

```bash
# Backend
pip install -r requirements.txt

# Frontend
cd frontend
npm install
cd ..
```

### 4. Inicializar Base de Datos

```bash
# Ejecutar migraciones para crear tablas
python -m backend.db.init_db
# O si usas Alembic:
alembic upgrade head
```

### 5. Iniciar la Aplicación

**Terminal 1 - Backend:**
```bash
uvicorn backend.app:app --reload --port 8000
```

**Terminal 2 - Frontend:**
```bash
cd frontend
npm run dev
```

El frontend estará disponible en: **http://localhost:5173**
El backend API estará en: **http://localhost:8000**

## Uso del Sistema de Autenticación

### Registro de Usuario

1. **Abrir la aplicación**: Navegar a http://localhost:5173
2. **Registro inicial**: El sistema mostrará el formulario de registro si no hay sesión activa
3. **Completar registro**:
   - Username: Tu nombre de usuario (ej: "trader1")
   - Email: Tu email (ej: "trader1@example.com")
   - Country: Tu país (ej: "AR")
   - Role: Seleccionar rol (viewer/trader/risk_manager/admin)

4. **Guardar credenciales**: El sistema guardará automáticamente:
   - Access token
   - Refresh token
   - User ID
   - Username
   - Role

### Verificación KYC

Para acceder a endpoints protegidos (recomendaciones, riesgo), necesitas verificar KYC:

```bash
# Usar el endpoint de verificación
POST /api/auth/verify
{
  "user_id": "user_abc123def456",
  "document_type": "passport",
  "document_number": "ABC123"
}
```

O desde el frontend, completar el formulario de verificación KYC.

### Inicio de Sesión

Si ya tienes una cuenta:

1. El sistema intentará restaurar la sesión automáticamente usando el refresh token
2. Si el token expiró, usarás el username guardado para reautenticarte
3. **Importante**: El sistema preserva el username original, nunca usa user_id como username

### Flujo de Refresh de Token

El sistema maneja automáticamente la renovación de tokens:

1. **Token expira**: Cuando el access token expira (12 horas)
2. **Refresh automático**: El frontend detecta el 401 y llama a `refreshAccessToken()`
3. **Preservación de identidad**: El sistema:
   - Preserva el username original del localStorage
   - Obtiene nuevos tokens del backend
   - Actualiza tokens manteniendo el mismo user_id y username
4. **KYC persistente**: El estado de verificación KYC se mantiene porque el user_id no cambia

## Uso de la Aplicación

### Dashboard Principal

1. **Acceder al dashboard**: Una vez autenticado y verificado KYC
2. **Ver recomendaciones**: El dashboard muestra:
   - Recomendación actual (LONG/SHORT/FLAT)
   - Nivel de confianza
   - Niveles de entrada, stop loss y take profit
   - Gráficos interactivos

### Refrescar Datos

```bash
# Desde el frontend: Click en botón "Refresh"
# O desde API:
POST http://localhost:8000/refresh
```

Esto:
- Descarga datos históricos de Binance
- Ejecuta backtests en todas las estrategias
- Genera nueva recomendación

### Ver Métricas de Estrategias

```bash
GET http://localhost:8000/strategies/info?timeframe=1h
```

O desde el frontend, navegar a la pestaña "Strategies" y seleccionar timeframe.

### Acceder a Datos de Riesgo

```bash
# Requiere KYC verificado
GET http://localhost:8000/api/risk/status
Headers: Authorization: Bearer <access_token>
```

## Pruebas de los Cambios Recientes

### Probar Preservación de Identidad

1. **Registrar usuario**:
```bash
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "username": "test_user",
    "email": "test@example.com",
    "country": "AR",
    "role": "trader"
  }'
```

2. **Guardar refresh_token** del response

3. **Verificar KYC**:
```bash
curl -X POST http://localhost:8000/api/auth/verify \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "<user_id_del_paso_1>"
  }'
```

4. **Refrescar token múltiples veces**:
```bash
curl -X POST http://localhost:8000/api/auth/refresh \
  -H "Content-Type: application/json" \
  -d '{
    "refresh_token": "<refresh_token>"
  }'
```

5. **Verificar que user_id y username se mantienen constantes** en cada respuesta

6. **Acceder a endpoint protegido**:
```bash
curl http://localhost:8000/api/recommendations/live \
  -H "Authorization: Bearer <nuevo_access_token>"
```

Debería funcionar sin requerir nueva verificación KYC.

### Probar Frontend

1. **Abrir navegador**: http://localhost:5173
2. **Abrir DevTools**: F12 → Application → Local Storage
3. **Verificar claves guardadas**:
   - `bt_auth_token`
   - `bt_refresh_token`
   - `bt_user_id`
   - `bt_username` (debe ser diferente de user_id)
   - `bt_user_role`

4. **Simular expiración de token**: Esperar 12 horas o limpiar `bt_auth_token` manualmente
5. **Refrescar página**: El sistema debe restaurar sesión automáticamente
6. **Verificar que username se preserva**: Comprobar que `bt_username` no se convierte en user_id

## Ejecutar Tests

### Tests Backend

```bash
# Todos los tests
pytest

# Tests específicos de autenticación
pytest tests/api/test_auth_flow.py -v

# Tests de persistencia KYC
pytest tests/services/test_kyc_persistence.py -v

# Tests de singleton AuthService
pytest tests/services/test_auth_singleton.py -v
```

### Tests Frontend

```bash
cd frontend
npm test

# Tests con UI
npm run test:ui

# Cobertura
npm run test:coverage
```

## Solución de Problemas

### Error: "User not found in persistent store"

- Verificar que la base de datos esté corriendo
- Ejecutar migraciones: `python -m backend.db.init_db`
- Verificar DATABASE_URL en .env

### Error: "KYC verification required"

- Completar verificación KYC en `/api/auth/verify`
- Verificar que el user_id usado sea el correcto
- Comprobar en base de datos: `SELECT * FROM kyc_users WHERE user_id = '<user_id>'`

### Error: Token expira pero username se pierde

- Verificar que `refreshAccessToken()` esté preservando el username original
- Revisar localStorage: `bt_username` no debe convertirse en `user_id`
- Ver logs del frontend en DevTools Console

### Error: "Cannot use user_id as username"

- El backend detecta cuando se intenta usar user_id como username
- Si ocurre, el sistema intenta encontrar el usuario por user_id y usar su username real
- Verificar que el frontend esté usando `username` correcto en login/register

## Estructura de Datos Persistidos

### Tabla `users`
- `user_id`: Identificador único e inmutable
- `username`: Nombre de usuario para autenticación
- `email`: Email (usado para consolidación de identidad)
- `role`: Rol del usuario

### Tabla `kyc_users`
- `user_id`: Referencia a users
- `verified`: Boolean de verificación
- `verified_at`: Timestamp de verificación

### Tabla `user_tokens`
- `user_id`: Referencia a users
- `token`: Token JWT
- `token_type`: 'access' o 'refresh'
- `expires_at`: Fecha de expiración

## Flujo Completo de Usuario

```
1. Usuario abre aplicación
   ↓
2. Sistema verifica localStorage
   ↓
3a. Si hay token válido → Acceso directo
3b. Si hay refresh token → Renovar tokens
3c. Si hay username → Login automático
3d. Si no hay nada → Mostrar registro/login
   ↓
4. Usuario se autentica
   ↓
5. Sistema guarda: token, refresh_token, user_id, username
   ↓
6. Usuario verifica KYC
   ↓
7. Usuario accede a funcionalidades protegidas
   ↓
8. Cuando token expira → Refresh automático preservando identidad
   ↓
9. KYC se mantiene porque user_id es constante
```

## Comandos Útiles

```bash
# Ver estado de la API
curl http://localhost:8000/

# Verificar estado de autenticación
curl http://localhost:8000/api/auth/kyc-status \
  -H "Content-Type: application/json" \
  -d '{"user_id": "<user_id>"}'

# Ver logs del backend
tail -f logs/app.log

# Ejecutar migraciones
alembic upgrade head

# Reiniciar base de datos (CUIDADO: borra datos)
python -m backend.db.init_db --reset
```

## Recursos Adicionales

- **Documentación de API**: `docs/api/`
- **Guía de Autenticación**: `docs/authentication.md`
- **Runbook KYC**: `docs/runbooks/auth_kyc.md`
- **Guía Frontend**: `docs/frontend/auth.md`
- **QA Status**: `docs/qa/status.md`
