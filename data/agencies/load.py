#!/usr/bin/env python3
"""
Load agencies from agencies.csv into the database as attributes of type 'agency' with taxonomy structure
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


def load_agencies_from_csv():
    """Load agencies from CSV and create attributes of type 'agency' with proper taxonomy"""
    csv_path = Path(__file__).parent / "agencies.csv"
    
    if not csv_path.exists():
        print(f"Error: {csv_path} not found")
        return
    
    session = get_db_session()
    
    try:
        # Keep track of created agencies by their full hierarchy path
        agency_cache: Dict[str, Attribute] = {}
        agencies_loaded = 0
        agencies_skipped = 0
        
        # First pass: collect all agencies to understand the hierarchy
        agencies_data = []
        with open(csv_path, 'r', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
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
        
        # Sort by level to ensure parents are created before children
        agencies_data.sort(key=lambda x: x['level'])
        
        print(f"Found {len(agencies_data)} agencies to process")
        
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
                agencies_skipped += 1
                # Important: Cache the existing item so it can be found as a parent
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
            
            print(f"Added: {canonical_name} (depth: {depth}, parent: {parent_attr.name if parent_attr else 'None'})")
            
            # Commit every 50 records to avoid losing work
            if agencies_loaded % 50 == 0:
                session.commit()
                print(f"Committed {agencies_loaded} agencies...")
        
        # Final commit
        session.commit()
        print(f"\nAgency loading complete:")
        print(f"  Loaded: {agencies_loaded} new agencies")
        print(f"  Skipped: {agencies_skipped} existing agencies")
        print(f"  Total processed: {agencies_loaded + agencies_skipped}")
        
        # Print some taxonomy statistics
        depth_counts = {}
        for agency in agency_cache.values():
            depth_counts[agency.depth] = depth_counts.get(agency.depth, 0) + 1
        
        print(f"\nTaxonomy structure:")
        for depth in sorted(depth_counts.keys()):
            print(f"  Depth {depth}: {depth_counts[depth]} agencies")
        
    except Exception as e:
        session.rollback()
        print(f"Error loading agencies: {str(e)}")
        import traceback
        traceback.print_exc()
        raise
    finally:
        session.close()


if __name__ == "__main__":
    print("Loading agencies from CSV with taxonomy structure...")
    load_agencies_from_csv()