# Testing the Search Houses Feature

## Prerequisites
1. Ensure Docker container is running
2. Ensure `RAPIDAPI_KEY` environment variable is set in docker-compose.yml
3. Have a registered user account (or create one during testing)

## Test Cases

### Test 1: Access Control (Anonymous User)
**Steps**:
1. Open application (don't login)
2. Click "Search Houses" tab
3. Verify login notice appears: "🔒 Login Required..."
4. Verify search form is hidden
5. Click "Login or Create Account" button
6. Verify auth modal opens

**Expected Result**: Anonymous users cannot access search feature

---

### Test 2: Basic Search (Registered User)
**Steps**:
1. Login or create account
2. Click "Search Houses" tab
3. Enter ZIP code: `80303` (Boulder, CO)
4. Enter max price: `700000`
5. Click "Search Properties"
6. Wait for results

**Expected Result**: 
- Shows loading state ("⏳ Searching...")
- Displays list of properties under $700k
- Each property shows: photo, address, price, beds, baths, sqft, garage
- "Add to My Houses" button on each property

---

### Test 3: Add Search Result to Houses
**Steps**:
1. Complete Test 2 first
2. Click "Add to My Houses" on any search result
3. Wait for confirmation

**Expected Result**:
- Success message appears
- Automatically switches to "Add a House" tab
- Property appears in "Your Houses" list on right
- Property has initial score based on basic features
- Property has photo (if available in search)
- Property has price displayed

---

### Test 4: Edit Added Property
**Steps**:
1. Complete Test 3 first
2. Find the added property in "Your Houses"
3. Click "Edit" button
4. Add custom features (deck, pool, nice backyard, etc.)
5. Click "Update House"

**Expected Result**:
- Form populates with existing data
- Can modify all fields
- Score updates based on new features
- Property updates in list with new score

---

### Test 5: Invalid ZIP Code
**Steps**:
1. Login
2. Click "Search Houses" tab
3. Enter invalid ZIP: `1234` (only 4 digits)
4. Click "Search Properties"

**Expected Result**: 
- HTML5 validation error (pattern mismatch)
- Form doesn't submit

---

### Test 6: No Properties Found
**Steps**:
1. Login
2. Click "Search Houses" tab
3. Enter ZIP code: `99999` (unlikely to have properties)
4. Enter max price: `100000`
5. Click "Search Properties"

**Expected Result**:
- Alert message: "No properties found in ZIP code 99999..."
- Search results container stays hidden

---

### Test 7: Cache Hit (Performance)
**Steps**:
1. Complete Test 2 first (search 80303, $700k)
2. Click "Add a House" tab
3. Click "Search Houses" tab again
4. Enter same ZIP: `80303`
5. Enter same max price: `700000`
6. Click "Search Properties"

**Expected Result**:
- Results appear much faster (from cache)
- Console shows "Cache hit for ZIP 80303..."
- Same properties displayed

---

### Test 8: Tab Switching
**Steps**:
1. Login
2. Click "Search Houses" tab
3. Verify search form shows
4. Click "Add a House" tab
5. Verify add house form shows
6. Click "Search Houses" tab again
7. Verify search form still shows (doesn't require re-login check)

**Expected Result**: Smooth tab switching without data loss

---

### Test 9: Multiple Properties from Search
**Steps**:
1. Complete Test 2 (get search results)
2. Click "Add to My Houses" on 3 different properties
3. Check "Your Houses" list

**Expected Result**:
- All 3 properties added successfully
- Each has unique address and score
- All sorted by score (highest first)

---

### Test 10: Photo Loading
**Steps**:
1. Search for properties with photos (80303, $700k)
2. Find result with photo
3. Click "Add to My Houses"
4. Wait for property to appear
5. Verify photo shows in "Your Houses"

**Expected Result**:
- Photo from search result is converted to base64
- Photo persists in database
- Photo displays in house card

---

## Common ZIP Codes for Testing

| ZIP Code | Location | Typical Price Range |
|----------|----------|-------------------|
| 80303 | Boulder, CO | $500k - $2M |
| 94102 | San Francisco, CA | $800k - $5M |
| 10001 | New York, NY | $600k - $10M |
| 90210 | Beverly Hills, CA | $2M - $50M |
| 33139 | Miami Beach, FL | $400k - $10M |
| 78701 | Austin, TX | $400k - $2M |
| 98101 | Seattle, WA | $500k - $3M |

## Debugging

### Check Backend Logs
```bash
docker-compose logs -f app
```

Look for:
- "Cache hit for ZIP..." or "Cache miss for ZIP..."
- "Cached X properties for ZIP code..."
- Any error messages from RapidAPI

### Check Browser Console
- Open DevTools (F12)
- Check Console tab for:
  - "Search error:" messages
  - API response data
  - JavaScript errors

### Verify Database
Properties should be cached in `database/property_cache.db`:
```bash
docker-compose exec app python -c "
from app.property_cache import get_cached_properties_by_zip
props = get_cached_properties_by_zip('80303')
print(f'Found {len(props)} cached properties')
"
```

## Troubleshooting

### Issue: "RapidAPI key not configured"
**Solution**: Check docker-compose.yml has RAPIDAPI_KEY set

### Issue: "403 Forbidden from API"
**Solution**: Verify RapidAPI subscription is active for "Realty in US" API

### Issue: Photos not loading in search results
**Solution**: 
- Check if API returned photo_url
- Verify image URLs are accessible (not behind authentication)
- Check browser console for CORS errors

### Issue: Search button disabled
**Solution**: Ensure user is logged in (not anonymous)

### Issue: Properties not adding to list
**Solution**: 
- Check browser console for errors
- Verify user is logged in
- Check backend logs for database errors
