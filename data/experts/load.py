#!/usr/bin/env python3
"""
Expert JSON Loader Script

This script loads experts from experts.json using the fast LLM extraction method.
It processes the profile_text as unstructured input and stores profile_id and 
profile_url in the expert's meta field.

Usage:
    python data/experts/load.py [--limit N] [--start N] [--batch-size N]

Options:
    --limit N       Limit processing to N records (default: all)
    --start N       Start from record N (default: 0)
    --batch-size N  Process N records per batch (default: 10)
    --dry-run       Show what would be processed without saving to database
"""

import os
import sys
import json
import argparse
import time
from datetime import datetime

# Add the project root to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from models import Expert, Experience, Attribute
from lib.llm_extractor import LLMExtractor
from database import get_db_session
from sqlalchemy.exc import IntegrityError

class ExpertLoader:
    def __init__(self, batch_size=5, dry_run=False):
        self.batch_size = batch_size
        self.dry_run = dry_run
        self.session = None if dry_run else get_db_session()
        self.extractor = LLMExtractor()
        
        # Statistics
        self.stats = {
            'processed': 0,
            'successful': 0,
            'failed': 0,
            'skipped': 0,
            'start_time': time.time()
        }
        
    def __enter__(self):
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            self.session.close()
            
    def log(self, message, level='INFO'):
        """Simple logging with timestamp"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        print(f"[{timestamp}] {level}: {message}")
        
    def process_expert_record(self, record):
        """Process a single expert record from JSON"""
        try:
            profile_id = record.get('profile_id', '').strip()
            profile_text = record.get('profile_text', '').strip()
            profile_url = record.get('profile_url', '').strip()
            
            if not profile_id:
                self.log(f"Skipping record: missing profile_id", 'WARN')
                self.stats['skipped'] += 1
                return False
                
            if not profile_text:
                self.log(f"Skipping {profile_id}: missing profile_text", 'WARN')
                self.stats['skipped'] += 1
                return False
            
            # Check if expert already exists (by profile_id in meta)
            if not self.dry_run:
                existing = self.session.query(Expert).filter(
                    Expert.meta.op('->>')('profile_id') == profile_id
                ).first()
                
                if existing:
                    self.log(f"Skipping {profile_id}: expert already exists (ID: {existing.id})", 'INFO')
                    self.stats['skipped'] += 1
                    return False
            
            # Extract expert data using optimized batch method
            self.log(f"Processing {profile_id}: Extracting from {len(profile_text)} chars of text")
            
            extraction_start = time.time()
            extracted_data = self.extractor.extract_expert_with_attributes_fast(profile_text)
            extraction_time = time.time() - extraction_start
            
            expert_data = extracted_data.get('expert', {})
            experiences_data = extracted_data.get('experiences', [])
            
            if not expert_data.get('name'):
                self.log(f"Failed {profile_id}: No expert name extracted", 'ERROR')
                self.stats['failed'] += 1
                return False
                
            # Create meta object with profile information
            meta = {
                'profile_id': profile_id,
                'profile_url': profile_url,
                'raw': profile_text,
                'extraction_time': round(extraction_time, 2),
                'processed_at': datetime.now().isoformat()
            }
            
            if self.dry_run:
                self.log(f"DRY RUN - Would create expert: {expert_data.get('name')} with {len(experiences_data)} experiences")
                self.stats['successful'] += 1
                return True
            
            # Create expert record
            expert = Expert(
                name=expert_data.get('name')[:30],  # Truncate to fit field limit
                summary=expert_data.get('summary', ''),
                status=True,
                meta=meta
            )
            
            self.session.add(expert)
            self.session.flush()  # Get expert ID without committing
            
            # Create experiences and attributes
            created_experiences = 0
            for exp_data in experiences_data:
                try:
                    # Handle date parsing
                    start_date_str = exp_data.get('start_date')
                    end_date_str = exp_data.get('end_date')
                    
                    if not start_date_str or not end_date_str:
                        continue
                        
                    start_date = datetime.fromisoformat(start_date_str).date()
                    
                    if end_date_str.lower() in ['present', 'current', 'ongoing', 'now']:
                        end_date = datetime.now().date()
                    else:
                        end_date = datetime.fromisoformat(end_date_str).date()
                    
                    experience = Experience(
                        expert_id=expert.id,
                        employer=exp_data.get('employer'),
                        position=exp_data.get('position'),
                        start_date=start_date,
                        end_date=end_date,
                        summary=exp_data.get('summary', '')
                    )
                    
                    self.session.add(experience)
                    self.session.flush()
                    
                    # Associate only existing attributes using IDs from two-step extraction
                    matched_attributes = 0
                    attribute_ids = exp_data.get('attribute_ids', [])
                    
                    for attr_id in attribute_ids:
                        # Get attribute from database by ID
                        attribute = self.session.query(Attribute).filter(Attribute.id == attr_id).first()
                        
                        if attribute:
                            # Associate existing database attribute with this experience
                            if experience not in attribute.experiences:
                                attribute.experiences.append(experience)
                            matched_attributes += 1
                        else:
                            self.log(f"Warning: Attribute ID {attr_id} not found in database for {profile_id}", 'WARN')
                    
                    self.log(f"  Matched {matched_attributes} existing attributes for experience: {exp_data.get('position', 'Unknown')} at {exp_data.get('employer', 'Unknown')}")
                    
                    created_experiences += 1
                    
                except Exception as exp_error:
                    self.log(f"Warning: Failed to create experience for {profile_id}: {str(exp_error)}", 'WARN')
                    continue
            
            # Commit less frequently for better performance
            self.session.commit()
            
            self.log(f"Success {profile_id}: Created expert '{expert_data.get('name')}' (ID: {expert.id}) with {created_experiences} experiences in {extraction_time:.2f}s")
            self.stats['successful'] += 1
            return True
            
        except Exception as e:
            if not self.dry_run:
                self.session.rollback()
            self.log(f"Failed {profile_id}: {str(e)}", 'ERROR')
            self.stats['failed'] += 1
            return False
            
    def load_experts(self, json_file, limit=None, start=0):
        """Load experts from JSON file"""
        self.log(f"Starting expert loading from {json_file}")
        self.log(f"Configuration: limit={limit}, start={start}, batch_size={self.batch_size}, dry_run={self.dry_run}")
        
        # Load JSON data
        with open(json_file, 'r', encoding='utf-8') as f:
            experts_data = json.load(f)
        
        self.log(f"Loaded {len(experts_data)} expert records from JSON")
        
        # Apply start and limit
        if start > 0:
            experts_data = experts_data[start:]
        if limit:
            experts_data = experts_data[:limit]
            
        self.log(f"Processing {len(experts_data)} records after applying start={start}, limit={limit}")
        
        batch = []
        for record_num, record in enumerate(experts_data, start=start):
            self.stats['processed'] += 1
            batch.append((record_num, record))
            
            # Process batch when full
            if len(batch) >= self.batch_size:
                self.process_batch(batch)
                batch = []
                
            # Progress update every 20 records (smaller batches for JSON)
            if self.stats['processed'] % 20 == 0:
                elapsed = time.time() - self.stats['start_time']
                rate = self.stats['processed'] / elapsed if elapsed > 0 else 0
                self.log(f"Progress: {self.stats['processed']} processed ({rate:.1f}/s), {self.stats['successful']} successful, {self.stats['failed']} failed")
        
        # Process remaining batch
        if batch:
            self.process_batch(batch)
            
        self.print_final_stats()
        
    def process_batch(self, batch):
        """Process a batch of expert records"""
        self.log(f"Processing batch of {len(batch)} records...")
        
        for record_num, record in batch:
            self.process_expert_record(record)
            
    def print_final_stats(self):
        """Print final processing statistics"""
        elapsed = time.time() - self.stats['start_time']
        
        self.log("=" * 60)
        self.log("FINAL STATISTICS")
        self.log("=" * 60)
        self.log(f"Total processed: {self.stats['processed']}")
        self.log(f"Successful: {self.stats['successful']}")
        self.log(f"Failed: {self.stats['failed']}")
        self.log(f"Skipped: {self.stats['skipped']}")
        self.log(f"Total time: {elapsed:.2f}s")
        self.log(f"Average rate: {self.stats['processed'] / elapsed:.2f} records/s")
        self.log(f"Success rate: {(self.stats['successful'] / max(1, self.stats['processed'])) * 100:.1f}%")
        

def main():
    parser = argparse.ArgumentParser(description='Load experts from JSON file')
    parser.add_argument('--limit', type=int, help='Limit number of records to process')
    parser.add_argument('--start', type=int, default=0, help='Start from record number (0-based)')
    parser.add_argument('--batch-size', type=int, default=5, help='Batch size for processing')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be processed without saving')
    parser.add_argument('--json-file', default='data/experts/experts.json', help='Path to JSON file')
    
    args = parser.parse_args()
    
    # Validate JSON file exists
    if not os.path.exists(args.json_file):
        print(f"ERROR: JSON file not found: {args.json_file}")
        return 1
    
    # Get actual record count from JSON
    try:
        with open(args.json_file, 'r') as f:
            data = json.load(f)
            total_records = len(data)
    except Exception as e:
        print(f"ERROR: Failed to read JSON file: {str(e)}")
        return 1
    
    # Confirm processing for large datasets
    if not args.dry_run and not args.limit and total_records > 50:
        response = input(f"WARNING: This will process all {total_records} experts. Continue? (y/N): ")
        if response.lower() != 'y':
            print("Cancelled by user")
            return 0
    
    try:
        with ExpertLoader(batch_size=args.batch_size, dry_run=args.dry_run) as loader:
            loader.load_experts(args.json_file, limit=args.limit, start=args.start)
        return 0
        
    except KeyboardInterrupt:
        print("\nStopped by user")
        return 0
    except Exception as e:
        print(f"ERROR: {str(e)}")
        return 1

if __name__ == '__main__':
    exit(main())