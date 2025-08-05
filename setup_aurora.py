#!/usr/bin/env python3
"""
Script to set up Aurora PostgreSQL database with pgvector extension
"""

import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from sqlalchemy import create_engine, text

def setup_aurora_database():
    """Set up Aurora PostgreSQL database with pgvector extension"""
    # Try both cluster and instance endpoints
    endpoints = [
        'cerca-aurora-cluster.cluster-cxgooo0scwa0.us-east-1.rds.amazonaws.com',
        'cerca-aurora-instance.cxgooo0scwa0.us-east-1.rds.amazonaws.com'
    ]
    
    for endpoint in endpoints:
        database_url = f'postgresql://postgres:cerca123@{endpoint}:5432/cerca'
        print(f"Trying to connect to: {database_url}")
        
        try:
            # Create engine
            engine = create_engine(database_url, echo=True)
            
            # Test connection
            with engine.connect() as conn:
                print(f"✅ Database connection successful to {endpoint}!")
                
                # Enable pgvector extension
                print("🔧 Enabling pgvector extension...")
                conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
                conn.commit()
                print("✅ pgvector extension enabled!")
                
                # Check pgvector is working
                result = conn.execute(text("SELECT '[1,2,3]'::vector(3)"))
                vector_test = result.fetchone()
                print(f"✅ pgvector test successful: {vector_test[0]}")
                
                # Update our database configuration
                print(f"✅ Use this endpoint: {endpoint}")
                return endpoint
                
        except Exception as e:
            print(f"❌ Connection to {endpoint} failed: {str(e)}")
            continue
    
    print("❌ Could not connect to any Aurora endpoint")
    return None

if __name__ == "__main__":
    print("Setting up Aurora PostgreSQL database with pgvector...")
    endpoint = setup_aurora_database()
    if endpoint:
        print(f"\n🎉 Database setup complete!")
        print(f"✅ Working endpoint: {endpoint}")
        print("You can now run: pipenv run flask db migrate && pipenv run flask db upgrade")
    else:
        print("\n💥 Database setup failed. Please check Aurora configuration.")