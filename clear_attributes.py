#!/usr/bin/env python
"""
Clear all attributes from the database
"""
import os

# Load environment variables first
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

from database import get_db_session
from models import Attribute, Experience
from sqlalchemy import text

def clear_attributes():
    """Clear all attributes from the database"""
    session = get_db_session()
    try:
        print("Clearing existing attributes...")
        
        # First, clear the association table
        session.execute(text("DELETE FROM experience_attribute"))
        session.commit()
        print("  - Cleared experience_attribute associations")
        
        # Then delete all attributes
        deleted_count = session.query(Attribute).delete()
        session.commit()
        print(f"  - Deleted {deleted_count} attributes")
        
        print("✅ Attributes cleared successfully")
        
    except Exception as e:
        session.rollback()
        print(f"Error clearing attributes: {str(e)}")
        raise
    finally:
        session.close()

if __name__ == "__main__":
    clear_attributes()