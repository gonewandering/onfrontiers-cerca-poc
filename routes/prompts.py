from flask import request
from flask_restful import Resource
from models import Prompt
from database import get_db_session
from datetime import datetime
import json

class PromptListResource(Resource):
    def get(self):
        """List all prompt templates with their active versions, or all versions if show_all_versions=true"""
        session = get_db_session()
        try:
            # Get query parameters
            prompt_type = request.args.get('type')
            show_all_versions = request.args.get('show_all_versions', 'false').lower() in ('true', '1', 'yes')
            template_name = request.args.get('template_name')
            
            # Build query
            query = session.query(Prompt)
            
            if prompt_type:
                query = query.filter(Prompt.prompt_type == prompt_type)
            
            if template_name:
                query = query.filter(Prompt.template_name == template_name)
            
            if not show_all_versions:
                # Only show active versions by default
                query = query.filter(Prompt.is_active_version == True)
            
            # Order by template name, then by version number descending
            prompts = query.order_by(Prompt.template_name, Prompt.version_number.desc()).all()
            
            return {
                'prompts': [
                    {
                        'id': prompt.id,
                        'template_name': prompt.template_name,
                        'version_number': prompt.version_number,
                        'prompt_type': prompt.prompt_type,
                        'description': prompt.description,
                        'model': prompt.model,
                        'temperature': prompt.temperature,
                        'enable_attribute_search': prompt.enable_attribute_search,
                        'is_active_version': prompt.is_active_version,
                        'is_default': prompt.is_default,
                        'version_notes': prompt.version_notes,
                        'created_at': prompt.created_at.isoformat(),
                        'updated_at': prompt.updated_at.isoformat(),
                        'created_by': prompt.created_by,
                        # Legacy fields for backward compatibility
                        'name': prompt.name,
                        'version': prompt.version,
                        'is_active': prompt.is_active
                    } for prompt in prompts
                ]
            }
        finally:
            session.close()
    
    def post(self):
        """Create a new prompt version"""
        session = get_db_session()
        try:
            data = request.get_json()
            
            # Validate required fields
            required_fields = ['template_name', 'prompt_type', 'system_prompt', 'user_prompt_template']
            for field in required_fields:
                if not data.get(field):
                    return {'message': f'Missing required field: {field}'}, 400
            
            # Validate response_schema if provided
            response_schema = data.get('response_schema')
            if response_schema and isinstance(response_schema, str):
                try:
                    response_schema = json.loads(response_schema)
                except json.JSONDecodeError:
                    return {'message': 'Invalid JSON in response_schema'}, 400
            
            # Determine next version number
            template_name = data['template_name']
            latest_version = session.query(Prompt).filter(
                Prompt.template_name == template_name
            ).order_by(Prompt.version_number.desc()).first()
            
            next_version = 1 if not latest_version else latest_version.version_number + 1
            
            # If this is set as active, deactivate other versions
            is_active_version = bool(data.get('is_active_version', data.get('is_active', True)))
            if is_active_version:
                session.query(Prompt).filter(
                    Prompt.template_name == template_name,
                    Prompt.is_active_version == True
                ).update({'is_active_version': False})
            
            # Create new prompt version
            prompt = Prompt(
                template_name=template_name,
                version_number=next_version,
                prompt_type=data['prompt_type'],
                system_prompt=data['system_prompt'],
                user_prompt_template=data['user_prompt_template'],
                response_schema=response_schema,
                description=data.get('description'),
                model=data.get('model', 'gpt-4o-mini'),
                temperature=float(data.get('temperature', 0.1)),
                enable_attribute_search=bool(data.get('enable_attribute_search', False)),
                created_by=data.get('created_by', 'user'),
                is_active_version=is_active_version,
                is_default=bool(data.get('is_default', False)),
                version_notes=data.get('version_notes')
            )
            
            session.add(prompt)
            session.commit()
            
            return {
                'id': prompt.id,
                'template_name': prompt.template_name,
                'version_number': prompt.version_number,
                'prompt_type': prompt.prompt_type,
                'is_active_version': prompt.is_active_version,
                'message': 'Prompt version created successfully'
            }, 201
            
        except ValueError as e:
            return {'message': f'Invalid data type: {str(e)}'}, 400
        except Exception as e:
            session.rollback()
            return {'message': f'Failed to create prompt: {str(e)}'}, 500
        finally:
            session.close()

class PromptVersionActivateResource(Resource):
    def post(self, prompt_id):
        """Activate a specific prompt version"""
        session = get_db_session()
        try:
            prompt = session.query(Prompt).filter(Prompt.id == prompt_id).first()
            if not prompt:
                return {'message': 'Prompt version not found'}, 404
            
            # Deactivate all other versions of this template
            session.query(Prompt).filter(
                Prompt.template_name == prompt.template_name,
                Prompt.is_active_version == True
            ).update({'is_active_version': False})
            
            # Activate this version
            prompt.is_active_version = True
            prompt.updated_at = datetime.utcnow()
            
            session.commit()
            
            return {
                'id': prompt.id,
                'template_name': prompt.template_name,
                'version_number': prompt.version_number,
                'is_active_version': prompt.is_active_version,
                'message': 'Prompt version activated successfully'
            }
            
        except Exception as e:
            session.rollback()
            return {'message': f'Failed to activate prompt version: {str(e)}'}, 500
        finally:
            session.close()

class PromptResource(Resource):
    def get(self, prompt_id):
        """Get a specific prompt by ID"""
        session = get_db_session()
        try:
            prompt = session.query(Prompt).filter(Prompt.id == prompt_id).first()
            if not prompt:
                return {'message': 'Prompt not found'}, 404
            
            return {
                'id': prompt.id,
                'template_name': prompt.template_name,
                'version_number': prompt.version_number,
                'prompt_type': prompt.prompt_type,
                'system_prompt': prompt.system_prompt,
                'user_prompt_template': prompt.user_prompt_template,
                'response_schema': prompt.response_schema,
                'description': prompt.description,
                'model': prompt.model,
                'temperature': prompt.temperature,
                'enable_attribute_search': prompt.enable_attribute_search,
                'is_active_version': prompt.is_active_version,
                'is_default': prompt.is_default,
                'version_notes': prompt.version_notes,
                'created_at': prompt.created_at.isoformat(),
                'updated_at': prompt.updated_at.isoformat(),
                'created_by': prompt.created_by,
                # Legacy fields for backward compatibility
                'name': prompt.name,
                'version': prompt.version,
                'is_active': prompt.is_active
            }
        finally:
            session.close()
    
    def put(self, prompt_id):
        """Update an existing prompt"""
        session = get_db_session()
        try:
            prompt = session.query(Prompt).filter(Prompt.id == prompt_id).first()
            if not prompt:
                return {'message': 'Prompt not found'}, 404
            
            data = request.get_json()
            
            # Update fields if provided
            if 'name' in data:
                # Check for name conflicts (excluding current prompt)
                existing = session.query(Prompt).filter(
                    Prompt.name == data['name'],
                    Prompt.id != prompt_id
                ).first()
                if existing:
                    return {'message': f'Prompt with name "{data["name"]}" already exists'}, 409
                prompt.name = data['name']
            
            if 'prompt_type' in data:
                prompt.prompt_type = data['prompt_type']
            
            if 'system_prompt' in data:
                prompt.system_prompt = data['system_prompt']
            
            if 'user_prompt_template' in data:
                prompt.user_prompt_template = data['user_prompt_template']
            
            if 'response_schema' in data:
                response_schema = data['response_schema']
                if isinstance(response_schema, str):
                    try:
                        response_schema = json.loads(response_schema)
                    except json.JSONDecodeError:
                        return {'message': 'Invalid JSON in response_schema'}, 400
                prompt.response_schema = response_schema
            
            if 'description' in data:
                prompt.description = data['description']
            
            if 'version' in data:
                prompt.version = data['version']
            
            if 'model' in data:
                prompt.model = data['model']
            
            if 'temperature' in data:
                try:
                    prompt.temperature = float(data['temperature'])
                except ValueError:
                    return {'message': 'Temperature must be a number'}, 400
            
            if 'enable_attribute_search' in data:
                prompt.enable_attribute_search = bool(data['enable_attribute_search'])
            
            if 'is_active' in data:
                prompt.is_active = bool(data['is_active'])
            
            if 'is_default' in data:
                prompt.is_default = bool(data['is_default'])
            
            # Update timestamp
            prompt.updated_at = datetime.utcnow()
            
            session.commit()
            
            return {
                'id': prompt.id,
                'name': prompt.name,
                'message': 'Prompt updated successfully'
            }
            
        except Exception as e:
            session.rollback()
            return {'message': f'Failed to update prompt: {str(e)}'}, 500
        finally:
            session.close()
    
    def delete(self, prompt_id):
        """Delete a prompt (or deactivate if it's a default)"""
        session = get_db_session()
        try:
            prompt = session.query(Prompt).filter(Prompt.id == prompt_id).first()
            if not prompt:
                return {'message': 'Prompt not found'}, 404
            
            # Don't delete default prompts, just deactivate them
            if prompt.is_default:
                prompt.is_active = False
                prompt.updated_at = datetime.utcnow()
                session.commit()
                return {'message': 'Default prompt deactivated successfully'}
            else:
                session.delete(prompt)
                session.commit()
                return {'message': 'Prompt deleted successfully'}
            
        except Exception as e:
            session.rollback()
            return {'message': f'Failed to delete prompt: {str(e)}'}, 500
        finally:
            session.close()

class PromptByNameResource(Resource):
    def get(self, template_name):
        """Get the active version of a prompt template by name (used by LLM extractor)"""
        session = get_db_session()
        try:
            prompt = session.query(Prompt).filter(
                Prompt.template_name == template_name,
                Prompt.is_active_version == True
            ).first()
            
            if not prompt:
                return {'message': 'Active prompt template not found'}, 404
            
            # Return in the same format as the JSON templates
            return {
                'system_prompt': prompt.system_prompt,
                'user_prompt_template': prompt.user_prompt_template,
                'response_schema': prompt.response_schema,
                'metadata': {
                    'name': prompt.template_name,
                    'description': prompt.description,
                    'version': str(prompt.version_number),
                    'model': prompt.model,
                    'temperature': prompt.temperature,
                    'enable_attribute_search': prompt.enable_attribute_search
                }
            }
        finally:
            session.close()