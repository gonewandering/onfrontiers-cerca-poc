from flask import request
from flask_restful import Resource
from models import Expert, Experience, Attribute
from lib.llm_extractor import LLMExtractor
from database import get_db_session
from datetime import datetime

class ExpertResource(Resource):
    def get(self, expert_id=None):
        session = get_db_session()
        try:
            if expert_id:
                expert = session.query(Expert).filter(Expert.id == expert_id).first()
                if not expert:
                    return {'message': 'Expert not found'}, 404
                return {
                    'id': expert.id,
                    'name': expert.name,
                    'summary': expert.summary,
                    'status': expert.status,
                    'meta': expert.meta,
                    'experiences': [
                        {
                            'id': exp.id,
                            'start_date': exp.start_date.isoformat(),
                            'end_date': exp.end_date.isoformat(),
                            'summary': exp.summary,
                            'attributes': [
                                {
                                    'id': attr.id,
                                    'name': attr.name,
                                    'type': attr.type,
                                    'summary': attr.summary
                                } for attr in exp.attributes
                            ]
                        } for exp in expert.experiences
                    ]
                }
            else:
                experts = session.query(Expert).all()
                return {
                    'experts': [
                        {
                            'id': expert.id,
                            'name': expert.name,
                            'summary': expert.summary,
                            'status': expert.status,
                            'meta': expert.meta,
                            'experiences': [
                                {
                                    'id': exp.id,
                                    'start_date': exp.start_date.isoformat(),
                                    'end_date': exp.end_date.isoformat(),
                                    'summary': exp.summary,
                                    'attributes': [
                                        {
                                            'id': attr.id,
                                            'name': attr.name,
                                            'type': attr.type,
                                            'summary': attr.summary
                                        } for attr in exp.attributes
                                    ]
                                } for exp in expert.experiences
                            ]
                        } for expert in experts
                    ]
                }
        finally:
            session.close()

    def post(self):
        print('POSTing an Expert')
        session = get_db_session()
        try:
            # Check if request contains JSON data (structured) or text (unstructured)
            content_type = request.headers.get('Content-Type', '')
            
            if 'application/json' in content_type:
                # Handle structured input (original functionality)
                data = request.get_json()
                expert = Expert(
                    name=data.get('name'),
                    summary=data.get('summary'),
                    status=data.get('status', True)
                )
                session.add(expert)
                session.commit()
                return {
                    'id': expert.id,
                    'name': expert.name,
                    'summary': expert.summary,
                    'status': expert.status,
                    'meta': expert.meta
                }, 201
            
            elif 'text/plain' in content_type or content_type == '':
                # Handle unstructured text input
                text = request.get_data(as_text=True)
                if not text.strip():
                    return {'message': 'Empty text provided'}, 400
                
                # Extract structured data using LLM
                try:
                    print(f"DEBUG - Starting LLM extraction for text length: {len(text)} characters")
                    extractor = LLMExtractor()
                    extracted_data = extractor.extract_expert_data(text)
                    print("DEBUG - LLM extraction successful")
                    print("DEBUG - Extracted data structure:", {
                        'expert_keys': list(extracted_data.get('expert', {}).keys()) if 'expert' in extracted_data else 'No expert key',
                        'experiences_count': len(extracted_data.get('experiences', [])) if 'experiences' in extracted_data else 'No experiences key',
                        'raw_data': extracted_data
                    })
                except Exception as llm_error:
                    print(f"ERROR - LLM extraction failed: {str(llm_error)}")
                    print(f"ERROR - LLM error type: {type(llm_error).__name__}")
                    import traceback
                    traceback.print_exc()
                    return {'message': f'LLM extraction failed: {str(llm_error)}'}, 400
                
                # Create expert
                try:
                    print("DEBUG - Creating expert record")
                    expert_data = extracted_data.get('expert', {})
                    expert_name = expert_data.get('name')
                    expert_summary = expert_data.get('summary')
                    
                    if not expert_name:
                        raise ValueError("Missing expert name in extracted data")
                    if not expert_summary:
                        raise ValueError("Missing expert summary in extracted data")
                    
                    print(f"DEBUG - Expert name: '{expert_name}', summary length: {len(expert_summary)}")
                    
                    expert = Expert(
                        name=expert_name,
                        summary=expert_summary,
                        status=True,
                        meta={'raw': text}
                    )
                    print("DEBUG - Expert object created successfully")
                except Exception as expert_error:
                    print(f"ERROR - Expert creation failed: {str(expert_error)}")
                    print(f"ERROR - Expert data available: {extracted_data.get('expert', 'No expert data')}")
                    return {'message': f'Expert creation failed: {str(expert_error)}'}, 400
                session.add(expert)
                session.flush()  # Get the expert ID without committing
                
                # Create experiences and attributes
                created_experiences = []
                
                experiences_data = extracted_data.get('experiences', [])
                print(f"DEBUG - Processing {len(experiences_data)} experiences")
                
                for i, exp_data in enumerate(experiences_data):
                    try:
                        print(f"DEBUG - Processing experience {i+1}/{len(experiences_data)}")
                        print(f"DEBUG - Experience data keys: {list(exp_data.keys()) if isinstance(exp_data, dict) else 'Not a dict'}")
                    except Exception as exp_debug_error:
                        print(f"ERROR - Failed to debug experience {i+1}: {str(exp_debug_error)}")
                        continue
                    # Handle "present" as current date
                    start_date_str = exp_data['start_date']
                    end_date_str = exp_data['end_date']
                    
                    start_date = datetime.fromisoformat(start_date_str).date()
                    
                    if end_date_str.lower() in ['present', 'current', 'ongoing', 'now']:
                        end_date = datetime.now().date()
                    else:
                        end_date = datetime.fromisoformat(end_date_str).date()
                    
                    experience = Experience(
                        expert_id=expert.id,
                        start_date=start_date,
                        end_date=end_date,
                        summary=exp_data['summary']
                    )
                    session.add(experience)
                    session.flush()  # Get the experience ID
                    
                    # Create attributes for this experience
                    created_attributes = []
                    
                    for attr_data in exp_data['attributes']:
                        # Only process attributes that have a valid ID (existing attributes found by LLM search)
                        attr_id = attr_data.get('id')
                        if attr_id is not None and str(attr_id).lower() not in ['none', 'null', '']:
                            # Use existing attribute by ID
                            existing_attr = session.query(Attribute).filter(Attribute.id == attr_id).first()
                            if existing_attr:
                                # Associate existing attribute with this experience
                                existing_attr.experiences.append(experience)
                                created_attributes.append({
                                    'id': existing_attr.id,
                                    'name': existing_attr.name,
                                    'type': existing_attr.type,
                                    'summary': existing_attr.summary,
                                    'existing': True
                                })
                                print(f"DEBUG - Using existing {existing_attr.type}: {existing_attr.name} (ID: {existing_attr.id})")
                            else:
                                print(f"WARNING - Attribute ID {attr_id} not found in database, skipping")
                        else:
                            print(f"DEBUG - Skipping attribute without ID: {attr_data.get('name', 'Unknown')} ({attr_data.get('type', 'Unknown type')})")
                    
                    created_experiences.append({
                        'start_date': experience.start_date.isoformat(),
                        'end_date': experience.end_date.isoformat(),
                        'summary': experience.summary,
                        'attributes': created_attributes
                    })
                
                session.commit()
                
                return {
                    'id': expert.id,
                    'name': expert.name,
                    'summary': expert.summary,
                    'status': expert.status,
                    'meta': expert.meta,
                    'experiences': created_experiences,
                    'extraction_source': 'llm'
                }, 201
            
            else:
                return {'message': 'Unsupported content type. Use application/json or text/plain'}, 400
                
        except Exception as e:
            session.rollback()
            print(f"ERROR - Unexpected error in POST /api/experts: {str(e)}")
            print(f"ERROR - Exception type: {type(e).__name__}")
            import traceback
            traceback.print_exc()
            
            # More descriptive error message
            error_msg = f"{type(e).__name__}: {str(e)}"
            return {'message': error_msg}, 400
        finally:
            session.close()

    def put(self, expert_id):
        session = get_db_session()
        try:
            expert = session.query(Expert).filter(Expert.id == expert_id).first()
            if not expert:
                return {'message': 'Expert not found'}, 404
            
            data = request.get_json()
            expert.name = data.get('name', expert.name)
            expert.summary = data.get('summary', expert.summary)
            expert.status = data.get('status', expert.status)
            
            session.commit()
            return {
                'id': expert.id,
                'name': expert.name,
                'summary': expert.summary,
                'status': expert.status,
                'meta': expert.meta
            }
        except Exception as e:
            session.rollback()
            return {'message': str(e)}, 400
        finally:
            session.close()

    def delete(self, expert_id):
        session = get_db_session()
        try:
            expert = session.query(Expert).filter(Expert.id == expert_id).first()
            if not expert:
                return {'message': 'Expert not found'}, 404
            
            session.delete(expert)
            session.commit()
            return {'message': 'Expert deleted successfully'}
        except Exception as e:
            session.rollback()
            return {'message': str(e)}, 400
        finally:
            session.close()

class ExpertListResource(Resource):
    def get(self):
        session = get_db_session()
        try:
            experts = session.query(Expert).all()
            return {
                'experts': [
                    {
                        'id': expert.id,
                        'name': expert.name,
                        'summary': expert.summary,
                        'status': expert.status,
                        'meta': expert.meta,
                        'experiences': [
                            {
                                'id': exp.id,
                                'start_date': exp.start_date.isoformat(),
                                'end_date': exp.end_date.isoformat(),
                                'summary': exp.summary,
                                'attributes': [
                                    {
                                        'id': attr.id,
                                        'name': attr.name,
                                        'type': attr.type,
                                        'summary': attr.summary
                                    } for attr in exp.attributes
                                ]
                            } for exp in expert.experiences
                        ]
                    } for expert in experts
                ]
            }
        finally:
            session.close()

    def post(self):
        session = get_db_session()
        try:
            content_type = request.headers.get('Content-Type', '')
            
            if 'application/json' in content_type:
                # Handle structured input (original functionality)
                data = request.get_json()
                expert = Expert(
                    name=data.get('name'),
                    summary=data.get('summary'),
                    status=data.get('status', True)
                )
                session.add(expert)
                session.commit()
                return {
                    'id': expert.id,
                    'name': expert.name,
                    'summary': expert.summary,
                    'status': expert.status,
                    'meta': expert.meta
                }, 201
            
            elif 'text/plain' in content_type or content_type == '':
                # Handle unstructured text input
                text = request.get_data(as_text=True)
                if not text.strip():
                    return {'message': 'Empty text provided'}, 400
                
                # Extract structured data using LLM
                try:
                    print(f"DEBUG - Starting LLM extraction for text length: {len(text)} characters")
                    extractor = LLMExtractor()
                    extracted_data = extractor.extract_expert_data(text)
                    print("DEBUG - LLM extraction successful")
                    print("DEBUG - Extracted data structure:", {
                        'expert_keys': list(extracted_data.get('expert', {}).keys()) if 'expert' in extracted_data else 'No expert key',
                        'experiences_count': len(extracted_data.get('experiences', [])) if 'experiences' in extracted_data else 'No experiences key',
                        'raw_data': extracted_data
                    })
                except Exception as llm_error:
                    print(f"ERROR - LLM extraction failed: {str(llm_error)}")
                    print(f"ERROR - LLM error type: {type(llm_error).__name__}")
                    import traceback
                    traceback.print_exc()
                    return {'message': f'LLM extraction failed: {str(llm_error)}'}, 400
                
                # Create expert
                try:
                    print("DEBUG - Creating expert record")
                    expert_data = extracted_data.get('expert', {})
                    expert_name = expert_data.get('name')
                    expert_summary = expert_data.get('summary')
                    
                    if not expert_name:
                        raise ValueError("Missing expert name in extracted data")
                    if not expert_summary:
                        raise ValueError("Missing expert summary in extracted data")
                    
                    print(f"DEBUG - Expert name: '{expert_name}', summary length: {len(expert_summary)}")
                    
                    expert = Expert(
                        name=expert_name,
                        summary=expert_summary,
                        status=True,
                        meta={'raw': text}
                    )
                    print("DEBUG - Expert object created successfully")
                except Exception as expert_error:
                    print(f"ERROR - Expert creation failed: {str(expert_error)}")
                    print(f"ERROR - Expert data available: {extracted_data.get('expert', 'No expert data')}")
                    return {'message': f'Expert creation failed: {str(expert_error)}'}, 400
                session.add(expert)
                session.flush()  # Get the expert ID without committing
                
                # Create experiences and attributes
                created_experiences = []
                
                experiences_data = extracted_data.get('experiences', [])
                print(f"DEBUG - Processing {len(experiences_data)} experiences")
                
                for i, exp_data in enumerate(experiences_data):
                    try:
                        print(f"DEBUG - Processing experience {i+1}/{len(experiences_data)}")
                        print(f"DEBUG - Experience data keys: {list(exp_data.keys()) if isinstance(exp_data, dict) else 'Not a dict'}")
                    except Exception as exp_debug_error:
                        print(f"ERROR - Failed to debug experience {i+1}: {str(exp_debug_error)}")
                        continue
                    # Handle "present" as current date
                    start_date_str = exp_data['start_date']
                    end_date_str = exp_data['end_date']
                    
                    start_date = datetime.fromisoformat(start_date_str).date()
                    
                    if end_date_str.lower() in ['present', 'current', 'ongoing', 'now']:
                        end_date = datetime.now().date()
                    else:
                        end_date = datetime.fromisoformat(end_date_str).date()
                    
                    experience = Experience(
                        expert_id=expert.id,
                        start_date=start_date,
                        end_date=end_date,
                        summary=exp_data['summary']
                    )
                    session.add(experience)
                    session.flush()  # Get the experience ID
                    
                    # Create attributes for this experience
                    created_attributes = []
                    
                    for attr_data in exp_data['attributes']:
                        # Only process attributes that have a valid ID (existing attributes found by LLM search)
                        attr_id = attr_data.get('id')
                        if attr_id is not None and str(attr_id).lower() not in ['none', 'null', '']:
                            # Use existing attribute by ID
                            existing_attr = session.query(Attribute).filter(Attribute.id == attr_id).first()
                            if existing_attr:
                                # Associate existing attribute with this experience
                                existing_attr.experiences.append(experience)
                                created_attributes.append({
                                    'id': existing_attr.id,
                                    'name': existing_attr.name,
                                    'type': existing_attr.type,
                                    'summary': existing_attr.summary,
                                    'existing': True
                                })
                                print(f"DEBUG - Using existing {existing_attr.type}: {existing_attr.name} (ID: {existing_attr.id})")
                            else:
                                print(f"WARNING - Attribute ID {attr_id} not found in database, skipping")
                        else:
                            print(f"DEBUG - Skipping attribute without ID: {attr_data.get('name', 'Unknown')} ({attr_data.get('type', 'Unknown type')})")
                    
                    created_experiences.append({
                        'start_date': experience.start_date.isoformat(),
                        'end_date': experience.end_date.isoformat(),
                        'summary': experience.summary,
                        'attributes': created_attributes
                    })
                
                session.commit()
                
                return {
                    'id': expert.id,
                    'name': expert.name,
                    'summary': expert.summary,
                    'status': expert.status,
                    'meta': expert.meta,
                    'experiences': created_experiences,
                    'extraction_source': 'llm'
                }, 201
            
            else:
                return {'message': 'Unsupported content type. Use application/json or text/plain'}, 400
            
        except Exception as e:
            session.rollback()
            return {'message': str(e)}, 400
        finally:
            session.close()