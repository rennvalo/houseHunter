from fastapi import FastAPI, HTTPException, Header, Request
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from typing import List, Optional
import json
from pathlib import Path
from pydantic import BaseModel, EmailStr

from models import House, HouseResponse, HouseFeatures, calculate_score
import db

app = FastAPI(title="HouseHunter", description="House Rating & Decision Tool")

# Initialize database on startup
@app.on_event("startup")
async def startup_event():
    """Initialize database on application startup"""
    db.init_db()
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
        score_breakdown=breakdown
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
        score_breakdown=breakdown
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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
