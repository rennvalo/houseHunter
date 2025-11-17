"""
Property Cache Module
Caches property search results from RapidAPI to reduce API calls and improve performance.
Properties are cached for 30 days and indexed by ZIP code and address for fast lookup.
"""

import sqlite3
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List, Dict, Any


# Database path
DB_PATH = Path(__file__).parent.parent / "database" / "property_cache.db"


def init_cache_db():
    """Initialize the property cache database with schema"""
    DB_PATH.parent.mkdir(exist_ok=True)
    
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    
    # Create cached_properties table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS cached_properties (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            zip_code TEXT NOT NULL,
            address TEXT NOT NULL,
            bedrooms INTEGER,
            bathrooms REAL,
            sqft INTEGER,
            lot_sqft INTEGER,
            lot_acres REAL,
            garage_cars INTEGER,
            year_built INTEGER,
            property_type TEXT,
            price INTEGER,
            photo_url TEXT,
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            raw_data TEXT,
            UNIQUE(zip_code, address)
        )
    """)
    
    # Create indexes for fast lookup
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_zip_code ON cached_properties(zip_code)
    """)
    
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_address ON cached_properties(address)
    """)
    
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_last_updated ON cached_properties(last_updated)
    """)
    
    conn.commit()
    conn.close()
    
    print(f"Property cache database initialized at {DB_PATH}")


def cache_properties(properties: List[Dict[Any, Any]], zip_code: str):
    """
    Cache a list of properties from a ZIP code search.
    Updates existing entries or inserts new ones.
    
    Args:
        properties: List of property dicts from API response
        zip_code: ZIP code these properties belong to
    """
    if not properties:
        return
    
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    
    cached_count = 0
    
    for prop in properties:
        try:
            # Extract address
            prop_address = ""
            if prop.get("location") and prop["location"].get("address"):
                addr = prop["location"]["address"]
                prop_address = addr.get("line", "") or ""
            elif prop.get("address"):
                if isinstance(prop["address"], dict):
                    prop_address = prop["address"].get("line", "") or ""
                else:
                    prop_address = str(prop["address"]) if prop["address"] else ""
            
            if not prop_address:
                continue
            
            # Normalize address for consistency
            prop_address = prop_address.lower().strip()
            
            # Extract property details
            description = prop.get("description", {})
            
            bedrooms = (
                description.get("beds") or 
                prop.get("beds") or 
                description.get("beds_min") or
                0
            )
            
            bathrooms_full = (
                description.get("baths_full") or 
                prop.get("baths_full") or 
                description.get("baths") or
                0
            )
            
            bathrooms_half = (
                description.get("baths_half") or 
                prop.get("baths_half") or 
                0
            )
            
            bathrooms = bathrooms_full + (bathrooms_half * 0.5)
            
            sqft = (
                description.get("sqft") or 
                prop.get("sqft") or
                description.get("lot_sqft") or
                0
            )
            
            lot_sqft = (
                description.get("lot_sqft") or 
                prop.get("lot_sqft") or 
                0
            )
            
            lot_acres = round(lot_sqft / 43560, 2) if lot_sqft else 0
            
            garage = (
                description.get("garage") or 
                prop.get("garage") or
                description.get("garage_spaces") or 
                prop.get("garage_spaces") or
                0
            )
            
            year_built = (
                description.get("year_built") or 
                prop.get("year_built") or 
                None
            )
            
            property_type = (
                description.get("type") or 
                prop.get("prop_type") or 
                prop.get("type") or
                "Unknown"
            )
            
            # Extract price
            price = None
            if prop.get("list_price"):
                price = prop["list_price"]
            elif prop.get("price"):
                price = prop["price"]
            elif description.get("sold_price"):
                price = description["sold_price"]
            
            # Extract primary photo URL
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
            
            # Store raw JSON for future reference
            raw_data = json.dumps(prop)
            
            # Insert or update property
            cursor.execute("""
                INSERT INTO cached_properties 
                (zip_code, address, bedrooms, bathrooms, sqft, lot_sqft, lot_acres, 
                 garage_cars, year_built, property_type, price, photo_url, raw_data, last_updated)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(zip_code, address) 
                DO UPDATE SET
                    bedrooms = excluded.bedrooms,
                    bathrooms = excluded.bathrooms,
                    sqft = excluded.sqft,
                    lot_sqft = excluded.lot_sqft,
                    lot_acres = excluded.lot_acres,
                    garage_cars = excluded.garage_cars,
                    year_built = excluded.year_built,
                    property_type = excluded.property_type,
                    price = excluded.price,
                    photo_url = excluded.photo_url,
                    raw_data = excluded.raw_data,
                    last_updated = CURRENT_TIMESTAMP
            """, (
                zip_code, prop_address, bedrooms, bathrooms, sqft, lot_sqft, lot_acres,
                garage, year_built, property_type, price, photo_url, raw_data
            ))
            
            cached_count += 1
            
        except Exception as e:
            print(f"Error caching property: {str(e)}")
            continue
    
    conn.commit()
    conn.close()
    
    print(f"Cached {cached_count} properties for ZIP code {zip_code}")


def lookup_cached_property(address: str, zip_code: str) -> Optional[Dict[str, Any]]:
    """
    Look up a property in the cache by address and ZIP code.
    Returns None if not found or if cache is older than 360 days.
    
    Args:
        address: Full street address (will be normalized for matching)
        zip_code: ZIP code
        
    Returns:
        Property data dict if found and fresh, None otherwise
    """
    import re
    
    # Normalize search address (same logic as caching)
    addr_without_zip = re.sub(r'\s*\d{5}(?:-\d{4})?\s*$', '', address).strip()
    state_match = re.search(r'[,\s]+(AL|AK|AZ|AR|CA|CO|CT|DE|FL|GA|HI|ID|IL|IN|IA|KS|KY|LA|ME|MD|MA|MI|MN|MS|MO|MT|NE|NV|NH|NJ|NM|NY|NC|ND|OH|OK|OR|PA|RI|SC|SD|TN|TX|UT|VT|VA|WA|WV|WI|WY)\s*$', addr_without_zip, re.IGNORECASE)
    
    if state_match:
        addr_without_state = addr_without_zip[:state_match.start()].strip()
        if ',' in addr_without_state:
            street_address_raw = addr_without_state.split(',')[0].strip()
        else:
            words = addr_without_state.split()
            if len(words) > 3:
                street_address_raw = ' '.join(words[:-1])
            else:
                street_address_raw = addr_without_state
    else:
        if ',' in addr_without_zip:
            street_address_raw = addr_without_zip.split(',')[0].strip()
        else:
            words = addr_without_zip.split()
            if len(words) > 3:
                street_address_raw = ' '.join(words[:-1])
            else:
                street_address_raw = addr_without_zip
    
    search_address = re.sub(r'\s*[#,]?\s*(unit|apt|apartment|suite|ste|d)\s*[\d\w-]+', '', street_address_raw, flags=re.IGNORECASE).strip().lower()
    
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Calculate cutoff date (360 days ago)
    cutoff_date = (datetime.now() - timedelta(days=360)).isoformat()
    
    # Search for matching address in this ZIP code
    cursor.execute("""
        SELECT * FROM cached_properties
        WHERE zip_code = ?
        AND last_updated > ?
        ORDER BY last_updated DESC
    """, (zip_code, cutoff_date))
    
    rows = cursor.fetchall()
    conn.close()
    
    # Find best address match
    for row in rows:
        cached_addr = row["address"].lower().strip()
        
        # Check if addresses match (fuzzy matching)
        if search_address in cached_addr or cached_addr in search_address:
            return {
                "address": address,  # Return original address format
                "bedrooms": row["bedrooms"],
                "bathrooms": row["bathrooms"],
                "square_feet": row["sqft"],
                "lot_acres": row["lot_acres"],
                "garage_cars": row["garage_cars"],
                "year_built": row["year_built"],
                "property_type": row["property_type"],
                "price": row["price"],
                "photo_url": row["photo_url"]
            }
    
    return None


def get_cached_properties_by_zip(zip_code: str, max_age_days: int = 360) -> List[Dict[str, Any]]:
    """
    Get all cached properties for a ZIP code that are within max_age_days old.
    
    Args:
        zip_code: ZIP code to search
        max_age_days: Maximum age of cached data in days (default 360)
        
    Returns:
        List of property dicts
    """
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cutoff_date = (datetime.now() - timedelta(days=max_age_days)).isoformat()
    
    cursor.execute("""
        SELECT * FROM cached_properties
        WHERE zip_code = ?
        AND last_updated > ?
        ORDER BY last_updated DESC
    """, (zip_code, cutoff_date))
    
    rows = cursor.fetchall()
    conn.close()
    
    return [dict(row) for row in rows]


def search_cached_properties(zip_code: str, max_price: int, max_age_days: int = 360) -> Optional[List[Dict[str, Any]]]:
    """
    Search cached properties by ZIP code and max price.
    Returns None if no properties found or cache is too old.
    
    Args:
        zip_code: ZIP code to search
        max_price: Maximum price to filter by
        max_age_days: Maximum age of cached data in days (default 360)
        
    Returns:
        List of property dicts if found and fresh, None otherwise
    """
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cutoff_date = (datetime.now() - timedelta(days=max_age_days)).isoformat()
    
    cursor.execute("""
        SELECT * FROM cached_properties
        WHERE zip_code = ?
        AND price IS NOT NULL
        AND price <= ?
        AND last_updated > ?
        ORDER BY price ASC
    """, (zip_code, max_price, cutoff_date))
    
    rows = cursor.fetchall()
    conn.close()
    
    if not rows:
        return None
    
    # Format results to match search endpoint response
    properties = []
    for row in rows:
        properties.append({
            "address": row["address"],
            "price": row["price"],
            "bedrooms": row["bedrooms"],
            "bathrooms": row["bathrooms"],
            "square_feet": row["sqft"],
            "lot_acres": row["lot_acres"],
            "garage_cars": row["garage_cars"],
            "photo_url": row["photo_url"],
            "property_type": row["property_type"],
            "year_built": row["year_built"]
        })
    
    return properties


def clear_old_cache(days: int = 90):
    """
    Remove cached properties older than specified days.
    
    Args:
        days: Delete cache entries older than this many days (default 90)
    """
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    
    cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()
    
    cursor.execute("""
        DELETE FROM cached_properties
        WHERE last_updated < ?
    """, (cutoff_date,))
    
    deleted_count = cursor.rowcount
    conn.commit()
    conn.close()
    
    print(f"Deleted {deleted_count} cached properties older than {days} days")
    return deleted_count
