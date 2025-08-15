from flask import request
from flask_restful import Resource
from models import Expert, Experience, Attribute
from lib.llm_extractor import LLMExtractor
from lib.embedding_service import embedding_service
from database import get_db_session
from config import SEARCHABLE_ATTRIBUTE_TYPES, ATTRIBUTE_MATCHING_THRESHOLD
from datetime import datetime
from sqlalchemy import text

class ExpertResource(Resource):
    def get(self, expert_id):
        session = get_db_session()
        try:
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
                        'employer': exp.employer,
                        'position': exp.position,
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
        finally:
            session.close()

    def post(self):
        return self._create_expert()
                
    
    def _find_matching_database_attribute(self, session, extracted_term, attr_type, similarity_threshold=None):
        """Find best matching attribute from database using vector similarity"""
        if similarity_threshold is None:
            similarity_threshold = ATTRIBUTE_MATCHING_THRESHOLD
            
        # Generate embedding for extracted term
        term_embedding = embedding_service.generate_embedding(extracted_term.strip())
        
        # Find all attributes of this type in database with embeddings
        db_attributes = session.query(Attribute).filter(
            Attribute.type == attr_type,
            Attribute.embedding.isnot(None)
        ).all()
        
        best_match = None
        best_similarity = 0.0
        
        for db_attr in db_attributes:
            similarity = embedding_service.cosine_similarity(term_embedding, db_attr.embedding)
            if similarity >= similarity_threshold and similarity > best_similarity:
                best_match = db_attr
                best_similarity = similarity
        
        return (best_match, best_similarity) if best_match else (None, 0.0)
    
    def _create_expert(self):
        """Shared logic for creating experts from both structured and unstructured input"""
        session = get_db_session()
        try:
            content_type = request.headers.get('Content-Type', '')
            
            if 'application/json' in content_type:
                # Handle structured input
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
                # Handle unstructured text input with two-step extraction
                text = request.get_data(as_text=True)
                if not text.strip():
                    return {'message': 'Empty text provided'}, 400
                
                # Extract structured data using two-step process
                extractor = LLMExtractor()
                extracted_data = extractor.extract_expert_with_attributes(text)
                
                # Create expert
                expert_data = extracted_data.get('expert', {})
                expert = Expert(
                    name=expert_data.get('name'),
                    summary=expert_data.get('summary'),
                    status=True,
                    meta={'source': 'llm_extraction', 'original_text': text}
                )
                session.add(expert)
                session.flush()
                
                # Create experiences with attributes from two-step extraction
                created_experiences = []
                experiences_data = extracted_data.get('experiences', [])
                
                for exp_data in experiences_data:
                    # Parse dates
                    start_date = datetime.fromisoformat(exp_data['start_date']).date()
                    end_date_str = exp_data['end_date']
                    if end_date_str.lower() in ['present', 'current', 'ongoing', 'now']:
                        end_date = datetime.now().date()
                    else:
                        end_date = datetime.fromisoformat(end_date_str).date()
                    
                    # Create experience with structured data
                    employer = exp_data.get('employer', '')
                    position = exp_data.get('position', '')
                    # Use 'summary' from the data, or 'activities' for backwards compatibility
                    summary = exp_data.get('summary', exp_data.get('activities', ''))
                    
                    # If summary is not provided, create from structured fields
                    if not summary and (position or employer):
                        summary = f"{position} at {employer}"
                    
                    experience = Experience(
                        expert_id=expert.id,
                        employer=employer,
                        position=position,
                        start_date=start_date,
                        end_date=end_date,
                        summary=summary
                    )
                    session.add(experience)
                    session.flush()
                    
                    # Process attribute IDs from LLM analysis
                    matched_attributes = []
                    attribute_ids = exp_data.get('attribute_ids', [])
                    
                    for attr_id in attribute_ids:
                        # Get attribute from database by ID
                        attribute = session.query(Attribute).filter(Attribute.id == attr_id).first()
                        
                        if attribute:
                            # Associate existing database attribute with this experience
                            if experience not in attribute.experiences:
                                attribute.experiences.append(experience)
                            
                            matched_attributes.append({
                                'id': attribute.id,
                                'name': attribute.name,
                                'type': attribute.type,
                                'summary': attribute.summary
                            })
                        else:
                            print(f"Warning: Attribute ID {attr_id} not found in database")
                    
                    created_experiences.append({
                        'employer': exp_data.get('employer', ''),
                        'position': exp_data.get('position', ''),
                        'start_date': experience.start_date.isoformat(),
                        'end_date': experience.end_date.isoformat(),
                        'summary': experience.summary,
                        'attributes': matched_attributes,
                        'analysis_notes': exp_data.get('analysis_notes', '')
                    })
                
                session.commit()
                
                return {
                    'id': expert.id,
                    'name': expert.name,
                    'summary': expert.summary,
                    'status': expert.status,
                    'meta': expert.meta,
                    'experiences': created_experiences,
                    'extraction_source': 'two_step_extraction_with_attribute_analysis'
                }, 201
            
            else:
                return {'message': 'Unsupported content type. Use application/json or text/plain'}, 400
                
        except Exception as e:
            session.rollback()
            return {'message': f'Expert creation failed: {str(e)}'}, 400
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
            # Get pagination and search parameters with error handling
            try:
                page = max(1, int(request.args.get('page', 1)))
                page_size = max(1, min(int(request.args.get('page_size', 20)), 100))  # Max 100 per page
            except ValueError:
                page = 1
                page_size = 20
            
            search_name = request.args.get('search', '').strip()
            include_experiences = request.args.get('include_experiences', 'false').lower() == 'true'
            
            # Calculate offset
            offset = (page - 1) * page_size
            
            # Build base query with optional name filtering
            base_query = session.query(Expert)
            if search_name:
                # Case-insensitive partial name search
                base_query = base_query.filter(Expert.name.ilike(f'%{search_name}%'))
            
            # Get total count with filters applied
            total_count = base_query.count()
            
            # Get paginated experts
            experts = base_query.offset(offset).limit(page_size).all()
            
            # Build response
            expert_data = []
            for expert in experts:
                expert_info = {
                    'id': expert.id,
                    'name': expert.name,
                    'summary': expert.summary,
                    'status': expert.status,
                    'meta': expert.meta
                }
                
                if include_experiences:
                    # Include full experience data with attributes
                    expert_info['experiences'] = [
                        {
                            'id': exp.id,
                            'employer': exp.employer,
                            'position': exp.position,
                            'start_date': exp.start_date.isoformat(),
                            'end_date': exp.end_date.isoformat(),
                            'summary': exp.summary,
                            'attributes': [
                                {
                                    'id': attr.id,
                                    'name': attr.name,
                                    'type': attr.type,
                                    'summary': attr.summary,
                                    'depth': attr.depth,
                                    'parent_id': attr.parent_id
                                } for attr in exp.attributes
                            ]
                        } for exp in expert.experiences
                    ]
                else:
                    # Calculate stats efficiently using separate queries
                    total_experiences = session.query(Experience).filter(Experience.expert_id == expert.id).count()
                    total_attributes = session.execute(text("""
                        SELECT COUNT(a.id) 
                        FROM attribute a 
                        JOIN experience_attribute ea ON a.id = ea.attribute_id 
                        JOIN experience e ON ea.experience_id = e.id 
                        WHERE e.expert_id = :expert_id
                    """), {'expert_id': expert.id}).scalar() or 0
                    
                    unique_types = session.execute(text("""
                        SELECT COUNT(DISTINCT a.type) 
                        FROM attribute a 
                        JOIN experience_attribute ea ON a.id = ea.attribute_id 
                        JOIN experience e ON ea.experience_id = e.id 
                        WHERE e.expert_id = :expert_id
                    """), {'expert_id': expert.id}).scalar() or 0
                    
                    expert_info['stats'] = {
                        'total_experiences': total_experiences,
                        'total_attributes': total_attributes,
                        'unique_attribute_types': unique_types
                    }
                
                expert_data.append(expert_info)
            
            # Calculate pagination info
            total_pages = (total_count + page_size - 1) // page_size
            
            return {
                'experts': expert_data,
                'pagination': {
                    'page': page,
                    'page_size': page_size,
                    'total_count': total_count,
                    'total_pages': total_pages,
                    'has_next': page < total_pages,
                    'has_prev': page > 1
                },
                'search': {
                    'query': search_name,
                    'is_filtered': bool(search_name)
                },
                'include_experiences': include_experiences
            }
        finally:
            session.close()

    def post(self):
        # Delegate to the same implementation as ExpertResource
        expert_resource = ExpertResource()
        return expert_resource._create_expert()