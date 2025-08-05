#!/usr/bin/env python3
"""
Script to set up PostgreSQL database with pgvector extension
Run this once the database credentials are corrected
"""

import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from sqlalchemy import create_engine, text
from database import DATABASE_URL

def setup_database():
    """Set up PostgreSQL database with pgvector extension"""
    print(f"Connecting to: {DATABASE_URL}")
    
    try:
        # Create engine
        engine = create_engine(DATABASE_URL, echo=True)
        
        # Test connection
        with engine.connect() as conn:
            print("✅ Database connection successful!")
            
            # Enable pgvector extension
            print("🔧 Enabling pgvector extension...")
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            conn.commit()
            print("✅ pgvector extension enabled!")
            
            # Check pgvector is working
            result = conn.execute(text("SELECT '[1,2,3]'::vector(3)"))
            vector_test = result.fetchone()
            print(f"✅ pgvector test successful: {vector_test[0]}")
            
    except Exception as e:
        print(f"❌ Database setup failed: {str(e)}")
        return False
    
    return True

if __name__ == "__main__":
    print("Setting up PostgreSQL database with pgvector...")
    if setup_database():
        print("\n🎉 Database setup complete!")
        print("You can now run: flask db migrate && flask db upgrade")
    else:
        print("\n💥 Database setup failed. Please check your credentials.")