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
    email: EmailStr
    password: str


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: int
    email: str

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


@app.post("/register", response_model=UserResponse)
async def register(user: UserRegister):
    """Register a new user account"""
    result = db.create_user(user.email, user.password)
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
