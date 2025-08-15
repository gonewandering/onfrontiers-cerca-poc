#!/usr/bin/env python
"""
Load new prompt templates into the database
"""
import json
from pathlib import Path
from database import get_db_session
from models import Prompt

def load_prompt_template(template_file: str):
    """Load a prompt template from file and save to database"""
    
    template_path = Path('promptTemplates') / template_file
    with open(template_path, 'r') as f:
        template = json.load(f)
    
    session = get_db_session()
    try:
        # Extract metadata
        metadata = template.get('metadata', {})
        template_name = metadata.get('name', template_file.replace('.json', ''))
        
        # Map template file name to template_name field
        template_name_map = {
            'expert_extraction_structured.json': 'expert_extraction_structured',
            'experience_attribute_analysis.json': 'experience_attribute_analysis'
        }
        
        db_template_name = template_name_map.get(template_file, template_file.replace('.json', ''))
        
        # Check if template already exists
        existing = session.query(Prompt).filter(
            Prompt.template_name == db_template_name
        ).first()
        
        if existing:
            print(f"Template '{db_template_name}' already exists with version {existing.version_number}")
            
            # Ask if user wants to create a new version
            response = input("Create new version? (y/n): ")
            if response.lower() != 'y':
                return
            
            # Get next version number
            latest_version = session.query(Prompt).filter(
                Prompt.template_name == db_template_name
            ).order_by(Prompt.version_number.desc()).first()
            next_version = latest_version.version_number + 1
        else:
            next_version = 1
        
        # Determine prompt type
        prompt_type_map = {
            'expert_extraction_structured': 'expert_extraction',
            'experience_attribute_analysis': 'attribute_search'
        }
        prompt_type = prompt_type_map.get(db_template_name, 'custom')
        
        # Create new prompt version
        prompt = Prompt(
            template_name=db_template_name,
            version_number=next_version,
            prompt_type=prompt_type,
            system_prompt=template['system_prompt'],
            user_prompt_template=template['user_prompt_template'],
            response_schema=template.get('response_schema'),
            description=metadata.get('description'),
            model=metadata.get('model', 'gpt-4o-mini'),
            temperature=float(metadata.get('temperature', 0.1)),
            enable_attribute_search=metadata.get('enable_attribute_search', False),
            created_by='system',
            is_active_version=True,  # Set as active by default
            is_default=False,
            version_notes=f"Loaded from {template_file}"
        )
        
        # Deactivate other versions if this is set as active
        if prompt.is_active_version:
            session.query(Prompt).filter(
                Prompt.template_name == db_template_name,
                Prompt.is_active_version == True
            ).update({'is_active_version': False})
        
        session.add(prompt)
        session.commit()
        
        print(f"✅ Created prompt '{db_template_name}' version {next_version}")
        
    except Exception as e:
        session.rollback()
        print(f"❌ Error loading template: {str(e)}")
    finally:
        session.close()

def main():
    """Load the new prompt templates"""
    
    print("Loading new prompt templates into database...")
    print("-" * 50)
    
    templates_to_load = [
        'expert_extraction_structured.json',
        'experience_attribute_analysis.json'
    ]
    
    for template_file in templates_to_load:
        print(f"\nLoading: {template_file}")
        load_prompt_template(template_file)
    
    print("\n" + "-" * 50)
    print("Done!")

if __name__ == "__main__":
    main()