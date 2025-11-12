from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from typing import List
import json
from pathlib import Path

from models import House, HouseResponse, HouseFeatures, calculate_score

app = FastAPI(title="HouseHunter", description="House Rating & Decision Tool")

# Mount static files
static_path = Path(__file__).parent / "static"
static_path.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_path)), name="static")

# In-memory storage (session-based, resets on restart)
houses_db = {}
next_id = 1


@app.get("/", response_class=HTMLResponse)
async def read_root():
    """Serve the main HTML page"""
    html_path = Path(__file__).parent / "templates" / "index.html"
    if html_path.exists():
        return HTMLResponse(content=html_path.read_text(), status_code=200)
    return HTMLResponse(content="<h1>HouseHunter - Template not found</h1>", status_code=404)


@app.post("/add_house", response_model=HouseResponse)
async def add_house(house: House):
    """Add a new house with features and calculate its score"""
    global next_id
    
    # Calculate score
    score, breakdown = calculate_score(house.features)
    
    # Store house
    house_data = {
        "id": next_id,
        "address": house.address,
        "features": house.features.dict(),
        "notes": house.notes,
        "score": score,
        "score_breakdown": breakdown
    }
    
    houses_db[next_id] = house_data
    next_id += 1
    
    return HouseResponse(**house_data)


@app.get("/houses", response_model=List[HouseResponse])
async def get_houses():
    """Get all houses sorted by score (highest first)"""
    houses_list = list(houses_db.values())
    # Sort by score descending
    houses_list.sort(key=lambda x: x["score"], reverse=True)
    return [HouseResponse(**house) for house in houses_list]


@app.get("/house/{house_id}", response_model=HouseResponse)
async def get_house(house_id: int):
    """Get a specific house by ID"""
    if house_id not in houses_db:
        raise HTTPException(status_code=404, detail="House not found")
    return HouseResponse(**houses_db[house_id])


@app.delete("/house/{house_id}")
async def delete_house(house_id: int):
    """Delete a house by ID"""
    if house_id not in houses_db:
        raise HTTPException(status_code=404, detail="House not found")
    
    deleted = houses_db.pop(house_id)
    return {"message": "House deleted successfully", "address": deleted["address"]}


@app.put("/house/{house_id}", response_model=HouseResponse)
async def update_house(house_id: int, house: House):
    """Update an existing house by ID"""
    if house_id not in houses_db:
        raise HTTPException(status_code=404, detail="House not found")
    
    # Calculate new score
    score, breakdown = calculate_score(house.features)
    
    # Update house data
    house_data = {
        "id": house_id,
        "address": house.address,
        "features": house.features.dict(),
        "notes": house.notes,
        "score": score,
        "score_breakdown": breakdown
    }
    
    houses_db[house_id] = house_data
    
    return HouseResponse(**house_data)


@app.get("/score/{house_id}")
async def get_score(house_id: int):
    """Get detailed scoring breakdown for a house"""
    if house_id not in houses_db:
        raise HTTPException(status_code=404, detail="House not found")
    
    house = houses_db[house_id]
    return {
        "id": house_id,
        "address": house["address"],
        "score": house["score"],
        "breakdown": house["score_breakdown"]
    }


@app.post("/seed_data")
async def seed_data():
    """Add example houses for testing"""
    global next_id
    
    examples = [
        {
            "address": "123 Oak Street, Springfield",
            "features": {
                "garage_cars": 2,
                "bathrooms": 3,
                "bedrooms": 4,
                "square_feet": 2000,
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
                "nice_backyard": False,
                "curb_appeal": True,
                "appliances": {
                    "dishwasher": "old",
                    "range": "old",
                    "fridge": "old"
                },
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
                "nice_backyard": True,
                "curb_appeal": False,
                "appliances": {
                    "microwave": "modern",
                    "fridge": "modern"
                },
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
        
        house_data = {
            "id": next_id,
            "address": house.address,
            "features": house.features.dict(),
            "notes": house.notes,
            "score": score,
            "score_breakdown": breakdown
        }
        
        houses_db[next_id] = house_data
        added.append(HouseResponse(**house_data))
        next_id += 1
    
    return {"message": f"Added {len(added)} example houses", "houses": added}


@app.delete("/clear_all")
async def clear_all():
    """Clear all houses (reset session)"""
    global houses_db, next_id
    count = len(houses_db)
    houses_db = {}
    next_id = 1
    return {"message": f"Cleared {count} houses"}


@app.post("/sync_houses")
async def sync_houses(houses: List[dict]):
    """
    Sync houses from browser local storage to server memory.
    This restores the session when the user returns.
    """
    global houses_db, next_id
    
    # Clear current in-memory storage
    houses_db = {}
    
    # Find the highest ID to set next_id correctly
    max_id = 0
    
    for house_data in houses:
        house_id = house_data.get("id")
        if house_id:
            houses_db[house_id] = house_data
            max_id = max(max_id, house_id)
    
    next_id = max_id + 1
    
    return {
        "message": f"Synced {len(houses_db)} houses from browser storage",
        "count": len(houses_db)
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
