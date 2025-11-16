from pydantic import BaseModel
from typing import Optional, Dict


class HouseFeatures(BaseModel):
    """Features of a house used for scoring"""
    garage_cars: int = 0  # Number of cars the garage can hold
    bathrooms: int = 1  # 1, 2, 3, or more
    bathroom_quality: str = "normal"  # normal (+1), modern (+2), needs_updates (-1)
    bedrooms: int = 1   # 1, 2, 3, 4, or more
    square_feet: int = 0  # Square footage of the house
    lot_acres: float = 0.0  # Lot size in acres (+1 per 0.25 acres)
    nice_backyard: bool = False
    curb_appeal: bool = False
    appliances: Dict[str, str] = {}  # {"dishwasher": "modern", "range": "old", ...}
    basement: int = 0  # 0=none, 1=unfinished (+1), 2=finished (+2)
    privacy: str = "normal"  # very_private (+3), private (+2), normal (+1), not_private (-1)
    noise_level: str = "normal"  # quiet (+1), normal (0), loud (-1)
    has_deck: bool = False  # +1
    patio_potential: bool = False  # +2
    has_pool: bool = False  # +3
    near_recreation: bool = False  # +2
    walking_shopping: bool = False  # +2
    has_hoa: bool = False
    hoa_monthly_fee: int = 0  # Monthly HOA fee in dollars


class House(BaseModel):
    """House model with address and features"""
    address: str
    features: HouseFeatures
    notes: Optional[str] = None
    photo: Optional[str] = None  # Base64 encoded image data
    price: Optional[int] = None  # Price in dollars


class HouseResponse(BaseModel):
    """House response with calculated score"""
    id: int
    address: str
    features: HouseFeatures
    notes: Optional[str]
    photo: Optional[str]
    price: Optional[int]
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
    
    # Garage scoring (1 point per car)
    if features.garage_cars > 0:
        garage_score = features.garage_cars
        breakdown['garage'] = f'+{garage_score} ({features.garage_cars}-car garage)'
        total += garage_score
    else:
        breakdown['garage'] = '+0 (No garage)'
    
    # Bathroom scoring (1 point per bathroom, modified by quality)
    bathroom_score = features.bathrooms
    
    # Apply quality modifier
    quality_scores = {
        "modern": (2, "modern"),
        "normal": (1, "normal"),
        "needs_updates": (-1, "needs updates")
    }
    quality_multiplier, quality_label = quality_scores.get(features.bathroom_quality, (1, "normal"))
    bathroom_score = bathroom_score * quality_multiplier
    
    sign = '+' if bathroom_score >= 0 else ''
    breakdown['bathrooms'] = f'{sign}{bathroom_score} ({features.bathrooms} bathroom{"s" if features.bathrooms != 1 else ""}, {quality_label})'
    total += bathroom_score
    
    # Bedroom scoring (1 point per bedroom)
    bedroom_score = features.bedrooms
    breakdown['bedrooms'] = f'+{bedroom_score} ({features.bedrooms} bedroom{"s" if features.bedrooms != 1 else ""})'
    total += bedroom_score
    
    # Square feet scoring (1 point per 500 sq ft)
    if features.square_feet > 0:
        sqft_score = features.square_feet // 500
        breakdown['square_feet'] = f'+{sqft_score} ({features.square_feet} sq ft)'
        total += sqft_score
    else:
        breakdown['square_feet'] = '+0 (No square footage provided)'
    
    # Lot size scoring (1 point per 0.25 acres)
    if features.lot_acres > 0:
        lot_score = int(features.lot_acres / 0.25)
        breakdown['lot_size'] = f'+{lot_score} ({features.lot_acres} acres)'
        total += lot_score
    else:
        breakdown['lot_size'] = '+0 (No lot size provided)'
    
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
    
    # Appliances scoring (old = 1 point, modern = 2 points each, missing = -2 points)
    # Define all possible appliances
    all_appliances = ["dishwasher", "range", "oven", "fridge", "washer", "dryer", "microwave"]
    appliance_score = 0
    appliance_details = []
    
    # Score appliances that are present
    for appliance, condition in features.appliances.items():
        if condition == "modern":
            appliance_score += 2
            appliance_details.append(f"{appliance} (modern, +2)")
        elif condition == "old":
            appliance_score += 1
            appliance_details.append(f"{appliance} (old, +1)")
    
    # Deduct points for missing appliances
    present_appliances = set(features.appliances.keys())
    missing_appliances = [app for app in all_appliances if app not in present_appliances]
    for appliance in missing_appliances:
        appliance_score -= 2
        appliance_details.append(f"{appliance} (missing, -2)")
    
    sign = '+' if appliance_score >= 0 else ''
    breakdown['appliances'] = f'{sign}{appliance_score} ({len(features.appliances)} present, {len(missing_appliances)} missing: {", ".join(appliance_details)})'
    total += appliance_score
    
    # Basement scoring (unfinished +1, finished +2)
    if features.basement == 2:
        basement_score = 2
        breakdown['basement'] = '+2 (Finished basement)'
        total += basement_score
    elif features.basement == 1:
        basement_score = 1
        breakdown['basement'] = '+1 (Unfinished basement)'
        total += basement_score
    else:
        breakdown['basement'] = '+0 (No basement)'
    
    # Privacy scoring
    privacy_scores = {
        "very_private": (3, "Very private"),
        "private": (2, "Private"),
        "normal": (1, "Normal privacy"),
        "not_private": (-1, "Not private")
    }
    privacy_score, privacy_label = privacy_scores.get(features.privacy, (1, "Normal privacy"))
    breakdown['privacy'] = f'{privacy_score:+d} ({privacy_label})'
    total += privacy_score
    
    # Noise level scoring
    noise_scores = {
        "quiet": (1, "Quiet"),
        "normal": (0, "Normal noise"),
        "loud": (-1, "Loud")
    }
    noise_score, noise_label = noise_scores.get(features.noise_level, (0, "Normal noise"))
    breakdown['noise_level'] = f'{noise_score:+d} ({noise_label})'
    total += noise_score
    
    # Deck scoring
    if features.has_deck:
        deck_score = 1
        breakdown['deck'] = '+1 (Has deck)'
        total += deck_score
    else:
        breakdown['deck'] = '+0 (No deck)'
    
    # Patio potential scoring
    if features.patio_potential:
        patio_score = 2
        breakdown['patio_potential'] = '+2 (Patio potential)'
        total += patio_score
    else:
        breakdown['patio_potential'] = '+0 (No patio potential)'
    
    # Pool scoring
    if features.has_pool:
        pool_score = 3
        breakdown['pool'] = '+3 (Has pool)'
        total += pool_score
    else:
        breakdown['pool'] = '+0 (No pool)'
    
    # Near recreation areas scoring
    if features.near_recreation:
        recreation_score = 2
        breakdown['near_recreation'] = '+2 (Near recreation areas)'
        total += recreation_score
    else:
        breakdown['near_recreation'] = '+0 (Not near recreation)'
    
    # Walking distance to shopping scoring
    if features.walking_shopping:
        shopping_score = 2
        breakdown['walking_shopping'] = '+2 (Walking distance to shopping)'
        total += shopping_score
    else:
        breakdown['walking_shopping'] = '+0 (Not walking distance to shopping)'
    
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
