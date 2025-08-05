from flask import request
from flask_restful import Resource
from models import Experience, Expert
from database import get_db_session
from datetime import datetime

class ExperienceResource(Resource):
    def get(self, experience_id=None):
        session = get_db_session()
        try:
            if experience_id:
                experience = session.query(Experience).filter(Experience.id == experience_id).first()
                if not experience:
                    return {'message': 'Experience not found'}, 404
                return {
                    'id': experience.id,
                    'expert_id': experience.expert_id,
                    'start_date': experience.start_date.isoformat(),
                    'end_date': experience.end_date.isoformat(),
                    'summary': experience.summary,
                    'attributes': [
                        {
                            'id': attr.id,
                            'name': attr.name,
                            'type': attr.type,
                            'summary': attr.summary
                        } for attr in experience.attributes
                    ]
                }
            else:
                experiences = session.query(Experience).all()
                return {
                    'experiences': [
                        {
                            'id': exp.id,
                            'expert_id': exp.expert_id,
                            'start_date': exp.start_date.isoformat(),
                            'end_date': exp.end_date.isoformat(),
                            'summary': exp.summary
                        } for exp in experiences
                    ]
                }
        finally:
            session.close()

    def post(self):
        session = get_db_session()
        try:
            data = request.get_json()
            
            expert = session.query(Expert).filter(Expert.id == data.get('expert_id')).first()
            if not expert:
                return {'message': 'Expert not found'}, 404
            
            experience = Experience(
                expert_id=data.get('expert_id'),
                start_date=datetime.fromisoformat(data.get('start_date')).date(),
                end_date=datetime.fromisoformat(data.get('end_date')).date(),
                summary=data.get('summary')
            )
            session.add(experience)
            session.commit()
            return {
                'id': experience.id,
                'expert_id': experience.expert_id,
                'start_date': experience.start_date.isoformat(),
                'end_date': experience.end_date.isoformat(),
                'summary': experience.summary
            }, 201
        except Exception as e:
            session.rollback()
            return {'message': str(e)}, 400
        finally:
            session.close()

    def put(self, experience_id):
        session = get_db_session()
        try:
            experience = session.query(Experience).filter(Experience.id == experience_id).first()
            if not experience:
                return {'message': 'Experience not found'}, 404
            
            data = request.get_json()
            if data.get('start_date'):
                experience.start_date = datetime.fromisoformat(data.get('start_date')).date()
            if data.get('end_date'):
                experience.end_date = datetime.fromisoformat(data.get('end_date')).date()
            experience.summary = data.get('summary', experience.summary)
            
            session.commit()
            return {
                'id': experience.id,
                'expert_id': experience.expert_id,
                'start_date': experience.start_date.isoformat(),
                'end_date': experience.end_date.isoformat(),
                'summary': experience.summary
            }
        except Exception as e:
            session.rollback()
            return {'message': str(e)}, 400
        finally:
            session.close()

    def delete(self, experience_id):
        session = get_db_session()
        try:
            experience = session.query(Experience).filter(Experience.id == experience_id).first()
            if not experience:
                return {'message': 'Experience not found'}, 404
            
            session.delete(experience)
            session.commit()
            return {'message': 'Experience deleted successfully'}
        except Exception as e:
            session.rollback()
            return {'message': str(e)}, 400
        finally:
            session.close()

class ExperienceListResource(Resource):
    def get(self):
        session = get_db_session()
        try:
            experiences = session.query(Experience).all()
            return {
                'experiences': [
                    {
                        'id': exp.id,
                        'expert_id': exp.expert_id,
                        'start_date': exp.start_date.isoformat(),
                        'end_date': exp.end_date.isoformat(),
                        'summary': exp.summary
                    } for exp in experiences
                ]
            }
        finally:
            session.close()

    def post(self):
        session = get_db_session()
        try:
            data = request.get_json()
            
            expert = session.query(Expert).filter(Expert.id == data.get('expert_id')).first()
            if not expert:
                return {'message': 'Expert not found'}, 404
            
            experience = Experience(
                expert_id=data.get('expert_id'),
                start_date=datetime.fromisoformat(data.get('start_date')).date(),
                end_date=datetime.fromisoformat(data.get('end_date')).date(),
                summary=data.get('summary')
            )
            session.add(experience)
            session.commit()
            return {
                'id': experience.id,
                'expert_id': experience.expert_id,
                'start_date': experience.start_date.isoformat(),
                'end_date': experience.end_date.isoformat(),
                'summary': experience.summary
            }, 201
        except Exception as e:
            session.rollback()
            return {'message': str(e)}, 400
        finally:
            session.close()