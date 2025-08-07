from flask import request
from flask_restful import Resource
from models import Expert, Experience, Attribute
from lib.llm_extractor import LLMExtractor
from lib.embedding_service import embedding_service
from database import get_db_session
from config import SEARCHABLE_ATTRIBUTE_TYPES, ATTRIBUTE_MATCHING_THRESHOLD
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
                # Handle unstructured text input with predefined attribute matching
                text = request.get_data(as_text=True)
                if not text.strip():
                    return {'message': 'Empty text provided'}, 400
                
                # Extract structured data using LLM
                extractor = LLMExtractor()
                extracted_data = extractor.extract_expert_data_fast(text)
                
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
                
                # Create experiences with predefined attribute matching
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
                    
                    # Create experience
                    experience = Experience(
                        expert_id=expert.id,
                        start_date=start_date,
                        end_date=end_date,
                        summary=exp_data['summary']
                    )
                    session.add(experience)
                    session.flush()
                    
                    # Process attributes with database-based matching
                    matched_attributes = []
                    for attr_data in exp_data.get('attributes', []):
                        attr_name = attr_data.get('name', '').strip()
                        attr_type = attr_data.get('type', '').strip()
                        
                        if not attr_name or attr_type not in SEARCHABLE_ATTRIBUTE_TYPES:
                            continue
                        
                        # Find best matching attribute in database
                        matched_attr, similarity_score = self._find_matching_database_attribute(
                            session, attr_name, attr_type
                        )
                        
                        if matched_attr:
                            # Associate existing database attribute with this experience
                            if experience not in matched_attr.experiences:
                                matched_attr.experiences.append(experience)
                            
                            matched_attributes.append({
                                'id': matched_attr.id,
                                'name': matched_attr.name,
                                'type': matched_attr.type,
                                'summary': matched_attr.summary,
                                'matched_from': attr_name,
                                'similarity_score': round(similarity_score, 3)
                            })
                    
                    created_experiences.append({
                        'start_date': experience.start_date.isoformat(),
                        'end_date': experience.end_date.isoformat(),
                        'summary': experience.summary,
                        'attributes': matched_attributes
                    })
                
                session.commit()
                
                return {
                    'id': expert.id,
                    'name': expert.name,
                    'summary': expert.summary,
                    'status': expert.status,
                    'meta': expert.meta,
                    'experiences': created_experiences,
                    'extraction_source': 'llm_with_database_matching'
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
        # Delegate to the same implementation as ExpertResource
        expert_resource = ExpertResource()
        return expert_resource._create_expert()