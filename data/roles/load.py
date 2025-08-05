#!/usr/bin/env python3
"""
Load roles from roles.csv into the database as attributes of type 'role'
"""

import csv
import sys
import os
from pathlib import Path
from typing import Dict, Optional

# Add project root to path to import modules
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from database import get_db_session
from models import Attribute
from lib.embedding_service import embedding_service


def load_roles_from_csv():
    """Load roles from CSV and create attributes of type 'role'"""
    csv_path = Path(__file__).parent / "roles.csv"
    
    if not csv_path.exists():
        print(f"Error: {csv_path} not found")
        return
    
    session = get_db_session()
    
    try:
        roles_loaded = 0
        roles_skipped = 0
        
        # Read roles from CSV
        roles_data = []
        with open(csv_path, 'r', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                name = row['name'].strip()
                depth = int(row['depth']) if row['depth'].strip() else 0
                summary = row['summary'].strip()
                
                if not name:
                    continue
                    
                roles_data.append({
                    'name': name,
                    'depth': depth,
                    'summary': summary
                })
        
        print(f"Found {len(roles_data)} roles to process")
        
        for role_data in roles_data:
            name = role_data['name']
            depth = role_data['depth']
            summary = role_data['summary']
            
            # Check if this role already exists
            existing = session.query(Attribute).filter_by(
                type="role",
                name=name
            ).first()
            
            if existing:
                print(f"Skipping existing role: {name}")
                roles_skipped += 1
                continue
            
            # Create the role attribute
            # For embedding generation, combine name with summary for better context
            embedding_text = f"{name}: {summary}" if summary else name
            
            role_attr = Attribute(
                name=name,
                type="role",
                summary=embedding_text,  # This will be used for embedding generation
                parent_id=None,  # Roles are flat, no hierarchy
                depth=depth
            )
            
            session.add(role_attr)
            roles_loaded += 1
            
            print(f"Added: {name} (depth: {depth})")
            
            # Commit every 50 records to avoid losing work
            if roles_loaded % 50 == 0:
                session.commit()
                print(f"Committed {roles_loaded} roles...")
        
        # Final commit
        session.commit()
        print(f"\nRole loading complete:")
        print(f"  Loaded: {roles_loaded} new roles")
        print(f"  Skipped: {roles_skipped} existing roles")
        print(f"  Total processed: {roles_loaded + roles_skipped}")
        
        # Print some statistics
        depth_counts = {}
        all_roles = session.query(Attribute).filter_by(type="role").all()
        for role in all_roles:
            depth_counts[role.depth] = depth_counts.get(role.depth, 0) + 1
        
        print(f"\nRole structure:")
        for depth in sorted(depth_counts.keys()):
            print(f"  Depth {depth}: {depth_counts[depth]} roles")
        
    except Exception as e:
        session.rollback()
        print(f"Error loading roles: {str(e)}")
        import traceback
        traceback.print_exc()
        raise
    finally:
        session.close()


if __name__ == "__main__":
    print("Loading roles from CSV...")
    load_roles_from_csv()