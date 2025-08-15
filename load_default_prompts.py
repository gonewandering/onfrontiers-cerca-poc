#!/usr/bin/env python3
"""
Load default prompt templates from JSON files into the database
"""
import json
import sys
from pathlib import Path
from database import get_db_session
from models import Prompt

def load_prompt_template(template_path: Path) -> dict:
    """Load a prompt template from a JSON file"""
    with open(template_path, 'r') as f:
        return json.load(f)

def create_prompt_from_template(session, template_name: str, template_data: dict, prompt_type: str) -> Prompt:
    """Create a Prompt database record from template data"""
    
    # Extract metadata
    metadata = template_data.get('metadata', {})
    
    prompt = Prompt(
        template_name=template_name,
        version_number=int(metadata.get('version', '1.0').split('.')[0]),  # Convert version to int
        prompt_type=prompt_type,
        system_prompt=template_data['system_prompt'],
        user_prompt_template=template_data['user_prompt_template'],
        response_schema=template_data.get('response_schema'),
        description=metadata.get('description', f'Default {template_name} prompt'),
        model=metadata.get('model', 'gpt-4o-mini'),
        temperature=metadata.get('temperature', 0.1),
        enable_attribute_search=metadata.get('enable_attribute_search', False),
        created_by='system',
        is_active_version=True,
        is_default=True
    )
    
    return prompt

def main():
    """Load all default prompt templates into the database"""
    
    templates_dir = Path('promptTemplates')
    if not templates_dir.exists():
        print("Error: promptTemplates directory not found")
        sys.exit(1)
    
    session = get_db_session()
    
    try:
        # Define template mappings
        template_mappings = [
            ('expert_extraction_fast.json', Prompt.PromptType.EXPERT_EXTRACTION),
            ('expert_extraction.json', Prompt.PromptType.EXPERT_EXTRACTION),
            ('expert_extraction_structured.json', Prompt.PromptType.EXPERT_EXTRACTION),
            ('experience_attribute_analysis.json', Prompt.PromptType.ATTRIBUTE_SEARCH),
            ('expert_search_fast.json', Prompt.PromptType.EXPERT_SEARCH),
            ('expert_search.json', Prompt.PromptType.EXPERT_SEARCH),
        ]
        
        loaded_count = 0
        
        for filename, prompt_type in template_mappings:
            template_path = templates_dir / filename
            
            if not template_path.exists():
                print(f"Warning: Template {filename} not found, skipping...")
                continue
            
            # Use filename without extension as template name
            template_name = template_path.stem
            
            # Check if prompt already exists
            existing = session.query(Prompt).filter(Prompt.template_name == template_name).first()
            if existing:
                print(f"Prompt '{template_name}' already exists, skipping...")
                continue
            
            try:
                # Load template data
                template_data = load_prompt_template(template_path)
                
                # Create prompt record
                prompt = create_prompt_from_template(session, template_name, template_data, prompt_type)
                session.add(prompt)
                
                print(f"Loaded prompt: {template_name} ({prompt_type})")
                loaded_count += 1
                
            except Exception as e:
                print(f"Error loading template {filename}: {str(e)}")
                continue
        
        # Commit all changes
        if loaded_count > 0:
            session.commit()
            print(f"\nSuccessfully loaded {loaded_count} prompt templates into database")
        else:
            print("\nNo new prompts to load")
        
    except Exception as e:
        session.rollback()
        print(f"Error: {str(e)}")
        sys.exit(1)
    finally:
        session.close()

if __name__ == "__main__":
    main()