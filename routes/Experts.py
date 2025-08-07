from flask import request
from flask_restful import Resource
from models import Expert, Experience, Attribute
from lib.llm_extractor import LLMExtractor
from lib.embedding_service import embedding_service
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
                
                # Extract structured data using fast LLM (no function calling)
                try:
                    print(f"DEBUG - Starting FAST LLM extraction for text length: {len(text)} characters")
                    extractor = LLMExtractor()
                    extracted_data = extractor.extract_expert_data_fast(text)
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
                    
                    print(f"DEBUG - Processing {len(exp_data.get('attributes', []))} attributes for this experience")
                    for i, attr_data in enumerate(exp_data.get('attributes', [])):
                        print(f"DEBUG - Attribute {i+1}: {attr_data}")
                        
                        attr_name = attr_data.get('name', '').strip()
                        attr_type = attr_data.get('type', '').strip()
                        attr_summary = attr_data.get('summary', '')
                        
                        if not attr_name or not attr_type:
                            print(f"DEBUG - Skipping attribute with missing name or type")
                            continue
                            
                        # Check if attribute already exists (exact name and type match)
                        existing_attr = session.query(Attribute).filter(
                            Attribute.name.ilike(attr_name),
                            Attribute.type == attr_type
                        ).first()
                        
                        if existing_attr:
                            print(f"DEBUG - Found existing {attr_type}: {attr_name} (ID: {existing_attr.id})")
                            # Associate existing attribute with this experience
                            existing_attr.experiences.append(experience)
                            created_attributes.append({
                                'id': existing_attr.id,
                                'name': existing_attr.name,
                                'type': existing_attr.type,
                                'summary': existing_attr.summary,
                                'existing': True
                            })
                        else:
                            print(f"DEBUG - Creating new {attr_type}: {attr_name}")
                            # Generate embedding for new attribute
                            try:
                                embedding = embedding_service.generate_attribute_embedding(
                                    attr_name, attr_type, attr_summary or f"{attr_type.title()}: {attr_name}"
                                )
                                print(f"DEBUG - Generated embedding for {attr_name} ({len(embedding)} dimensions)")
                            except Exception as e:
                                print(f"WARNING - Failed to generate embedding for {attr_name}: {str(e)}")
                                embedding = None
                            
                            # Create new attribute
                            new_attr = Attribute(
                                name=attr_name,
                                type=attr_type,  
                                summary=attr_summary or f"{attr_type.title()}: {attr_name}",
                                embedding=embedding
                            )
                            session.add(new_attr)
                            session.flush()  # Get the ID
                            
                            # Associate new attribute with this experience
                            new_attr.experiences.append(experience)
                            created_attributes.append({
                                'id': new_attr.id,
                                'name': new_attr.name,
                                'type': new_attr.type,
                                'summary': new_attr.summary,
                                'existing': False
                            })
                            print(f"DEBUG - Created and associated new {attr_type}: {attr_name} (ID: {new_attr.id}) with embedding")
                            
                    print(f"DEBUG - Created {len(created_attributes)} attribute associations for this experience")
                    
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
                
                # Extract structured data using fast LLM (no function calling)
                try:
                    print(f"DEBUG - Starting FAST LLM extraction for text length: {len(text)} characters")
                    extractor = LLMExtractor()
                    extracted_data = extractor.extract_expert_data_fast(text)
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
                    
                    print(f"DEBUG - Processing {len(exp_data.get('attributes', []))} attributes for this experience")
                    for i, attr_data in enumerate(exp_data.get('attributes', [])):
                        print(f"DEBUG - Attribute {i+1}: {attr_data}")
                        
                        attr_name = attr_data.get('name', '').strip()
                        attr_type = attr_data.get('type', '').strip()
                        attr_summary = attr_data.get('summary', '')
                        
                        if not attr_name or not attr_type:
                            print(f"DEBUG - Skipping attribute with missing name or type")
                            continue
                            
                        # Check if attribute already exists (exact name and type match)
                        existing_attr = session.query(Attribute).filter(
                            Attribute.name.ilike(attr_name),
                            Attribute.type == attr_type
                        ).first()
                        
                        if existing_attr:
                            print(f"DEBUG - Found existing {attr_type}: {attr_name} (ID: {existing_attr.id})")
                            # Associate existing attribute with this experience
                            existing_attr.experiences.append(experience)
                            created_attributes.append({
                                'id': existing_attr.id,
                                'name': existing_attr.name,
                                'type': existing_attr.type,
                                'summary': existing_attr.summary,
                                'existing': True
                            })
                        else:
                            print(f"DEBUG - Creating new {attr_type}: {attr_name}")
                            # Generate embedding for new attribute
                            try:
                                embedding = embedding_service.generate_attribute_embedding(
                                    attr_name, attr_type, attr_summary or f"{attr_type.title()}: {attr_name}"
                                )
                                print(f"DEBUG - Generated embedding for {attr_name} ({len(embedding)} dimensions)")
                            except Exception as e:
                                print(f"WARNING - Failed to generate embedding for {attr_name}: {str(e)}")
                                embedding = None
                            
                            # Create new attribute
                            new_attr = Attribute(
                                name=attr_name,
                                type=attr_type,  
                                summary=attr_summary or f"{attr_type.title()}: {attr_name}",
                                embedding=embedding
                            )
                            session.add(new_attr)
                            session.flush()  # Get the ID
                            
                            # Associate new attribute with this experience
                            new_attr.experiences.append(experience)
                            created_attributes.append({
                                'id': new_attr.id,
                                'name': new_attr.name,
                                'type': new_attr.type,
                                'summary': new_attr.summary,
                                'existing': False
                            })
                            print(f"DEBUG - Created and associated new {attr_type}: {attr_name} (ID: {new_attr.id}) with embedding")
                            
                    print(f"DEBUG - Created {len(created_attributes)} attribute associations for this experience")
                    
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