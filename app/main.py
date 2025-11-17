from fastapi import FastAPI, HTTPException, Header, Request
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from typing import List, Optional
import json
import os
import requests
from pathlib import Path
from pydantic import BaseModel, EmailStr

from models import House, HouseResponse, HouseFeatures, calculate_score
import db
import property_cache

app = FastAPI(title="HouseHunter", description="House Rating & Decision Tool")

# Initialize database on startup
@app.on_event("startup")
async def startup_event():
    """Initialize database on application startup"""
    db.init_db()
    property_cache.init_cache_db()
    print("Database initialized successfully")


# Helper function to get user_id from header or generate anonymous ID
def get_user_id(x_user_id: Optional[str] = Header(None)) -> str:
    """Extract user ID from header, default to 'anonymous' if not provided"""
    return x_user_id if x_user_id else "anonymous"


# User authentication models
class UserRegister(BaseModel):
    first_name: str
    last_name: str
    email: EmailStr
    phone: str
    password: str


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: int
    first_name: str
    last_name: str
    email: str
    phone: str

# Mount static files
static_path = Path(__file__).parent / "static"
static_path.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_path)), name="static")


@app.get("/", response_class=HTMLResponse)
async def read_root():
    """Serve the main HTML page"""
    html_path = Path(__file__).parent / "templates" / "index.html"
    if html_path.exists():
        return HTMLResponse(content=html_path.read_text(), status_code=200)
    return HTMLResponse(content="<h1>HouseHunter - Template not found</h1>", status_code=404)


@app.get("/privacy", response_class=HTMLResponse)
async def privacy_policy():
    """Serve the Privacy Policy page"""
    html_path = Path(__file__).parent / "templates" / "privacy.html"
    if html_path.exists():
        return HTMLResponse(content=html_path.read_text(), status_code=200)
    return HTMLResponse(content="<h1>Privacy Policy - Page not found</h1>", status_code=404)


@app.get("/terms", response_class=HTMLResponse)
async def terms_of_use():
    """Serve the Terms of Use page"""
    html_path = Path(__file__).parent / "templates" / "terms.html"
    if html_path.exists():
        return HTMLResponse(content=html_path.read_text(), status_code=200)
    return HTMLResponse(content="<h1>Terms of Use - Page not found</h1>", status_code=404)


@app.post("/register", response_model=UserResponse)
async def register(user: UserRegister):
    """Register a new user account"""
    result = db.create_user(user.first_name, user.last_name, user.email, user.phone, user.password)
    if not result:
        raise HTTPException(status_code=400, detail="Email already registered")
    return UserResponse(**result)


@app.post("/login", response_model=UserResponse)
async def login(user: UserLogin):
    """Login with email and password"""
    result = db.verify_user(user.email, user.password)
    if not result:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return UserResponse(**result)


@app.post("/add_house", response_model=HouseResponse)
async def add_house(house: House, user_id: str = Header(None, alias="X-User-ID")):
    """Add a new house with features and calculate its score"""
    # Use provided user_id or default to 'anonymous'
    user_id = user_id if user_id else "anonymous"
    
    # Debug logging
    photo_preview = house.photo[:50] + "..." if house.photo else "None"
    print(f"ADD HOUSE - Photo received: {photo_preview}")
    
    # Calculate score
    score, breakdown = calculate_score(house.features)
    
    # Store house in database
    house_data = db.add_house(
        user_id=user_id,
        address=house.address,
        features=house.features.dict(),
        notes=house.notes,
        photo=house.photo,
        score=score,
        score_breakdown=breakdown,
        price=house.price
    )
    
    print(f"ADD HOUSE - Photo in response: {house_data.get('photo', 'MISSING')[:50] if house_data.get('photo') else 'None'}")
    
    return HouseResponse(**house_data)


@app.get("/houses", response_model=List[HouseResponse])
async def get_houses(user_id: str = Header(None, alias="X-User-ID")):
    """Get all houses for the current user sorted by score (highest first)"""
    # Use provided user_id or default to 'anonymous'
    user_id = user_id if user_id else "anonymous"
    
    houses_list = db.get_all_houses(user_id=user_id, order_by_score=True)
    
    # Debug: Check if photos are in the response
    for house in houses_list:
        photo_info = house.get('photo', 'MISSING')
        if photo_info and photo_info != 'MISSING':
            print(f"GET HOUSES - House {house.get('id')}: Has photo (length: {len(photo_info)})")
        else:
            print(f"GET HOUSES - House {house.get('id')}: NO PHOTO")
    
    return [HouseResponse(**house) for house in houses_list]


@app.get("/house/{house_id}", response_model=HouseResponse)
async def get_house(house_id: int, user_id: str = Header(None, alias="X-User-ID")):
    """Get a specific house by ID (must belong to user)"""
    # Use provided user_id or default to 'anonymous'
    user_id = user_id if user_id else "anonymous"
    
    house = db.get_house_by_id(user_id=user_id, house_id=house_id)
    if not house:
        raise HTTPException(status_code=404, detail="House not found")
    return HouseResponse(**house)


@app.delete("/house/{house_id}")
async def delete_house(house_id: int, user_id: str = Header(None, alias="X-User-ID")):
    """Delete a house by ID (must belong to user)"""
    # Use provided user_id or default to 'anonymous'
    user_id = user_id if user_id else "anonymous"
    
    house = db.get_house_by_id(user_id=user_id, house_id=house_id)
    if not house:
        raise HTTPException(status_code=404, detail="House not found")
    
    db.delete_house(user_id=user_id, house_id=house_id)
    return {"message": "House deleted successfully", "address": house["address"]}


@app.put("/house/{house_id}", response_model=HouseResponse)
async def update_house(house_id: int, house: House, user_id: str = Header(None, alias="X-User-ID")):
    """Update an existing house by ID (must belong to user)"""
    # Use provided user_id or default to 'anonymous'
    user_id = user_id if user_id else "anonymous"
    
    # Debug logging
    photo_preview = house.photo[:50] + "..." if house.photo else "None"
    print(f"UPDATE HOUSE {house_id} - Photo received: {photo_preview}")
    
    # Calculate new score
    score, breakdown = calculate_score(house.features)
    
    # Update house in database
    house_data = db.update_house(
        user_id=user_id,
        house_id=house_id,
        address=house.address,
        features=house.features.dict(),
        notes=house.notes,
        photo=house.photo,
        score=score,
        score_breakdown=breakdown,
        price=house.price
    )
    
    print(f"UPDATE HOUSE {house_id} - Photo in response: {house_data.get('photo', 'MISSING')[:50] if house_data and house_data.get('photo') else 'None'}")
    
    if not house_data:
        raise HTTPException(status_code=404, detail="House not found")
    
    return HouseResponse(**house_data)


@app.get("/score/{house_id}")
async def get_score(house_id: int, user_id: str = Header(None, alias="X-User-ID")):
    """Get detailed scoring breakdown for a house (must belong to user)"""
    # Use provided user_id or default to 'anonymous'
    user_id = user_id if user_id else "anonymous"
    
    house = db.get_house_by_id(user_id=user_id, house_id=house_id)
    if not house:
        raise HTTPException(status_code=404, detail="House not found")
    
    return {
        "id": house_id,
        "address": house["address"],
        "score": house["score"],
        "breakdown": house["score_breakdown"]
    }


@app.post("/seed_data")
async def seed_data(user_id: str = Header(None, alias="X-User-ID")):
    """Add example houses for testing"""
    # Use provided user_id or default to 'anonymous'
    user_id = user_id if user_id else "anonymous"
    
    examples = [
        {
            "address": "123 Oak Street, Springfield",
            "features": {
                "garage_cars": 2,
                "bathrooms": 3,
                "bedrooms": 4,
                "square_feet": 2000,
                "lot_acres": 0.5,
                "nice_backyard": True,
                "curb_appeal": True,
                "appliances": {
                    "dishwasher": "modern",
                    "range": "modern",
                    "oven": "modern",
                    "fridge": "modern",
                    "washer": "modern",
                    "dryer": "modern"
                },
                "basement": 2,
                "privacy": "very_private",
                "has_deck": True,
                "patio_potential": False,
                "has_pool": True,
                "near_recreation": True,
                "walking_shopping": False,
                "has_hoa": False,
                "hoa_monthly_fee": 0
            },
            "notes": "Beautiful family home with everything we want!"
        },
        {
            "address": "456 Maple Avenue, Riverside",
            "features": {
                "garage_cars": 1,
                "bathrooms": 2,
                "bedrooms": 3,
                "square_feet": 1200,
                "lot_acres": 0.25,
                "nice_backyard": False,
                "curb_appeal": True,
                "appliances": {
                    "dishwasher": "old",
                    "range": "old",
                    "fridge": "old"
                },
                "basement": 1,
                "privacy": "normal",
                "has_deck": False,
                "patio_potential": True,
                "has_pool": False,
                "near_recreation": False,
                "walking_shopping": True,
                "has_hoa": True,
                "hoa_monthly_fee": 30
            },
            "notes": "Decent starter home, needs some upgrades. Low HOA fee."
        },
        {
            "address": "789 Pine Road, Lakeside",
            "features": {
                "garage_cars": 0,
                "bathrooms": 2,
                "bedrooms": 2,
                "square_feet": 900,
                "lot_acres": 0.1,
                "nice_backyard": True,
                "curb_appeal": False,
                "appliances": {
                    "microwave": "modern",
                    "fridge": "modern"
                },
                "basement": 0,
                "privacy": "not_private",
                "has_deck": False,
                "patio_potential": False,
                "has_pool": False,
                "near_recreation": True,
                "walking_shopping": False,
                "has_hoa": True,
                "hoa_monthly_fee": 400
            },
            "notes": "Cozy but no garage and HIGH HOA fees - street parking only"
        }
    ]
    
    added = []
    for example in examples:
        house = House(**example)
        score, breakdown = calculate_score(house.features)
        
        house_data = db.add_house(
            user_id=user_id,
            address=house.address,
            features=house.features.dict(),
            notes=house.notes,
            score=score,
            score_breakdown=breakdown
        )
        
        added.append(HouseResponse(**house_data))
    
    return {"message": f"Added {len(added)} example houses", "houses": added}


@app.delete("/clear_all")
async def clear_all(user_id: str = Header(None, alias="X-User-ID")):
    """Clear all houses for current user"""
    # Use provided user_id or default to 'anonymous'
    user_id = user_id if user_id else "anonymous"
    
    count = db.clear_all_houses(user_id=user_id)
    return {"message": f"Cleared {count} houses"}


@app.post("/sync_houses")
async def sync_houses(houses: List[dict], user_id: str = Header(None, alias="X-User-ID")):
    """
    Sync houses from browser local storage to server database for current user.
    This restores the session when the user returns or if database is empty.
    """
    # Use provided user_id or default to 'anonymous'
    user_id = user_id if user_id else "anonymous"
    
    count = db.sync_houses_from_browser(user_id=user_id, houses=houses)
    
    return {
        "message": f"Synced {count} houses from browser storage to database",
        "count": count
    }


def get_zip_codes_for_city(city: str, state: str) -> List[str]:
    """
    Look up ZIP codes for a given city and state.
    Uses the free ZipCodeAPI service.
    
    Args:
        city: City name (e.g., "Boulder")
        state: State code (e.g., "CO")
        
    Returns:
        List of ZIP codes for the city
    """
    try:
        # Use ZipCodeAPI (free service)
        url = f"https://api.zippopotam.us/us/{state.upper()}/{city.replace(' ', '%20')}"
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            zip_codes = [place['post code'] for place in data.get('places', [])]
            return zip_codes
        else:
            # Fallback: return empty list
            return []
    except Exception as e:
        print(f"Error fetching ZIP codes for {city}, {state}: {str(e)}")
        return []


@app.get("/search_properties")
async def search_properties(zip_code: str, max_price: int, user_id: str = Header(None, alias="X-User-ID")):
    """
    Search for properties in a ZIP code at or below a maximum price.
    Only available to registered users.
    """
    # Verify user is registered (not anonymous)
    user_id = user_id if user_id else "anonymous"
    if user_id == "anonymous" or not user_id.startswith("user_"):
        raise HTTPException(
            status_code=403,
            detail="This feature is only available to registered users. Please login or create an account."
        )
    
    # Get API key from environment variable
    api_key = os.getenv("RAPIDAPI_KEY")
    
    if not api_key:
        raise HTTPException(
            status_code=500,
            detail="RapidAPI key not configured. Please set RAPIDAPI_KEY environment variable."
        )
    
    try:
        # Validate ZIP code format
        import re
        if not re.match(r'^\d{5}$', zip_code):
            raise HTTPException(
                status_code=400,
                detail="Invalid ZIP code format. Please use 5-digit ZIP code (e.g., 80303)"
            )
        
        # Check cache first
        cached_properties = property_cache.search_cached_properties(zip_code, max_price)
        if cached_properties:
            print(f"Cache hit for ZIP {zip_code} with max price ${max_price}")
            return {
                "success": True,
                "zip_code": zip_code,
                "max_price": max_price,
                "count": len(cached_properties),
                "properties": cached_properties,
                "source": "cache"
            }
        
        print(f"Cache miss for ZIP {zip_code}, fetching from API")
        
        # Search properties by ZIP code from API
        search_url = "https://realty-in-us.p.rapidapi.com/properties/v3/list"
        headers = {
            "Content-Type": "application/json",
            "X-RapidAPI-Key": api_key,
            "X-RapidAPI-Host": "realty-in-us.p.rapidapi.com"
        }
        
        # Search payload
        payload = {
            "limit": 200,
            "offset": 0,
            "postal_code": zip_code,
            "status": ["for_sale", "ready_to_build"]
        }
        
        search_response = requests.post(search_url, headers=headers, json=payload, timeout=15)
        
        if search_response.status_code == 403:
            raise HTTPException(
                status_code=403,
                detail="RapidAPI authentication failed. Please verify you're subscribed to 'Realty in US' API"
            )
        
        search_response.raise_for_status()
        search_data = search_response.json()
        
        # Extract properties from response
        properties = []
        if search_data.get("data") and search_data["data"].get("home_search"):
            properties = search_data["data"]["home_search"].get("results", [])
        elif search_data.get("data") and search_data["data"].get("results"):
            properties = search_data["data"]["results"]
        
        if not properties:
            raise HTTPException(
                status_code=404,
                detail=f"No properties found in ZIP code {zip_code}"
            )
        
        # Cache all properties from this search
        property_cache.cache_properties(properties, zip_code)
        
        # Filter by price and format results
        filtered_properties = []
        for prop in properties:
            # Extract price
            price = None
            if prop.get("list_price"):
                price = prop["list_price"]
            elif prop.get("price"):
                price = prop["price"]
            
            # Skip if no price or price is above max
            if not price or price > max_price:
                continue
            
            # Extract property details
            description = prop.get("description", {})
            location = prop.get("location", {}).get("address", {})
            
            # Extract address
            prop_address = ""
            if location.get("line"):
                prop_address = location.get("line", "")
            elif prop.get("address"):
                if isinstance(prop["address"], dict):
                    prop_address = prop["address"].get("line", "")
                else:
                    prop_address = str(prop["address"])
            
            # Build full address
            full_address = f"{location.get('line', '')}, {location.get('city', '')}, {location.get('state_code', '')} {location.get('postal_code', '')}"
            full_address = full_address.strip().strip(',')
            
            # Extract other details
            bedrooms = description.get("beds") or prop.get("beds") or 0
            bathrooms_full = description.get("baths_full") or prop.get("baths_full") or 0
            bathrooms_half = description.get("baths_half") or prop.get("baths_half") or 0
            bathrooms = bathrooms_full + (bathrooms_half * 0.5)
            bathrooms = int(bathrooms) if bathrooms == int(bathrooms) else bathrooms
            
            sqft = description.get("sqft") or prop.get("sqft") or 0
            lot_sqft = description.get("lot_sqft") or prop.get("lot_sqft") or 0
            lot_acres = round(lot_sqft / 43560, 2) if lot_sqft else 0
            
            garage = description.get("garage") or prop.get("garage") or 0
            
            # Extract photo URL
            photo_url = None
            if prop.get("primary_photo"):
                if isinstance(prop["primary_photo"], dict):
                    photo_url = prop["primary_photo"].get("href")
                elif isinstance(prop["primary_photo"], str):
                    photo_url = prop["primary_photo"]
            elif prop.get("photos") and len(prop["photos"]) > 0:
                first_photo = prop["photos"][0]
                if isinstance(first_photo, dict):
                    photo_url = first_photo.get("href")
                elif isinstance(first_photo, str):
                    photo_url = first_photo
            elif prop.get("thumbnail"):
                photo_url = prop.get("thumbnail")
            
            filtered_properties.append({
                "address": full_address or "Address not available",
                "price": price,
                "bedrooms": bedrooms,
                "bathrooms": bathrooms,
                "square_feet": sqft,
                "lot_acres": lot_acres,
                "garage_cars": garage,
                "photo_url": photo_url,
                "property_type": description.get("type") or prop.get("prop_type") or "Unknown",
                "year_built": description.get("year_built") or prop.get("year_built")
            })
        
        # Sort by price (lowest first)
        filtered_properties.sort(key=lambda x: x["price"])
        
        return {
            "success": True,
            "zip_code": zip_code,
            "max_price": max_price,
            "count": len(filtered_properties),
            "properties": filtered_properties,
            "total_searched": len(properties),
            "source": "api"
        }
        
    except HTTPException:
        raise
    except requests.exceptions.Timeout:
        raise HTTPException(status_code=504, detail="Request to Realtor API timed out")
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=502, detail=f"Error connecting to Realtor API: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing property data: {str(e)}")


@app.get("/search_by_city")
async def search_by_city(city: str, state: str, max_price: int, user_id: str = Header(None, alias="X-User-ID")):
    """
    Search for properties in a city at or below a maximum price.
    Looks up all ZIP codes for the city and searches each one.
    Only available to registered users.
    """
    # Verify user is registered (not anonymous)
    user_id = user_id if user_id else "anonymous"
    if user_id == "anonymous" or not user_id.startswith("user_"):
        raise HTTPException(
            status_code=403,
            detail="This feature is only available to registered users. Please login or create an account."
        )
    
    # Get API key from environment variable
    api_key = os.getenv("RAPIDAPI_KEY")
    
    if not api_key:
        raise HTTPException(
            status_code=500,
            detail="RapidAPI key not configured. Please set RAPIDAPI_KEY environment variable."
        )
    
    try:
        # Validate state code (2 letters)
        import re
        if not re.match(r'^[A-Z]{2}$', state.upper()):
            raise HTTPException(
                status_code=400,
                detail="Invalid state code. Please use 2-letter state code (e.g., CO, CA, NY)"
            )
        
        # Look up ZIP codes for the city
        zip_codes = get_zip_codes_for_city(city, state)
        
        if not zip_codes:
            raise HTTPException(
                status_code=404,
                detail=f"No ZIP codes found for {city}, {state}. Please check the city and state spelling."
            )
        
        print(f"Found {len(zip_codes)} ZIP codes for {city}, {state}: {zip_codes}")
        
        # Search properties in each ZIP code
        all_properties = []
        searched_zips = []
        cache_hits = 0
        api_calls = 0
        
        for zip_code in zip_codes:
            try:
                # Check cache first
                cached_properties = property_cache.search_cached_properties(zip_code, max_price)
                if cached_properties:
                    print(f"Cache hit for ZIP {zip_code}")
                    all_properties.extend(cached_properties)
                    searched_zips.append(zip_code)
                    cache_hits += 1
                    continue
                
                # Not in cache, fetch from API
                print(f"Cache miss for ZIP {zip_code}, fetching from API")
                api_calls += 1
                
                search_url = "https://realty-in-us.p.rapidapi.com/properties/v3/list"
                headers = {
                    "Content-Type": "application/json",
                    "X-RapidAPI-Key": api_key,
                    "X-RapidAPI-Host": "realty-in-us.p.rapidapi.com"
                }
                
                payload = {
                    "limit": 200,
                    "offset": 0,
                    "postal_code": zip_code,
                    "status": ["for_sale", "ready_to_build"]
                }
                
                search_response = requests.post(search_url, headers=headers, json=payload, timeout=15)
                
                if search_response.status_code == 403:
                    print(f"API authentication failed for ZIP {zip_code}")
                    continue
                
                if not search_response.ok:
                    print(f"API error for ZIP {zip_code}: {search_response.status_code}")
                    continue
                
                search_data = search_response.json()
                
                # Extract properties
                properties = []
                if search_data.get("data") and search_data["data"].get("home_search"):
                    properties = search_data["data"]["home_search"].get("results", [])
                elif search_data.get("data") and search_data["data"].get("results"):
                    properties = search_data["data"]["results"]
                
                if not properties:
                    print(f"No properties found in ZIP {zip_code}")
                    continue
                
                # Cache all properties
                property_cache.cache_properties(properties, zip_code)
                
                # Filter and format properties
                for prop in properties:
                    price = prop.get("list_price") or prop.get("price")
                    
                    if not price or price > max_price:
                        continue
                    
                    description = prop.get("description", {})
                    location = prop.get("location", {}).get("address", {})
                    
                    full_address = f"{location.get('line', '')}, {location.get('city', '')}, {location.get('state_code', '')} {location.get('postal_code', '')}"
                    full_address = full_address.strip().strip(',')
                    
                    bedrooms = description.get("beds") or prop.get("beds") or 0
                    bathrooms_full = description.get("baths_full") or prop.get("baths_full") or 0
                    bathrooms_half = description.get("baths_half") or prop.get("baths_half") or 0
                    bathrooms = bathrooms_full + (bathrooms_half * 0.5)
                    bathrooms = int(bathrooms) if bathrooms == int(bathrooms) else bathrooms
                    
                    sqft = description.get("sqft") or prop.get("sqft") or 0
                    lot_sqft = description.get("lot_sqft") or prop.get("lot_sqft") or 0
                    lot_acres = round(lot_sqft / 43560, 2) if lot_sqft else 0
                    garage = description.get("garage") or prop.get("garage") or 0
                    
                    photo_url = None
                    if prop.get("primary_photo"):
                        if isinstance(prop["primary_photo"], dict):
                            photo_url = prop["primary_photo"].get("href")
                        elif isinstance(prop["primary_photo"], str):
                            photo_url = prop["primary_photo"]
                    elif prop.get("photos") and len(prop["photos"]) > 0:
                        first_photo = prop["photos"][0]
                        if isinstance(first_photo, dict):
                            photo_url = first_photo.get("href")
                        elif isinstance(first_photo, str):
                            photo_url = first_photo
                    elif prop.get("thumbnail"):
                        photo_url = prop.get("thumbnail")
                    
                    all_properties.append({
                        "address": full_address or "Address not available",
                        "price": price,
                        "bedrooms": bedrooms,
                        "bathrooms": bathrooms,
                        "square_feet": sqft,
                        "lot_acres": lot_acres,
                        "garage_cars": garage,
                        "photo_url": photo_url,
                        "property_type": description.get("type") or prop.get("prop_type") or "Unknown",
                        "year_built": description.get("year_built") or prop.get("year_built"),
                        "zip_code": zip_code
                    })
                
                searched_zips.append(zip_code)
                
            except Exception as e:
                print(f"Error searching ZIP {zip_code}: {str(e)}")
                continue
        
        if not all_properties:
            raise HTTPException(
                status_code=404,
                detail=f"No properties found in {city}, {state} for ${max_price:,} or less. Searched {len(searched_zips)} ZIP codes."
            )
        
        # Remove duplicates by address
        seen_addresses = set()
        unique_properties = []
        for prop in all_properties:
            if prop["address"] not in seen_addresses:
                seen_addresses.add(prop["address"])
                unique_properties.append(prop)
        
        # Sort by price (lowest first)
        unique_properties.sort(key=lambda x: x["price"])
        
        return {
            "success": True,
            "city": city.title(),
            "state": state.upper(),
            "max_price": max_price,
            "zip_codes_searched": searched_zips,
            "zip_codes_found": len(zip_codes),
            "count": len(unique_properties),
            "properties": unique_properties,
            "cache_hits": cache_hits,
            "api_calls": api_calls,
            "source": "city_search"
        }
        
    except HTTPException:
        raise
    except requests.exceptions.Timeout:
        raise HTTPException(status_code=504, detail="Request to location API timed out")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error searching by city: {str(e)}")


@app.get("/lookup_address")
async def lookup_address(address: str):
    """
    Lookup property details from Realtor API via RapidAPI.
    Returns bedrooms, bathrooms, sqft, lot size, garage, etc.
    """
    # Get API key from environment variable
    api_key = os.getenv("RAPIDAPI_KEY")
    
    if not api_key:
        raise HTTPException(
            status_code=500, 
            detail="RapidAPI key not configured. Please set RAPIDAPI_KEY environment variable."
        )
    
    try:
        # Extract ZIP code from address (last 5 digits or ZIP+4 format)
        import re
        zip_match = re.search(r'\b(\d{5})(?:-\d{4})?\b', address)
        
        if not zip_match:
            raise HTTPException(
                status_code=400,
                detail="Could not extract ZIP code from address. Please include ZIP code in format: '123 Main St, City, State 12345'"
            )
        
        zip_code = zip_match.group(1)
        
        # Check cache first
        cached_property = property_cache.lookup_cached_property(address, zip_code)
        if cached_property:
            print(f"Cache hit for address: {address}")
            return {
                "success": True,
                "data": cached_property,
                "matched_from_zip": zip_code,
                "source": "cache"
            }
        
        print(f"Cache miss for address: {address}, fetching from API")
        
        # Extract street address - handle various comma placements
        # Case 1: "123 Main St, City, State ZIP" - standard format
        # Case 2: "123 Main St City, State ZIP" - comma only before state
        # Case 3: "123 Main St City State ZIP" - no commas
        
        # Strategy: Remove ZIP, then check if we have state code at end
        addr_without_zip = re.sub(r'\s*\d{5}(?:-\d{4})?\s*$', '', address).strip()
        
        # Look for state code pattern (2 uppercase letters at or near end)
        # This handles ", CO" or " CO" at the end
        state_match = re.search(r'[,\s]+(AL|AK|AZ|AR|CA|CO|CT|DE|FL|GA|HI|ID|IL|IN|IA|KS|KY|LA|ME|MD|MA|MI|MN|MS|MO|MT|NE|NV|NH|NJ|NM|NY|NC|ND|OH|OK|OR|PA|RI|SC|SD|TN|TX|UT|VT|VA|WA|WV|WI|WY)\s*$', addr_without_zip, re.IGNORECASE)
        
        if state_match:
            # Found state at end - take everything before it
            addr_without_state = addr_without_zip[:state_match.start()].strip()
            # Now check if there's a comma before the city name
            # If so, street is before first comma
            if ',' in addr_without_state:
                street_address_raw = addr_without_state.split(',')[0].strip()
            else:
                # No comma before city - assume last word is city name
                words = addr_without_state.split()
                if len(words) > 3:
                    street_address_raw = ' '.join(words[:-1])  # Drop last word (city)
                else:
                    street_address_raw = addr_without_state
        else:
            # No state code found - fall back to comma splitting or word counting
            if ',' in addr_without_zip:
                street_address_raw = addr_without_zip.split(',')[0].strip()
            else:
                words = addr_without_zip.split()
                if len(words) > 3:
                    street_address_raw = ' '.join(words[:-1])
                else:
                    street_address_raw = addr_without_zip
        
        # Normalize: remove unit/apt numbers, special chars for better matching
        street_address = re.sub(r'\s*[#,]?\s*(unit|apt|apartment|suite|ste|d)\s*[\d\w-]+', '', street_address_raw, flags=re.IGNORECASE).strip().lower()
        # Also keep just the street number and name
        street_number = re.match(r'^(\d+)', street_address)
        street_number = street_number.group(1) if street_number else ""
        
        # Step 1: Search properties by ZIP code
        search_url = "https://realty-in-us.p.rapidapi.com/properties/v3/list"
        headers = {
            "Content-Type": "application/json",
            "X-RapidAPI-Key": api_key,
            "X-RapidAPI-Host": "realty-in-us.p.rapidapi.com"
        }
        
        # Search payload - get more results to increase match chance
        payload = {
            "limit": 200,
            "offset": 0,
            "postal_code": zip_code,
            "status": ["for_sale", "ready_to_build", "sold", "for_rent", "pending", "off_market"]
        }
        
        search_response = requests.post(search_url, headers=headers, json=payload, timeout=15)
        
        if search_response.status_code == 403:
            raise HTTPException(
                status_code=403,
                detail="RapidAPI authentication failed. Please verify you're subscribed to 'Realty in US' API at https://rapidapi.com/apimaker/api/realty-in-us"
            )
        
        search_response.raise_for_status()
        search_data = search_response.json()
        
        # Extract properties from response
        properties = []
        if search_data.get("data") and search_data["data"].get("home_search"):
            properties = search_data["data"]["home_search"].get("results", [])
        elif search_data.get("data") and search_data["data"].get("results"):
            properties = search_data["data"]["results"]
        
        if not properties:
            raise HTTPException(
                status_code=404,
                detail=f"No properties found in ZIP code {zip_code}. The property might not be listed or use a different ZIP code."
            )
        
        # Cache all properties from this ZIP code search
        property_cache.cache_properties(properties, zip_code)
        
        # Step 2: Find matching property by address
        matched_property = None
        for prop in properties:
            prop_address = ""
            prop_address_raw = ""
            
            # Try different address formats
            if prop.get("location") and prop["location"].get("address"):
                addr = prop["location"]["address"]
                prop_address_raw = addr.get("line", "") or ""
            elif prop.get("address"):
                if isinstance(prop["address"], dict):
                    prop_address_raw = prop["address"].get("line", "") or ""
                else:
                    prop_address_raw = str(prop["address"]) if prop["address"] else ""
            
            # Skip if no address found
            if not prop_address_raw:
                continue
                
            prop_address_raw = prop_address_raw.lower()
            
            # Normalize property address too
            prop_address = re.sub(r'\s*[#,]?\s*(unit|apt|apartment|suite|ste)\s*[\d\w-]+', '', prop_address_raw, flags=re.IGNORECASE).strip()
            
            # Extract street number from property
            prop_street_number = re.match(r'^(\d+)', prop_address)
            prop_street_number = prop_street_number.group(1) if prop_street_number else ""
            
            # Match by street number and partial street name
            if street_number and prop_street_number == street_number:
                # Numbers match, check if street names are similar
                if street_address in prop_address or prop_address in street_address:
                    matched_property = prop
                    break
            # Fallback: fuzzy match entire address
            elif street_address in prop_address_raw or prop_address_raw in street_address:
                matched_property = prop
                break
        
        if not matched_property:
            # Return helpful error with found addresses
            found_addresses = []
            for prop in properties[:5]:  # Show first 5
                if prop.get("location") and prop["location"].get("address"):
                    found_addresses.append(prop["location"]["address"].get("line", ""))
            
            raise HTTPException(
                status_code=404,
                detail=f"Address '{street_address}' not found in ZIP {zip_code}. Found addresses: {', '.join(found_addresses[:3])}. Try entering full address with exact street name."
            )
        
        # Step 3: Extract property details
        description = matched_property.get("description", {})
        location = matched_property.get("location", {}).get("address", {})
        
        bedrooms = (
            description.get("beds") or 
            matched_property.get("beds") or 
            description.get("beds_min") or
            0
        )
        
        bathrooms_full = (
            description.get("baths_full") or 
            matched_property.get("baths_full") or 
            description.get("baths") or
            0
        )
        
        bathrooms_half = (
            description.get("baths_half") or 
            matched_property.get("baths_half") or 
            0
        )
        
        bathrooms = bathrooms_full + (bathrooms_half * 0.5)
        bathrooms = int(bathrooms) if bathrooms == int(bathrooms) else bathrooms
        
        sqft = (
            description.get("sqft") or 
            matched_property.get("sqft") or
            description.get("lot_sqft") or
            0
        )
        
        lot_sqft = (
            description.get("lot_sqft") or 
            matched_property.get("lot_sqft") or 
            0
        )
        
        lot_acres = round(lot_sqft / 43560, 2) if lot_sqft else 0
        
        garage = (
            description.get("garage") or 
            matched_property.get("garage") or
            description.get("garage_spaces") or 
            matched_property.get("garage_spaces") or
            0
        )
        
        year_built = (
            description.get("year_built") or 
            matched_property.get("year_built") or 
            None
        )
        
        property_type = (
            description.get("type") or 
            matched_property.get("prop_type") or 
            matched_property.get("type") or
            "Unknown"
        )
        
        # Extract price
        price = None
        if matched_property.get("list_price"):
            price = matched_property["list_price"]
        elif matched_property.get("price"):
            price = matched_property["price"]
        elif description.get("sold_price"):
            price = description["sold_price"]
        
        # Extract primary photo URL
        photo_url = None
        if matched_property.get("primary_photo"):
            if isinstance(matched_property["primary_photo"], dict):
                photo_url = matched_property["primary_photo"].get("href")
            elif isinstance(matched_property["primary_photo"], str):
                photo_url = matched_property["primary_photo"]
        elif matched_property.get("photos") and len(matched_property["photos"]) > 0:
            first_photo = matched_property["photos"][0]
            if isinstance(first_photo, dict):
                photo_url = first_photo.get("href")
            elif isinstance(first_photo, str):
                photo_url = first_photo
        elif matched_property.get("thumbnail"):
            photo_url = matched_property.get("thumbnail")
        
        # Build full validated address
        full_address = f"{location.get('line', '')}, {location.get('city', '')}, {location.get('state_code', '')} {location.get('postal_code', '')}"
        full_address = full_address.strip().strip(',')
        
        return {
            "success": True,
            "data": {
                "address": full_address or address,
                "bedrooms": bedrooms,
                "bathrooms": bathrooms,
                "square_feet": sqft,
                "lot_acres": lot_acres,
                "garage_cars": garage,
                "year_built": year_built,
                "property_type": property_type,
                "price": price,
                "photo_url": photo_url
            },
            "matched_from_zip": zip_code,
            "properties_searched": len(properties),
            "source": "api"
        }
        
    except HTTPException:
        raise
    except requests.exceptions.Timeout:
        raise HTTPException(status_code=504, detail="Request to Realtor API timed out")
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=502, detail=f"Error connecting to Realtor API: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing property data: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
