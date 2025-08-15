#!/usr/bin/env python
"""
Clear and reload attributes from data files
"""
import os
import csv
from pathlib import Path

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
        
    except Exception as e:
        session.rollback()
        print(f"Error clearing attributes: {str(e)}")
        raise
    finally:
        session.close()

def load_agencies():
    """Load agencies from CSV file"""
    session = get_db_session()
    try:
        csv_path = Path("data/agencies/agencies.csv")
        print(f"\nLoading agencies from {csv_path}")
        
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            count = 0
            
            for row in reader:
                # Skip empty rows
                if not row.get('canonical_name'):
                    continue
                
                # Create agency attribute
                level_str = row.get('level', '0').strip()
                depth = int(level_str) if level_str else 0
                
                agency = Attribute(
                    name=row['canonical_name'],
                    type='agency',
                    summary=f"Federal Agency: {row['canonical_name']} ({row.get('abbreviation', '')})",
                    depth=depth,
                    parent_id=None  # We could add hierarchy support later
                )
                
                session.add(agency)
                count += 1
                
                # Commit in batches
                if count % 50 == 0:
                    session.commit()
                    print(f"  - Loaded {count} agencies...")
            
            session.commit()
            print(f"  ✅ Loaded {count} agencies total")
            
    except Exception as e:
        session.rollback()
        print(f"Error loading agencies: {str(e)}")
        raise
    finally:
        session.close()

def load_roles():
    """Load roles from CSV file"""
    session = get_db_session()
    try:
        csv_path = Path("data/roles/roles.csv")
        print(f"\nLoading roles from {csv_path}")
        
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            count = 0
            
            for row in reader:
                # Skip empty rows
                if not row.get('name'):
                    continue
                
                # Create role attribute
                role = Attribute(
                    name=row['name'],
                    type='role',
                    summary=row.get('summary', f"Role: {row['name']}"),
                    depth=int(row.get('depth', 0)),
                    parent_id=None
                )
                
                session.add(role)
                count += 1
                
                # Commit in batches
                if count % 20 == 0:
                    session.commit()
                    print(f"  - Loaded {count} roles...")
            
            session.commit()
            print(f"  ✅ Loaded {count} roles total")
            
    except Exception as e:
        session.rollback()
        print(f"Error loading roles: {str(e)}")
        raise
    finally:
        session.close()

def add_sample_skills():
    """Add some sample skills for testing"""
    session = get_db_session()
    try:
        print("\nAdding sample skills...")
        
        sample_skills = [
            # Programming languages
            ("Python", "Programming language for data science and backend development"),
            ("JavaScript", "Programming language for web development"),
            ("Java", "Enterprise programming language"),
            ("C#", "Microsoft .NET programming language"),
            ("Go", "Modern systems programming language"),
            ("Ruby", "Dynamic programming language"),
            ("TypeScript", "Typed superset of JavaScript"),
            
            # Cloud & Infrastructure
            ("AWS", "Amazon Web Services cloud platform"),
            ("Azure", "Microsoft Azure cloud platform"),
            ("Google Cloud", "Google Cloud Platform"),
            ("Docker", "Container platform"),
            ("Kubernetes", "Container orchestration platform"),
            ("Terraform", "Infrastructure as Code tool"),
            
            # Data & ML
            ("Machine Learning", "Building and deploying ML models"),
            ("Data Analysis", "Analyzing and interpreting data"),
            ("SQL", "Database query language"),
            ("TensorFlow", "Machine learning framework"),
            ("PyTorch", "Machine learning framework"),
            ("Pandas", "Data manipulation library"),
            
            # Security
            ("Cybersecurity", "Information security practices"),
            ("DevSecOps", "Security in DevOps practices"),
            ("NIST", "NIST security framework knowledge"),
            ("Zero Trust", "Zero trust security architecture"),
            
            # Management & Process
            ("Project Management", "Managing projects and teams"),
            ("Agile", "Agile development methodology"),
            ("Scrum", "Scrum framework"),
            ("Program Management", "Managing programs and portfolios"),
            ("Change Management", "Managing organizational change"),
            
            # Federal/Gov specific
            ("FAR", "Federal Acquisition Regulation knowledge"),
            ("FedRAMP", "Federal Risk and Authorization Management Program"),
            ("Section 508", "Accessibility compliance"),
            ("FISMA", "Federal Information Security Management Act"),
        ]
        
        count = 0
        for skill_name, skill_summary in sample_skills:
            skill = Attribute(
                name=skill_name,
                type='skill',
                summary=f"Skill: {skill_summary}",
                depth=0,
                parent_id=None
            )
            session.add(skill)
            count += 1
        
        session.commit()
        print(f"  ✅ Added {count} sample skills")
        
    except Exception as e:
        session.rollback()
        print(f"Error adding sample skills: {str(e)}")
        raise
    finally:
        session.close()

def add_sample_programs():
    """Add some sample programs for testing"""
    session = get_db_session()
    try:
        print("\nAdding sample programs...")
        
        sample_programs = [
            # Major federal programs
            ("Login.gov", "Federal single sign-on platform"),
            ("USAJobs", "Federal employment portal"),
            ("Grants.gov", "Federal grants management system"),
            ("SAM.gov", "System for Award Management"),
            ("VA.gov", "Veterans Affairs digital services"),
            ("Healthcare.gov", "Health insurance marketplace"),
            ("IRS Free File", "Free tax filing program"),
            
            # Defense programs
            ("F-35 Joint Strike Fighter", "Fifth-generation fighter aircraft program"),
            ("DISA Encore III", "IT services contract vehicle"),
            ("Army Futures Command", "Army modernization initiative"),
            ("Space Force", "U.S. Space Force establishment"),
            
            # Technology initiatives
            ("Cloud Smart", "Federal cloud adoption strategy"),
            ("CDM", "Continuous Diagnostics and Mitigation program"),
            ("TMF", "Technology Modernization Fund"),
            ("Centers of Excellence", "GSA digital transformation program"),
            
            # Agency-specific
            ("NASA Artemis", "Return to the Moon program"),
            ("Census 2020", "2020 U.S. Census program"),
            ("FDA MyStudies", "FDA mobile health platform"),
            ("USDA Farmers.gov", "USDA farmer portal"),
        ]
        
        count = 0
        for program_name, program_summary in sample_programs:
            program = Attribute(
                name=program_name,
                type='program',
                summary=f"Program: {program_summary}",
                depth=0,
                parent_id=None
            )
            session.add(program)
            count += 1
        
        session.commit()
        print(f"  ✅ Added {count} sample programs")
        
    except Exception as e:
        session.rollback()
        print(f"Error adding sample programs: {str(e)}")
        raise
    finally:
        session.close()

def verify_load():
    """Verify the attributes were loaded correctly"""
    session = get_db_session()
    try:
        print("\n" + "=" * 60)
        print("VERIFICATION")
        print("=" * 60)
        
        # Count by type
        for attr_type in ['agency', 'role', 'skill', 'program', 'seniority']:
            count = session.query(Attribute).filter(Attribute.type == attr_type).count()
            if count > 0:
                print(f"  {attr_type.capitalize()}: {count} attributes")
        
        total = session.query(Attribute).count()
        print(f"\n  Total attributes: {total}")
        
        # Show sample of each type
        print("\n" + "-" * 40)
        print("Sample attributes:")
        for attr_type in ['agency', 'role', 'skill', 'program']:
            samples = session.query(Attribute).filter(
                Attribute.type == attr_type
            ).limit(3).all()
            if samples:
                print(f"\n  {attr_type.capitalize()}:")
                for sample in samples:
                    print(f"    - {sample.name}")
        
    finally:
        session.close()

def main():
    """Main function to reload all attributes"""
    print("=" * 60)
    print("RELOADING ATTRIBUTES FROM DATA FILES")
    print("=" * 60)
    
    # Step 1: Clear existing attributes
    clear_attributes()
    
    # Step 2: Load agencies
    load_agencies()
    
    # Step 3: Load roles
    load_roles()
    
    # Step 4: Add sample skills
    add_sample_skills()
    
    # Step 5: Add sample programs
    add_sample_programs()
    
    # Step 6: Verify
    verify_load()
    
    print("\n" + "=" * 60)
    print("✅ RELOAD COMPLETE!")
    print("=" * 60)

if __name__ == "__main__":
    main()