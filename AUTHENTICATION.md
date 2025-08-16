# Authentication System

This document describes the JWT-based authentication system implemented in the Trade Analytics application.

## Overview

The application uses **JWT (JSON Web Tokens)** for secure user authentication and authorization. This system ensures that users can only access their own trading data while maintaining development flexibility.

## Architecture

### Backend Authentication (`backend/app/core/security.py`)

The backend implements a two-tier authentication approach:

1. **Primary: JWT Token Validation**
2. **Fallback: Development Mode (for testing/development)**

```python
async def get_current_user_id(authorization: Optional[str] = Header(None)) -> uuid.UUID:
    """
    Get current authenticated user ID from JWT token.
    Falls back to development mode when no token provided.
    """
```

### Frontend Authentication (`frontend/src/lib/api.ts`)

The frontend automatically includes JWT tokens in all API requests:

```typescript
function getAuthHeaders(): Record<string, string> {
  const headers = { 'Cache-Control': 'no-cache' }
  const token = getAuthToken()
  if (token) {
    headers['Authorization'] = `Bearer ${token}`
  }
  return headers
}
```

## Authentication Flow

### 1. User Login

```mermaid
sequenceDiagram
    participant Frontend
    participant Backend
    participant Robinhood
    participant Database

    Frontend->>Backend: POST /auth/robinhood/login
    Backend->>Robinhood: Authenticate credentials
    Robinhood-->>Backend: Authentication result
    Backend->>Database: Find/create user record
    Database-->>Backend: User record
    Backend->>Backend: Generate JWT token
    Backend-->>Frontend: JWT token + user info
    Frontend->>Frontend: Store token in localStorage
```

**Endpoint:** `POST /api/v1/auth/robinhood/login`

**Request:**
```json
{
  "username": "robinhood_username",
  "password": "robinhood_password", 
  "mfa_code": "optional_6_digit_code"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Login successful",
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "user_info": {
    "user_id": "123e4567-e89b-12d3-a456-426614174000",
    "username": "robinhood_username",
    "email": "user@robinhood.local"
  }
}
```

### 2. Authenticated API Requests

```mermaid
sequenceDiagram
    participant Frontend
    participant Backend
    participant Database

    Frontend->>Backend: API Request + JWT Token
    Backend->>Backend: Validate JWT token
    Backend->>Backend: Extract user_id from token
    Backend->>Database: Query user-specific data
    Database-->>Backend: User data
    Backend-->>Frontend: API Response
```

**Headers:**
```
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

### 3. Token Storage and Management

**Frontend Storage:**
- `localStorage.setItem('auth_token', token)` - JWT token
- `localStorage.setItem('user_info', JSON.stringify(userInfo))` - User details
- `localStorage.setItem('robinhood_authenticated', 'true')` - Auth status

**Token Cleanup:**
- Automatic cleanup on logout
- Cleanup on 401 authentication errors
- Cleanup on authentication failures

## User Management

### User Record Creation

When a user successfully authenticates with Robinhood, the system:

1. **Checks for existing user** by `robinhood_username`
2. **Links to existing data** by finding user_id with options orders
3. **Creates new user record** if none exists
4. **Updates login timestamp** on each successful authentication

```python
async def get_or_create_user_for_robinhood_login(
    db: AsyncSession, 
    username: str,
    rh_service: RobinhoodService
) -> User:
    """Find or create user for Robinhood login"""
```

### User Data Model (`backend/app/models/user.py`)

```python
class User(Base):
    __tablename__ = "users"
    
    id = Column(UUID(as_uuid=True), primary_key=True)
    email = Column(String, unique=True, index=True, nullable=False)
    full_name = Column(String, nullable=True)
    robinhood_username = Column(String, nullable=True)
    last_login = Column(DateTime(timezone=True), nullable=True)
    # ... other fields
```

## JWT Token Details

### Token Configuration

- **Algorithm:** HS256 (HMAC with SHA-256)
- **Secret:** Configured via `JWT_SECRET` environment variable
- **Expiration:** Configurable via `ACCESS_TOKEN_EXPIRE_MINUTES` (default: 24 hours)

### Token Structure

```json
{
  "header": {
    "alg": "HS256",
    "typ": "JWT"
  },
  "payload": {
    "sub": "user_uuid_here",
    "exp": 1755965084
  },
  "signature": "verification_signature"
}
```

### Token Validation

```python
def verify_token(token: str) -> Optional[str]:
    """Verify and decode JWT token"""
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        user_id: str = payload.get("sub")
        return user_id
    except JWTError:
        return None
```

## Development Mode

### Exact User Authentication

For development and testing, the system uses a **specific target user ID** instead of random selection:

#### Target User Configuration

```python
# Exact user ID for development/demo authentication
TARGET_USER_ID = "13461768-f848-4c04-aea2-46817bc9a3a5"
```

**Key Properties:**
- **User ID:** `13461768-f848-4c04-aea2-46817bc9a3a5`
- **Order Count:** 1,902 options orders
- **Purpose:** Consistent authentication for development/testing
- **Data Source:** Complete trading history from database

### Fallback Authentication Logic

For development and testing, when no JWT token is provided:

1. **Use exact target user** with verified options orders data
2. **Verify user exists** in database before using
3. **Use demo user** as ultimate fallback only if target user unavailable
4. **Log authentication method** for debugging

```python
# Development fallback - use specific target user
target_user_id = "13461768-f848-4c04-aea2-46817bc9a3a5"

# Verify this user exists and has data
result = await db.execute(text("""
    SELECT user_id FROM options_orders 
    WHERE user_id = :user_id
    LIMIT 1
"""), {"user_id": target_user_id})

if result.scalar_one_or_none():
    return uuid.UUID(target_user_id)
```

#### Benefits of Exact User Authentication

- ✅ **Deterministic**: Always uses the same user, no random selection
- ✅ **Consistent**: Reliable access to full dataset (1,902 orders)
- ✅ **Predictable**: Eliminates user switching between requests
- ✅ **Complete Data**: Access to comprehensive trading history
- ✅ **Development Friendly**: No surprises during testing

### Demo User (Fallback Only)

- **ID:** `00000000-0000-0000-0000-000000000001`
- **Purpose:** Ultimate fallback when target user unavailable
- **Usage:** Only when target user verification fails
- **Data:** Limited demo data for basic testing

## API Endpoints

### Authentication Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/auth/robinhood/login` | Authenticate with Robinhood credentials |
| `POST` | `/auth/logout` | Logout from Robinhood session |
| `GET` | `/auth/status` | Check current authentication status |
| `GET` | `/auth/test-connectivity` | Test Robinhood API connectivity |

### Protected Endpoints

All portfolio, options, and analytics endpoints require authentication:

- `/options/orders` - Options trading history
- `/options/positions` - Current options positions  
- `/options/summary` - Portfolio summary
- `/portfolio/summary` - Overall portfolio data
- `/stocks/positions` - Stock positions
- And all other data endpoints...

## Error Handling

### Authentication Errors

**401 Unauthorized:**
```json
{
  "detail": "Could not validate credentials"
}
```

**Frontend Response:**
- Clear stored tokens
- Redirect to login page
- Show authentication error message

### Token Expiration

**Automatic Handling:**
- Backend returns 401 on expired tokens
- Frontend detects 401 and redirects to login
- User must re-authenticate

## Security Considerations

### Token Security

- **HTTP-Only Storage:** Tokens stored in localStorage (consider httpOnly cookies for production)
- **HTTPS Required:** Always use HTTPS in production
- **Secret Management:** JWT secrets stored in environment variables
- **Token Expiration:** Configurable expiration times

### Data Isolation

- **User-Specific Queries:** All database queries filtered by authenticated user_id
- **No Cross-User Access:** Users can only access their own trading data
- **Audit Logging:** Authentication attempts and user actions logged

### Development Security

- **Fallback Limitations:** Development fallback only in non-production environments
- **Demo User Isolation:** Demo user data clearly separated
- **Debug Logging:** Authentication flow logged for troubleshooting

## Environment Configuration

### Required Environment Variables

```bash
# JWT Configuration
JWT_SECRET=your-super-secret-jwt-key-here
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440

# Robinhood API
ROBINHOOD_USERNAME=your-robinhood-username
ROBINHOOD_PASSWORD=your-robinhood-password

# Database
DATABASE_URL=postgresql+asyncpg://user:password@localhost/tradeanalytics
```

### Development User Configuration

For development and testing environments, the system uses a specific target user:

```python
# backend/app/core/security.py
TARGET_USER_ID = "13461768-f848-4c04-aea2-46817bc9a3a5"

# backend/app/api/auth.py  
target_user_id = "13461768-f848-4c04-aea2-46817bc9a3a5"
```

**To change the target user:**

1. **Identify the desired user ID** from the database:
   ```sql
   SELECT user_id, COUNT(*) as order_count 
   FROM options_orders 
   WHERE user_id != '00000000-0000-0000-0000-000000000001'
   GROUP BY user_id 
   ORDER BY order_count DESC;
   ```

2. **Update the target user ID** in both files:
   - `backend/app/core/security.py` (line ~111)
   - `backend/app/api/auth.py` (line ~67)

3. **Restart the backend** to apply changes:
   ```bash
   docker-compose restart backend
   ```

**Verification:**
```bash
# Test authentication returns expected user data
curl -s "http://localhost:8000/api/v1/options/orders?limit=5" | jq '{total: .total}'
```

### Frontend Environment

```bash
# API Configuration
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## Testing

### Authentication Test Scenarios

1. **No Token (Development Fallback)**
   ```bash
   curl http://localhost:8000/api/v1/options/orders?limit=2
   ```

2. **Invalid Token (Should Reject)**
   ```bash
   curl -H "Authorization: Bearer invalid_token" http://localhost:8000/api/v1/options/orders
   ```

3. **Valid Token (Should Authenticate)**
   ```bash
   curl -H "Authorization: Bearer <valid_jwt>" http://localhost:8000/api/v1/options/orders
   ```

4. **Login Flow (Should Return Token)**
   ```bash
   curl -X POST http://localhost:8000/api/v1/auth/robinhood/login \
     -H "Content-Type: application/json" \
     -d '{"username":"test","password":"test"}'
   ```

### Frontend Testing

1. **Login Page:** Visit `http://localhost:3000/login`
2. **Dashboard Access:** Verify authentication status
3. **Token Storage:** Check localStorage for tokens
4. **API Calls:** Verify Authorization headers in network tab

## Troubleshooting

### Common Issues

**1. "Could not validate credentials"**
- Check JWT_SECRET configuration
- Verify token is not expired
- Ensure token format is correct

**2. "No options orders found"**
- User may not have trading history
- Check user_id linking to orders table
- Verify database connection

**3. Development fallback not working**
- Check if target user exists in database: `13461768-f848-4c04-aea2-46817bc9a3a5`
- Verify target user has options orders data
- Check database connectivity
- Verify exact user ID is correct

**4. Frontend not sending tokens**
- Verify token storage in localStorage
- Check API client getAuthHeaders() function
- Inspect network requests for Authorization header

### Debug Logging

Enable debug logging to troubleshoot authentication:

```python
import logging
logging.getLogger("app.core.security").setLevel(logging.DEBUG)
```

Look for logs like:
- `"Authenticated user from JWT: <user_id>"`
- `"Development fallback: Using target user: 13461768-f848-4c04-aea2-46817bc9a3a5"`
- `"No actual user found, using demo user ID: <demo_id>"`

## Migration from Previous System

The previous system used a simple fallback mechanism. The new JWT system:

### Before (Random User Selection)
```python
# Previously used random/highest-count user selection
async def get_current_user_id() -> uuid.UUID:
    # Find any user with orders data (inconsistent)
    # Or user with most orders (not user-specific)
    # Return demo user if none found
```

### After (Exact User + JWT)
```python
# Primary: JWT validation, Fallback: exact target user
async def get_current_user_id(authorization: Optional[str] = Header(None)) -> uuid.UUID:
    # 1. Validate JWT token if provided
    # 2. Fall back to exact target user for development
    # 3. Ultimate fallback to demo user
    
    target_user_id = "13461768-f848-4c04-aea2-46817bc9a3a5"
```

### Migration Benefits

- **Proper Authentication:** Real user authentication with Robinhood credentials
- **Exact User Identification:** Uses specific target user instead of random selection
- **Deterministic Behavior:** Consistent user identification across requests
- **Complete Data Access:** Access to full trading history (1,902 orders)
- **Security:** User data isolation and secure token handling
- **Flexibility:** Maintains development/testing capabilities
- **Scalability:** Supports multiple authenticated users
- **Auditability:** Login tracking and authentication logging

---

## Next Steps

### Production Enhancements

1. **Refresh Tokens:** Implement token refresh mechanism
2. **Session Management:** Add session timeout and cleanup
3. **Rate Limiting:** Add authentication rate limiting
4. **Audit Logging:** Enhanced authentication event logging
5. **Multi-Factor Auth:** Additional MFA options beyond Robinhood

### Security Hardening

1. **HTTP-Only Cookies:** Move tokens from localStorage to httpOnly cookies
2. **CSRF Protection:** Add CSRF tokens for state-changing operations
3. **Token Encryption:** Encrypt tokens at rest
4. **Security Headers:** Add comprehensive security headers

### Monitoring

1. **Authentication Metrics:** Track login success/failure rates
2. **Token Analytics:** Monitor token usage and expiration
3. **User Activity:** Track authenticated user actions
4. **Security Alerts:** Alert on suspicious authentication patterns