# HouseHunter Multi-User Architecture

## System Flow Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                         Browser 1                               │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ localStorage:                                             │  │
│  │   househunter_user_id: "abc-123-uuid"                   │  │
│  │   OR                                                      │  │
│  │   househunter_auth_user: {"id": 5, "email": "..."}      │  │
│  └──────────────────────────────────────────────────────────┘  │
│                           ↓                                     │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ JavaScript: getUserId()                                   │  │
│  │   → Returns: "abc-123-uuid" OR "user_5"                  │  │
│  └──────────────────────────────────────────────────────────┘  │
│                           ↓                                     │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ fetch('/houses', {                                        │  │
│  │   headers: { 'X-User-ID': 'abc-123-uuid' }              │  │
│  │ })                                                        │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              ↓
                    HTTP Request with Header
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                    FastAPI Backend                              │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ @app.get("/houses")                                       │  │
│  │ async def get_houses(                                     │  │
│  │     user_id: str = Header(alias="X-User-ID")            │  │
│  │ ):                                                        │  │
│  │     # Extract user_id from header                        │  │
│  │     houses = db.get_all_houses(user_id)                 │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              ↓
                     Database Query
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│               SQLite Database (/database/househunter.db)        │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ SELECT * FROM houses                                      │  │
│  │ WHERE user_id = 'abc-123-uuid'                           │  │
│  │ ORDER BY score DESC                                       │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ houses table:                                             │  │
│  │ ┌────┬─────────────────┬──────────────┬───────┬──────┐  │  │
│  │ │ id │ user_id         │ address      │ score │ ...  │  │  │
│  │ ├────┼─────────────────┼──────────────┼───────┼──────┤  │  │
│  │ │ 1  │ abc-123-uuid    │ 123 Main St  │ 85    │ ...  │  │  │
│  │ │ 2  │ xyz-456-uuid    │ 456 Oak Ave  │ 92    │ ...  │  │  │
│  │ │ 3  │ user_5          │ 789 Pine Rd  │ 78    │ ...  │  │  │
│  │ │ 4  │ abc-123-uuid    │ 321 Elm Blvd │ 81    │ ...  │  │  │
│  │ └────┴─────────────────┴──────────────┴───────┴──────┘  │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

## User Type Comparison

### Anonymous User (UUID)
```
Browser Visit → Generate UUID → Store in localStorage
                     ↓
              "abc-123-uuid"
                     ↓
         Send with every API call
                     ↓
         Database filters by UUID
                     ↓
    Only sees houses with matching UUID
```

### Registered User (Account)
```
User Registers → Create account in users table
                     ↓
              {id: 5, email: "user@example.com"}
                     ↓
         Store in localStorage as auth_user
                     ↓
         Convert to "user_5" for X-User-ID
                     ↓
         Database filters by "user_5"
                     ↓
    Sees houses across all devices with same login
```

## Data Flow Examples

### Example 1: Anonymous User Adds House
```
1. Browser generates UUID: "abc-123-uuid"
2. User fills form and submits
3. JavaScript: fetch('/add_house', {
     headers: { 'X-User-ID': 'abc-123-uuid' },
     body: {...houseData}
   })
4. Backend: db.add_house(user_id="abc-123-uuid", ...)
5. Database: INSERT INTO houses (user_id, address, ...)
            VALUES ('abc-123-uuid', '123 Main St', ...)
6. House is now tied to 'abc-123-uuid'
```

### Example 2: User Registers Account
```
1. User clicks "Register" in UI
2. Enters email/password
3. JavaScript: fetch('/register', {
     body: {email: "test@test.com", password: "pass123"}
   })
4. Backend: 
   - Hash password with SHA-256
   - INSERT INTO users (email, password_hash)
   - Return {id: 5, email: "test@test.com"}
5. JavaScript stores in localStorage:
   - househunter_auth_user = {"id": 5, "email": "test@test.com"}
6. Future requests use "user_5" as X-User-ID
```

### Example 3: Cross-Device Sync
```
Device A (Chrome):
  - Login → localStorage stores {"id": 5, "email": "..."}
  - Add house → X-User-ID: "user_5"
  - Database: INSERT ... user_id='user_5'

Device B (Firefox):
  - Login with same account → localStorage stores {"id": 5, "email": "..."}
  - Load houses → X-User-ID: "user_5"
  - Database: SELECT * WHERE user_id='user_5'
  - Result: Sees houses from Device A! ✅
```

## Security Layer

```
┌─────────────────────────────────────────────────────────────┐
│ Request: GET /houses                                        │
│ Header: X-User-ID: abc-123-uuid                            │
└─────────────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────┐
│ Backend validates:                                          │
│   ✓ user_id is not None                                    │
│   ✓ user_id is string                                      │
│   (No JWT verification in current version)                 │
└─────────────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────┐
│ Database query:                                             │
│   SELECT * FROM houses WHERE user_id = ?                   │
│   ↓                                                         │
│   Only returns houses matching user_id                     │
│   Other users' houses are invisible                        │
└─────────────────────────────────────────────────────────────┘
```

## Storage Locations

```
┌────────────────────────────────────────────────────────────────┐
│ Client Side (Browser)                                          │
├────────────────────────────────────────────────────────────────┤
│ localStorage:                                                  │
│   - househunter_user_id: "uuid"        (anonymous user)       │
│   - househunter_auth_user: {...}       (logged in user)       │
│   - househunter_houses: [...]          (backup/cache)         │
└────────────────────────────────────────────────────────────────┘
                              ↕
┌────────────────────────────────────────────────────────────────┐
│ Server Side (Docker Container)                                 │
├────────────────────────────────────────────────────────────────┤
│ /database/househunter.db (SQLite)                             │
│   - users table         (optional accounts)                    │
│   - houses table        (all houses with user_id)             │
└────────────────────────────────────────────────────────────────┘
                              ↕
┌────────────────────────────────────────────────────────────────┐
│ Host Machine (Persistent)                                      │
├────────────────────────────────────────────────────────────────┤
│ ./database/househunter.db  (volume mapped)                    │
│   - Survives container restarts                               │
│   - Can be backed up                                          │
└────────────────────────────────────────────────────────────────┘
```
