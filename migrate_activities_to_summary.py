#!/usr/bin/env python
"""
Migrate data from 'activities' column to 'summary' column in Experience table
"""
import os

# Load environment variables first
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

from database import get_db_session
from sqlalchemy import text

def migrate_activities_to_summary():
    """Copy data from activities column to summary column and then drop activities"""
    session = get_db_session()
    try:
        print("Starting migration: activities -> summary")
        
        # First, check if activities column exists
        check_query = text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'experience' 
            AND column_name = 'activities'
        """)
        
        result = session.execute(check_query)
        if not result.fetchone():
            print("✅ Activities column doesn't exist (already migrated)")
            return
        
        # Copy data from activities to summary where summary is empty or null
        print("Copying data from activities to summary...")
        update_query = text("""
            UPDATE experience 
            SET summary = COALESCE(
                CASE 
                    WHEN summary IS NULL OR summary = '' THEN activities
                    ELSE summary
                END,
                summary
            )
            WHERE activities IS NOT NULL AND activities != ''
        """)
        
        result = session.execute(update_query)
        rows_updated = result.rowcount
        session.commit()
        print(f"  Updated {rows_updated} rows")
        
        # Now drop the activities column
        print("Dropping activities column...")
        drop_query = text("ALTER TABLE experience DROP COLUMN IF EXISTS activities")
        session.execute(drop_query)
        session.commit()
        print("  ✅ Activities column dropped")
        
        print("\n✅ Migration complete!")
        
    except Exception as e:
        session.rollback()
        print(f"❌ Error during migration: {str(e)}")
        raise
    finally:
        session.close()

if __name__ == "__main__":
    migrate_activities_to_summary()