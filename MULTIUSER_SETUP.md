# Multi-User Setup - HouseHunter

## Overview

HouseHunter now supports multi-user isolation with a hybrid approach:
- **Anonymous Users**: Automatic UUID generation for casual users (no signup required)
- **Registered Users**: Optional account creation for cross-device sync

## How It Works

### 1. Anonymous Users (Default)
- Each browser automatically gets a unique UUID stored in localStorage
- UUID is sent with every API request via `X-User-ID` header
- Houses are isolated per UUID
- Data persists in the database at `/database/househunter.db`

### 2. Registered Users (Optional)
- Click "Login" in the top-right corner
- Create account with email/password
- User ID becomes `user_{account_id}` instead of UUID
- Sync houses across multiple devices with same login

## Technical Details

### Database Schema
```sql
-- Users table (for optional accounts)
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Houses table (with user_id isolation)
CREATE TABLE houses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,  -- UUID or "user_{id}"
    address TEXT NOT NULL,
    features TEXT NOT NULL,
    notes TEXT,
    score INTEGER NOT NULL,
    score_breakdown TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### API Changes

All house endpoints now require `X-User-ID` header:

```bash
# Get houses for current user
curl -H "X-User-ID: your-uuid-here" http://localhost:7777/houses

# Add a house
curl -X POST -H "X-User-ID: your-uuid-here" \
  -H "Content-Type: application/json" \
  -d '{"address":"123 Main St", ...}' \
  http://localhost:7777/add_house
```

### New Endpoints

**POST /register** - Create account
```json
{
  "email": "user@example.com",
  "password": "yourpassword"
}
```

**POST /login** - Login
```json
{
  "email": "user@example.com",
  "password": "yourpassword"
}
```

## Frontend Implementation

### User ID Generation
```javascript
// Auto-generates UUID on first visit
function getUserId() {
    // Check if logged in
    const authUser = localStorage.getItem('househunter_auth_user');
    if (authUser) {
        return `user_${JSON.parse(authUser).id}`;
    }
    
    // Otherwise use anonymous UUID
    let userId = localStorage.getItem('househunter_user_id');
    if (!userId) {
        userId = crypto.randomUUID();
        localStorage.setItem('househunter_user_id', userId);
    }
    return userId;
}
```

### Header Injection
```javascript
// All fetch requests include X-User-ID header
fetch('/houses', {
    headers: {
        'X-User-ID': getUserId()
    }
})
```

## Migration Notes

- Existing houses without `user_id` are assigned to `'legacy'` user
- Old database will auto-migrate on first run with new code
- No data loss - existing houses remain accessible

## Security Notes

⚠️ **Current Implementation**:
- Passwords are hashed with SHA-256 (basic security)
- No JWT tokens (user ID sent in header)
- Suitable for personal use or trusted networks

🔒 **For Production**:
- Upgrade to bcrypt/argon2 for password hashing
- Implement JWT or session tokens
- Add HTTPS/TLS
- Add rate limiting on auth endpoints
- Add CORS protection

## Testing

### Test Anonymous User Isolation
1. Open browser 1, add a house
2. Open browser 2 (different UUID), verify you don't see browser 1's house
3. Each browser maintains separate houses

### Test Account Sync
1. Register account in browser 1
2. Add houses while logged in
3. Login with same account in browser 2
4. Verify houses appear in browser 2

### Test Database Persistence
```bash
# Inside container
docker exec -it househunter-app /bin/sh
python3 -c "import sqlite3; conn = sqlite3.connect('/database/househunter.db'); cursor = conn.cursor(); cursor.execute('SELECT user_id, address FROM houses'); print(cursor.fetchall())"
```

## Deployment

No changes to docker-compose needed - the volume mapping already works:
```yaml
volumes:
  - ./database:/database  # Persists multi-user database
```

Rebuild container:
```bash
docker-compose down
docker-compose up -d --build
```
