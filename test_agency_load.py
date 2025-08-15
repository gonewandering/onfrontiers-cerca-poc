#!/usr/bin/env python3
"""
Test loading a few agencies to verify the process works
"""

import csv
import sys
import os
from pathlib import Path

# Load environment variables first
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

# Add project root to path to import modules
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from database import get_db_session
from models import Attribute
from lib.embedding_service import embedding_service


def test_load_few_agencies():
    """Test loading just the first 5 agencies"""
    csv_path = Path("data/agencies/agencies.csv")
    
    if not csv_path.exists():
        print(f"Error: {csv_path} not found")
        return
    
    session = get_db_session()
    
    try:
        print("Testing agency loading with first 5 agencies...")
        
        # Read first 5 agencies
        agencies_data = []
        with open(csv_path, 'r', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            count = 0
            for row in reader:
                canonical_name = row['canonical_name'].strip()
                hierarchy_path = row['hierarchy_path'].strip()
                level = int(row['level']) if row['level'].strip() else 1
                
                if not canonical_name:
                    continue
                    
                agencies_data.append({
                    'name': canonical_name,
                    'hierarchy_path': hierarchy_path,
                    'level': level
                })
                
                count += 1
                if count >= 5:  # Only first 5
                    break
        
        # Sort by level to ensure parents are created before children
        agencies_data.sort(key=lambda x: x['level'])
        
        print(f"Loading {len(agencies_data)} test agencies:")
        for agency_data in agencies_data:
            print(f"  - {agency_data['name']} (level: {agency_data['level']})")
        
        agencies_loaded = 0
        agency_cache = {}
        
        for agency_data in agencies_data:
            canonical_name = agency_data['name']
            hierarchy_path = agency_data['hierarchy_path']
            level = agency_data['level']
            
            # Check if this agency already exists
            existing = session.query(Attribute).filter_by(
                type="agency",
                name=canonical_name
            ).first()
            
            if existing:
                print(f"Skipping existing agency: {canonical_name}")
                agency_cache[hierarchy_path] = existing
                continue
            
            # Parse hierarchy to find parent
            parent_attr = None
            depth = level - 1  # Convert level (1,2,3) to depth (0,1,2)
            
            if hierarchy_path and '>' in hierarchy_path and depth > 0:
                # Split hierarchy path to find parent
                path_parts = hierarchy_path.split('>')
                if len(path_parts) >= 2:
                    # Parent is the second-to-last part in the hierarchy
                    parent_name = path_parts[-2].strip()
                    
                    # Look for parent in cache first
                    parent_path = '>'.join(path_parts[:-1])
                    parent_attr = agency_cache.get(parent_path)
                    
                    if not parent_attr:
                        # Try to find parent by name in database
                        parent_attr = session.query(Attribute).filter_by(
                            type="agency",
                            name=parent_name
                        ).first()
                        
                        # If we found the parent in DB, add it to cache for future lookups
                        if parent_attr:
                            agency_cache[parent_path] = parent_attr
                    
                    # Log if parent not found (this might indicate data issues)
                    if not parent_attr:
                        print(f"Warning: Parent '{parent_name}' not found for '{canonical_name}'")
            
            # Create the agency attribute
            # Parse hierarchy path into array for summary
            path_array = hierarchy_path.split('>') if hierarchy_path else [canonical_name]
            formatted_summary = ' > '.join(path_array)  # Use " > " for better readability
            
            # For embedding generation, combine canonical name with full taxonomy path
            # This gives the embedding model both the specific name and hierarchical context
            embedding_text = f"{canonical_name}: {formatted_summary}" if hierarchy_path else canonical_name
            
            print(f"Creating: {canonical_name} (depth: {depth}, parent: {parent_attr.name if parent_attr else 'None'})")
            print(f"  Summary: {embedding_text}")
            
            agency_attr = Attribute(
                name=canonical_name,
                type="agency",
                summary=embedding_text,  # This will be used for embedding generation
                parent_id=parent_attr.id if parent_attr else None,
                depth=depth
            )
            
            session.add(agency_attr)
            agency_cache[hierarchy_path] = agency_attr
            agencies_loaded += 1
        
        # Commit the test batch
        print(f"\nCommitting {agencies_loaded} agencies...")
        session.commit()
        print("✅ Test commit successful!")
        
        # Verify they were saved
        print("\nVerifying saved agencies:")
        saved_agencies = session.query(Attribute).filter_by(type="agency").all()
        for agency in saved_agencies:
            parent_name = session.query(Attribute).filter_by(id=agency.parent_id).first().name if agency.parent_id else None
            print(f"  - {agency.name} (depth: {agency.depth}, parent: {parent_name})")
            if agency.embedding:
                print(f"    Embedding: {len(str(agency.embedding))} chars")
            else:
                print(f"    Embedding: None")
        
        print(f"\nTest complete: Loaded {agencies_loaded} agencies successfully")
        
    except Exception as e:
        session.rollback()
        print(f"Error in test loading: {str(e)}")
        import traceback
        traceback.print_exc()
        raise
    finally:
        session.close()


if __name__ == "__main__":
    test_load_few_agencies()