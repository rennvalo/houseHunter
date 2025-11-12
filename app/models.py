from pydantic import BaseModel
from typing import Optional


class HouseFeatures(BaseModel):
    """Features of a house used for scoring"""
    has_garage: bool = False
    two_car_garage: bool = False
    bathrooms: int = 1  # 1, 2, 3, or more
    bedrooms: int = 1   # 1, 2, 3, 4, or more
    square_feet: int = 0  # Square footage of the house
    nice_backyard: bool = False
    curb_appeal: bool = False
    modern_appliances: bool = False
    has_hoa: bool = False
    hoa_monthly_fee: int = 0  # Monthly HOA fee in dollars


class House(BaseModel):
    """House model with address and features"""
    address: str
    features: HouseFeatures
    notes: Optional[str] = None


class HouseResponse(BaseModel):
    """House response with calculated score"""
    id: int
    address: str
    features: HouseFeatures
    notes: Optional[str]
    score: int
    score_breakdown: dict


class ScoreBreakdown(BaseModel):
    """Detailed breakdown of scoring"""
    garage_score: int
    bathroom_score: int
    bedroom_score: int
    backyard_score: int
    curb_appeal_score: int
    appliances_score: int
    total_score: int
    details: dict


def calculate_score(features: HouseFeatures) -> tuple[int, dict]:
    """
    Calculate the total score for a house based on its features.
    
    Returns:
        tuple: (total_score, breakdown_dict)
    """
    breakdown = {}
    total = 0
    
    # Garage scoring
    if features.two_car_garage:
        garage_score = 2
        breakdown['garage'] = '+2 (Two-car garage)'
    elif features.has_garage:
        garage_score = 1
        breakdown['garage'] = '+1 (Has garage)'
    else:
        garage_score = -1
        breakdown['garage'] = '-1 (No garage)'
    total += garage_score
    
    # Bathroom scoring
    if features.bathrooms >= 3:
        bathroom_score = 2
        breakdown['bathrooms'] = f'+2 ({features.bathrooms} bathrooms)'
    elif features.bathrooms == 2:
        bathroom_score = 1
        breakdown['bathrooms'] = '+1 (2 bathrooms)'
    else:
        bathroom_score = 0
        breakdown['bathrooms'] = f'+0 ({features.bathrooms} bathroom{"s" if features.bathrooms != 1 else ""})'
    total += bathroom_score
    
    # Bedroom scoring
    if features.bedrooms >= 4:
        bedroom_score = 4
        breakdown['bedrooms'] = f'+4 ({features.bedrooms} bedrooms)'
    elif features.bedrooms == 3:
        bedroom_score = 2
        breakdown['bedrooms'] = '+2 (3 bedrooms)'
    elif features.bedrooms == 2:
        bedroom_score = 1
        breakdown['bedrooms'] = '+1 (2 bedrooms)'
    else:
        bedroom_score = 0
        breakdown['bedrooms'] = f'+0 ({features.bedrooms} bedroom{"s" if features.bedrooms != 1 else ""})'
    total += bedroom_score
    
    # Square feet scoring (1 point per 500 sq ft)
    if features.square_feet > 0:
        sqft_score = features.square_feet // 500
        breakdown['square_feet'] = f'+{sqft_score} ({features.square_feet} sq ft)'
        total += sqft_score
    else:
        breakdown['square_feet'] = '+0 (No square footage provided)'
    
    # Backyard scoring
    if features.nice_backyard:
        backyard_score = 2
        breakdown['backyard'] = '+2 (Nice backyard)'
        total += backyard_score
    else:
        breakdown['backyard'] = '+0 (No backyard or not nice)'
    
    # Curb appeal scoring
    if features.curb_appeal:
        curb_score = 1
        breakdown['curb_appeal'] = '+1 (Has curb appeal)'
        total += curb_score
    else:
        breakdown['curb_appeal'] = '+0 (No curb appeal)'
    
    # Appliances scoring
    if features.modern_appliances:
        appliances_score = 1
        breakdown['appliances'] = '+1 (Modern appliances)'
        total += appliances_score
    else:
        breakdown['appliances'] = '+0 (No modern appliances)'
    
    # HOA scoring
    if features.has_hoa:
        hoa_score = -1  # Base penalty for having HOA
        # Additional penalty: -1 for every $100 in monthly fees
        fee_penalty = -(features.hoa_monthly_fee // 100)
        hoa_score += fee_penalty
        total += hoa_score
        breakdown['hoa'] = f'{hoa_score} (HOA: ${features.hoa_monthly_fee}/month)'
    else:
        breakdown['hoa'] = '+0 (No HOA)'
    
    return total, breakdown
