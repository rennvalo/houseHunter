from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from typing import List
import json
from pathlib import Path

from models import House, HouseResponse, HouseFeatures, calculate_score
import db

app = FastAPI(title="HouseHunter", description="House Rating & Decision Tool")

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


@app.post("/add_house", response_model=HouseResponse)
async def add_house(house: House):
    """Add a new house with features and calculate its score"""
    # Calculate score
    score, breakdown = calculate_score(house.features)
    
    # Store house in database
    house_data = db.add_house(
        address=house.address,
        features=house.features.dict(),
        notes=house.notes,
        score=score,
        score_breakdown=breakdown
    )
    
    return HouseResponse(**house_data)


@app.get("/houses", response_model=List[HouseResponse])
async def get_houses():
    """Get all houses sorted by score (highest first)"""
    houses_list = db.get_all_houses(order_by_score=True)
    return [HouseResponse(**house) for house in houses_list]


@app.get("/house/{house_id}", response_model=HouseResponse)
async def get_house(house_id: int):
    """Get a specific house by ID"""
    house = db.get_house_by_id(house_id)
    if not house:
        raise HTTPException(status_code=404, detail="House not found")
    return HouseResponse(**house)


@app.delete("/house/{house_id}")
async def delete_house(house_id: int):
    """Delete a house by ID"""
    house = db.get_house_by_id(house_id)
    if not house:
        raise HTTPException(status_code=404, detail="House not found")
    
    db.delete_house(house_id)
    return {"message": "House deleted successfully", "address": house["address"]}


@app.put("/house/{house_id}", response_model=HouseResponse)
async def update_house(house_id: int, house: House):
    """Update an existing house by ID"""
    # Calculate new score
    score, breakdown = calculate_score(house.features)
    
    # Update house in database
    house_data = db.update_house(
        house_id=house_id,
        address=house.address,
        features=house.features.dict(),
        notes=house.notes,
        score=score,
        score_breakdown=breakdown
    )
    
    if not house_data:
        raise HTTPException(status_code=404, detail="House not found")
    
    return HouseResponse(**house_data)


@app.get("/score/{house_id}")
async def get_score(house_id: int):
    """Get detailed scoring breakdown for a house"""
    house = db.get_house_by_id(house_id)
    if not house:
        raise HTTPException(status_code=404, detail="House not found")
    
    return {
        "id": house_id,
        "address": house["address"],
        "score": house["score"],
        "breakdown": house["score_breakdown"]
    }


@app.post("/seed_data")
async def seed_data():
    """Add example houses for testing"""
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
            address=house.address,
            features=house.features.dict(),
            notes=house.notes,
            score=score,
            score_breakdown=breakdown
        )
        
        added.append(HouseResponse(**house_data))
    
    return {"message": f"Added {len(added)} example houses", "houses": added}


@app.delete("/clear_all")
async def clear_all():
    """Clear all houses (reset session)"""
    count = db.clear_all_houses()
    return {"message": f"Cleared {count} houses"}


@app.post("/sync_houses")
async def sync_houses(houses: List[dict]):
    """
    Sync houses from browser local storage to server database.
    This restores the session when the user returns or if database is empty.
    """
    count = db.sync_houses_from_browser(houses)
    
    return {
        "message": f"Synced {count} houses from browser storage to database",
        "count": count
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
