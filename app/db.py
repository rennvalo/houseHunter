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
        
        # Create users table (optional accounts)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Check if houses table exists and if it has user_id column
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='houses'")
        table_exists = cursor.fetchone() is not None
        
        if table_exists:
            # Check if user_id column exists
            cursor.execute("PRAGMA table_info(houses)")
            columns = [column[1] for column in cursor.fetchall()]
            
            if 'user_id' not in columns:
                # Old schema - need to add user_id column
                print("Migrating database: Adding user_id column to houses table...")
                cursor.execute("ALTER TABLE houses ADD COLUMN user_id TEXT DEFAULT 'legacy'")
                # Set all existing houses to legacy user
                cursor.execute("UPDATE houses SET user_id = 'legacy' WHERE user_id IS NULL OR user_id = ''")
                print("Migration complete: All existing houses assigned to 'legacy' user")
            
            if 'photo' not in columns:
                # Add photo column if it doesn't exist
                print("Migrating database: Adding photo column to houses table...")
                cursor.execute("ALTER TABLE houses ADD COLUMN photo TEXT")
                print("Migration complete: photo column added")
        else:
            # New installation - create houses table with user_id
            cursor.execute("""
                CREATE TABLE houses (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    address TEXT NOT NULL,
                    features TEXT NOT NULL,
                    notes TEXT,
                    photo TEXT,
                    score INTEGER NOT NULL,
                    score_breakdown TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
        
        # Create index on user_id and score for faster filtering/sorting
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_houses_user_score 
            ON houses(user_id, score DESC)
        """)


def add_house(user_id: str, address: str, features: Dict[str, Any], notes: Optional[str], 
              photo: Optional[str], score: int, score_breakdown: Dict[str, str]) -> Dict[str, Any]:
    """Add a new house to the database"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO houses (user_id, address, features, notes, photo, score, score_breakdown)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            user_id,
            address,
            json.dumps(features),
            notes,
            photo,
            score,
            json.dumps(score_breakdown)
        ))
        
        house_id = cursor.lastrowid
        
        # Fetch and return the created house (within same connection)
        cursor.execute("SELECT * FROM houses WHERE id = ? AND user_id = ?", (house_id, user_id))
        row = cursor.fetchone()
        
        if row:
            return _row_to_dict(row)
        return None


def get_all_houses(user_id: str, order_by_score: bool = True) -> List[Dict[str, Any]]:
    """Get all houses for a specific user from the database"""
    with get_db() as conn:
        cursor = conn.cursor()
        
        if order_by_score:
            cursor.execute("SELECT * FROM houses WHERE user_id = ? ORDER BY score DESC", (user_id,))
        else:
            cursor.execute("SELECT * FROM houses WHERE user_id = ? ORDER BY id", (user_id,))
        
        houses = []
        for row in cursor.fetchall():
            houses.append(_row_to_dict(row))
        
        return houses


def get_house_by_id(user_id: str, house_id: int) -> Optional[Dict[str, Any]]:
    """Get a specific house by ID (must belong to user)"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM houses WHERE id = ? AND user_id = ?", (house_id, user_id))
        row = cursor.fetchone()
        
        if row:
            return _row_to_dict(row)
        return None


def update_house(user_id: str, house_id: int, address: str, features: Dict[str, Any], 
                 notes: Optional[str], photo: Optional[str], score: int, score_breakdown: Dict[str, str]) -> Optional[Dict[str, Any]]:
    """Update an existing house (must belong to user)"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE houses 
            SET address = ?, features = ?, notes = ?, photo = ?, score = ?, score_breakdown = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ? AND user_id = ?
        """, (
            address,
            json.dumps(features),
            notes,
            photo,
            score,
            json.dumps(score_breakdown),
            house_id,
            user_id
        ))
        
        if cursor.rowcount == 0:
            return None
        
        # Fetch and return the updated house (within same connection)
        cursor.execute("SELECT * FROM houses WHERE id = ? AND user_id = ?", (house_id, user_id))
        row = cursor.fetchone()
        
        if row:
            return _row_to_dict(row)
        return None


def delete_house(user_id: str, house_id: int) -> bool:
    """Delete a house by ID (must belong to user)"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM houses WHERE id = ? AND user_id = ?", (house_id, user_id))
        return cursor.rowcount > 0


def clear_all_houses(user_id: str) -> int:
    """Delete all houses for a specific user"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) as count FROM houses WHERE user_id = ?", (user_id,))
        count = cursor.fetchone()['count']
        cursor.execute("DELETE FROM houses WHERE user_id = ?", (user_id,))
        return count


def sync_houses_from_browser(user_id: str, houses: List[Dict[str, Any]]) -> int:
    """
    Sync houses from browser localStorage to database for a specific user.
    Clears existing user data and replaces with browser data.
    """
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Clear existing houses for this user
        cursor.execute("DELETE FROM houses WHERE user_id = ?", (user_id,))
        
        # Insert all houses from browser for this user
        for house in houses:
            cursor.execute("""
                INSERT INTO houses (user_id, address, features, notes, score, score_breakdown)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                user_id,
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
        'photo': row['photo'] if 'photo' in row.keys() else None,
        'score': row['score'],
        'score_breakdown': json.loads(row['score_breakdown'])
    }


# User authentication functions
def create_user(email: str, password: str) -> Optional[Dict[str, Any]]:
    """Create a new user account"""
    import hashlib
    password_hash = hashlib.sha256(password.encode()).hexdigest()
    
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO users (email, password_hash)
                VALUES (?, ?)
            """, (email, password_hash))
            
            user_id = cursor.lastrowid
            return {
                'id': user_id,
                'email': email
            }
    except sqlite3.IntegrityError:
        # Email already exists
        return None


def verify_user(email: str, password: str) -> Optional[Dict[str, Any]]:
    """Verify user credentials and return user info"""
    import hashlib
    password_hash = hashlib.sha256(password.encode()).hexdigest()
    
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, email FROM users 
            WHERE email = ? AND password_hash = ?
        """, (email, password_hash))
        
        row = cursor.fetchone()
        if row:
            return {
                'id': row['id'],
                'email': row['email']
            }
        return None


# Initialize database on module import
init_db()
