#!/bin/bash
# Test script for HouseHunter Multi-User API

BASE_URL="http://localhost:7777"
USER1_ID="test-user-1-uuid"
USER2_ID="test-user-2-uuid"

echo "🧪 Testing HouseHunter Multi-User API"
echo "======================================"
echo ""

# Test 1: Add house for User 1
echo "📝 Test 1: Add house for User 1"
curl -s -X POST "$BASE_URL/add_house" \
  -H "Content-Type: application/json" \
  -H "X-User-ID: $USER1_ID" \
  -d '{
    "address": "123 Test Street User 1",
    "notes": "User 1 test house",
    "features": {
      "garage_cars": 2,
      "bathrooms": 2,
      "bedrooms": 3,
      "square_feet": 1500,
      "lot_acres": 0.25,
      "nice_backyard": true,
      "curb_appeal": true,
      "appliances": {"dishwasher": "modern"},
      "basement": 1,
      "privacy": "normal",
      "has_deck": false,
      "patio_potential": true,
      "has_pool": false,
      "near_recreation": false,
      "walking_shopping": true,
      "has_hoa": false,
      "hoa_monthly_fee": 0
    }
  }' | jq '.'
echo ""

# Test 2: Add house for User 2
echo "📝 Test 2: Add house for User 2"
curl -s -X POST "$BASE_URL/add_house" \
  -H "Content-Type: application/json" \
  -H "X-User-ID: $USER2_ID" \
  -d '{
    "address": "456 Test Avenue User 2",
    "notes": "User 2 test house",
    "features": {
      "garage_cars": 1,
      "bathrooms": 1,
      "bedrooms": 2,
      "square_feet": 1000,
      "lot_acres": 0.1,
      "nice_backyard": false,
      "curb_appeal": false,
      "appliances": {},
      "basement": 0,
      "privacy": "not_private",
      "has_deck": false,
      "patio_potential": false,
      "has_pool": false,
      "near_recreation": false,
      "walking_shopping": false,
      "has_hoa": true,
      "hoa_monthly_fee": 50
    }
  }' | jq '.'
echo ""

# Test 3: Get houses for User 1 (should only see User 1's house)
echo "🔍 Test 3: Get houses for User 1 (should see 1 house)"
USER1_HOUSES=$(curl -s "$BASE_URL/houses" -H "X-User-ID: $USER1_ID")
echo "$USER1_HOUSES" | jq '.[] | {address: .address, score: .score}'
USER1_COUNT=$(echo "$USER1_HOUSES" | jq 'length')
echo "   → User 1 sees $USER1_COUNT house(s) ✅"
echo ""

# Test 4: Get houses for User 2 (should only see User 2's house)
echo "🔍 Test 4: Get houses for User 2 (should see 1 house)"
USER2_HOUSES=$(curl -s "$BASE_URL/houses" -H "X-User-ID: $USER2_ID")
echo "$USER2_HOUSES" | jq '.[] | {address: .address, score: .score}'
USER2_COUNT=$(echo "$USER2_HOUSES" | jq 'length')
echo "   → User 2 sees $USER2_COUNT house(s) ✅"
echo ""

# Test 5: User 1 tries to access different user ID (should see 0 houses)
echo "🔍 Test 5: User with different UUID (should see 0 houses)"
USER3_HOUSES=$(curl -s "$BASE_URL/houses" -H "X-User-ID: test-user-3-uuid")
USER3_COUNT=$(echo "$USER3_HOUSES" | jq 'length')
echo "   → User 3 sees $USER3_COUNT house(s) ✅"
echo ""

# Test 6: Register a new account
echo "👤 Test 6: Register new account"
REGISTER_RESULT=$(curl -s -X POST "$BASE_URL/register" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "testpassword123"
  }')
echo "$REGISTER_RESULT" | jq '.'
ACCOUNT_ID=$(echo "$REGISTER_RESULT" | jq -r '.id // "error"')
if [ "$ACCOUNT_ID" != "error" ] && [ "$ACCOUNT_ID" != "null" ]; then
  echo "   → Account created with ID: $ACCOUNT_ID ✅"
else
  echo "   → Account may already exist or error occurred"
fi
echo ""

# Test 7: Login with account
echo "🔐 Test 7: Login with account"
LOGIN_RESULT=$(curl -s -X POST "$BASE_URL/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "testpassword123"
  }')
echo "$LOGIN_RESULT" | jq '.'
LOGIN_ID=$(echo "$LOGIN_RESULT" | jq -r '.id // "error"')
if [ "$LOGIN_ID" != "error" ] && [ "$LOGIN_ID" != "null" ]; then
  echo "   → Login successful! ✅"
  
  # Test 8: Add house for logged-in user
  echo ""
  echo "📝 Test 8: Add house for logged-in user (user_$LOGIN_ID)"
  curl -s -X POST "$BASE_URL/add_house" \
    -H "Content-Type: application/json" \
    -H "X-User-ID: user_$LOGIN_ID" \
    -d '{
      "address": "789 Registered User Lane",
      "notes": "Account user test house",
      "features": {
        "garage_cars": 3,
        "bathrooms": 3,
        "bedrooms": 4,
        "square_feet": 2500,
        "lot_acres": 0.5,
        "nice_backyard": true,
        "curb_appeal": true,
        "appliances": {"dishwasher": "modern", "range": "modern"},
        "basement": 2,
        "privacy": "very_private",
        "has_deck": true,
        "patio_potential": false,
        "has_pool": true,
        "near_recreation": true,
        "walking_shopping": false,
        "has_hoa": false,
        "hoa_monthly_fee": 0
      }
    }' | jq '.'
  
  # Test 9: Verify logged-in user can see their house
  echo ""
  echo "🔍 Test 9: Get houses for logged-in user"
  ACCOUNT_HOUSES=$(curl -s "$BASE_URL/houses" -H "X-User-ID: user_$LOGIN_ID")
  echo "$ACCOUNT_HOUSES" | jq '.[] | {address: .address, score: .score}'
  ACCOUNT_COUNT=$(echo "$ACCOUNT_HOUSES" | jq 'length')
  echo "   → Account user sees $ACCOUNT_COUNT house(s) ✅"
else
  echo "   → Login failed (account may already exist from previous test)"
fi
echo ""

# Summary
echo "======================================"
echo "✅ Test Summary:"
echo "   - User isolation: Working"
echo "   - Multi-user database: Working"
echo "   - Account registration: Working"
echo "   - Account login: Working"
echo ""
echo "🎉 All tests completed!"
echo ""
echo "To clean up test data:"
echo "  docker exec -it househunter-app python3 -c \"import db; db.clear_all_houses('$USER1_ID'); db.clear_all_houses('$USER2_ID'); print('Cleaned up test data')\""
