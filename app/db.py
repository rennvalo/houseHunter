"""Database operations for HouseHunter using SQLite"""
import sqlite3
import json
from pathlib import Path
from typing import List, Optional, Dict, Any
from contextlib import contextmanager

# Database path - will be mounted as a volume in Docker
DB_PATH = Path("/database/househunter.db")

# Ensure database directory exists
DB_PATH.parent.mkdir(parents=True, exist_ok=True)


@contextmanager
def get_db():
    """Context manager for database connections"""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row  # Return rows as dictionaries
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    """Initialize the database with required tables"""
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Create houses table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS houses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                address TEXT NOT NULL,
                features TEXT NOT NULL,
                notes TEXT,
                score INTEGER NOT NULL,
                score_breakdown TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create index on score for faster sorting
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_houses_score 
            ON houses(score DESC)
        """)


def add_house(address: str, features: Dict[str, Any], notes: Optional[str], 
              score: int, score_breakdown: Dict[str, str]) -> Dict[str, Any]:
    """Add a new house to the database"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO houses (address, features, notes, score, score_breakdown)
            VALUES (?, ?, ?, ?, ?)
        """, (
            address,
            json.dumps(features),
            notes,
            score,
            json.dumps(score_breakdown)
        ))
        
        house_id = cursor.lastrowid
        
        # Fetch and return the created house
        return get_house_by_id(house_id)


def get_all_houses(order_by_score: bool = True) -> List[Dict[str, Any]]:
    """Get all houses from the database"""
    with get_db() as conn:
        cursor = conn.cursor()
        
        if order_by_score:
            cursor.execute("SELECT * FROM houses ORDER BY score DESC")
        else:
            cursor.execute("SELECT * FROM houses ORDER BY id")
        
        houses = []
        for row in cursor.fetchall():
            houses.append(_row_to_dict(row))
        
        return houses


def get_house_by_id(house_id: int) -> Optional[Dict[str, Any]]:
    """Get a specific house by ID"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM houses WHERE id = ?", (house_id,))
        row = cursor.fetchone()
        
        if row:
            return _row_to_dict(row)
        return None


def update_house(house_id: int, address: str, features: Dict[str, Any], 
                 notes: Optional[str], score: int, score_breakdown: Dict[str, str]) -> Optional[Dict[str, Any]]:
    """Update an existing house"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE houses 
            SET address = ?, features = ?, notes = ?, score = ?, score_breakdown = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (
            address,
            json.dumps(features),
            notes,
            score,
            json.dumps(score_breakdown),
            house_id
        ))
        
        if cursor.rowcount == 0:
            return None
        
        return get_house_by_id(house_id)


def delete_house(house_id: int) -> bool:
    """Delete a house by ID"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM houses WHERE id = ?", (house_id,))
        return cursor.rowcount > 0


def clear_all_houses() -> int:
    """Delete all houses from the database"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) as count FROM houses")
        count = cursor.fetchone()['count']
        cursor.execute("DELETE FROM houses")
        # Reset auto-increment counter
        cursor.execute("DELETE FROM sqlite_sequence WHERE name='houses'")
        return count


def sync_houses_from_browser(houses: List[Dict[str, Any]]) -> int:
    """
    Sync houses from browser localStorage to database.
    Clears existing data and replaces with browser data.
    """
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Clear existing houses
        cursor.execute("DELETE FROM houses")
        cursor.execute("DELETE FROM sqlite_sequence WHERE name='houses'")
        
        # Insert all houses from browser
        for house in houses:
            cursor.execute("""
                INSERT INTO houses (id, address, features, notes, score, score_breakdown)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                house.get('id'),
                house.get('address'),
                json.dumps(house.get('features')),
                house.get('notes'),
                house.get('score'),
                json.dumps(house.get('score_breakdown'))
            ))
        
        return len(houses)


def _row_to_dict(row: sqlite3.Row) -> Dict[str, Any]:
    """Convert a database row to a dictionary"""
    return {
        'id': row['id'],
        'address': row['address'],
        'features': json.loads(row['features']),
        'notes': row['notes'],
        'score': row['score'],
        'score_breakdown': json.loads(row['score_breakdown'])
    }


# Initialize database on module import
init_db()
