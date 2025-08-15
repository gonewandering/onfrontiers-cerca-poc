from flask import request
from flask_restful import Resource
from models import Attribute, Experience
from database import get_db_session
from lib.embedding_service import embedding_service
from sqlalchemy import text
from typing import List, Tuple


class AttributeResource(Resource):
    def get(self, attribute_id=None):
        session = get_db_session()
        try:
            if attribute_id:
                attribute = session.query(Attribute).filter(Attribute.id == attribute_id).first()
                if not attribute:
                    return {'message': 'Attribute not found'}, 404
                return {
                    'id': attribute.id,
                    'name': attribute.name,
                    'type': attribute.type,
                    'summary': attribute.summary,
                    'depth': attribute.depth,
                    'parent_id': attribute.parent_id,
                    'embedding': attribute.embedding,
                    'experiences': [exp.id for exp in attribute.experiences]
                }
            else:
                attributes = session.query(Attribute).all()
                return {
                    'attributes': [
                        {
                            'id': attr.id,
                            'name': attr.name,
                            'type': attr.type,
                            'summary': attr.summary,
                            'embedding': attr.embedding,
                            'experiences': [exp.id for exp in attr.experiences]
                        } for attr in attributes
                    ]
                }
        finally:
            session.close()

    def post(self):
        session = get_db_session()
        try:
            data = request.get_json()
            
            attribute = Attribute(
                name=data.get('name'),
                type=data.get('type'),
                summary=data.get('summary')
            )
            
            # Handle experience associations if provided
            experience_ids = data.get('experience_ids', [])
            if experience_ids:
                experiences = session.query(Experience).filter(Experience.id.in_(experience_ids)).all()
                attribute.experiences = experiences
            
            session.add(attribute)
            session.commit()
            return {
                'id': attribute.id,
                'name': attribute.name,
                'type': attribute.type,
                'summary': attribute.summary,
                'embedding': attribute.embedding,
                'experiences': [exp.id for exp in attribute.experiences]
            }, 201
        except Exception as e:
            session.rollback()
            return {'message': str(e)}, 400
        finally:
            session.close()

    def put(self, attribute_id):
        session = get_db_session()
        try:
            attribute = session.query(Attribute).filter(Attribute.id == attribute_id).first()
            if not attribute:
                return {'message': 'Attribute not found'}, 404
            
            data = request.get_json()
            attribute.name = data.get('name', attribute.name)
            attribute.type = data.get('type', attribute.type)
            attribute.summary = data.get('summary', attribute.summary)
            
            # Handle experience associations if provided
            if 'experience_ids' in data:
                experience_ids = data.get('experience_ids', [])
                experiences = session.query(Experience).filter(Experience.id.in_(experience_ids)).all()
                attribute.experiences = experiences
            
            session.commit()
            return {
                'id': attribute.id,
                'name': attribute.name,
                'type': attribute.type,
                'summary': attribute.summary,
                'embedding': attribute.embedding,
                'experiences': [exp.id for exp in attribute.experiences]
            }
        except Exception as e:
            session.rollback()
            return {'message': str(e)}, 400
        finally:
            session.close()

    def delete(self, attribute_id):
        session = get_db_session()
        try:
            attribute = session.query(Attribute).filter(Attribute.id == attribute_id).first()
            if not attribute:
                return {'message': 'Attribute not found'}, 404
            
            session.delete(attribute)
            session.commit()
            return {'message': 'Attribute deleted successfully'}
        except Exception as e:
            session.rollback()
            return {'message': str(e)}, 400
        finally:
            session.close()


class AttributeListResource(Resource):
    def get(self):
        session = get_db_session()
        try:
            # Check for search query parameter
            search_query = request.args.get('q')
            attribute_type = request.args.get('type')
            limit = request.args.get('limit', 50, type=int)
            
            if search_query:
                # Generate embedding for the search query
                try:
                    import time
                    start_time = time.time()
                    query_embedding = embedding_service.generate_embedding(search_query)
                    embedding_time = time.time() - start_time
                    print(f"🔍 Embedding generation took: {embedding_time:.3f}s")
                except Exception as e:
                    return {'message': f'Failed to generate embedding: {str(e)}'}, 400
                
                # Use pgvector cosine similarity directly in SQL with depth penalty
                # This is much more efficient than loading all records into Python
                
                # Build base query with type filter if provided
                type_filter = "AND type = :type_filter" if attribute_type else ""
                
                # SQL query using pgvector cosine similarity with depth penalty
                similarity_query = text(f"""
                    SELECT 
                        id, name, type, summary, depth, parent_id,
                        (1 - (embedding <=> CAST(:query_embedding AS vector))) as similarity_score,
                        (1 - (embedding <=> CAST(:query_embedding AS vector))) - (0.01 * COALESCE(depth, 0)) as adjusted_score
                    FROM attribute 
                    WHERE embedding IS NOT NULL {type_filter}
                    ORDER BY adjusted_score DESC 
                    LIMIT :limit
                """)
                
                params = {
                    'query_embedding': query_embedding,
                    'limit': limit
                }
                if attribute_type:
                    params['type_filter'] = attribute_type
                
                result = session.execute(similarity_query, params)
                rows = result.fetchall()
                
                # Skip count query for performance - use number of results found
                total_count = len(rows)
                
                return {
                    'query': search_query,
                    'type_filter': attribute_type,
                    'total_found': total_count,
                    'attributes': [
                        {
                            'id': row.id,
                            'name': row.name,
                            'type': row.type,
                            'summary': row.summary,
                            'depth': row.depth or 0,
                            'parent_id': row.parent_id,
                            'similarity_score': float(row.similarity_score),
                            'adjusted_score': float(row.adjusted_score),
                            'depth_penalty': float(0.01 * (row.depth or 0))
                        } for row in rows
                    ]
                }
            else:
                # Regular listing without search
                query = session.query(Attribute)
                if attribute_type:
                    query = query.filter(Attribute.type == attribute_type)
                
                # Get total count with same filters
                total_count = query.count()
                
                attributes = query.limit(limit).all()
                return {
                    'total_count': total_count,
                    'limit': limit,
                    'type_filter': attribute_type,
                    'attributes': [
                        {
                            'id': attr.id,
                            'name': attr.name,
                            'type': attr.type,
                            'summary': attr.summary,
                            'depth': attr.depth,
                            'parent_id': attr.parent_id,
                            'experiences': [exp.id for exp in attr.experiences]
                        } for attr in attributes
                    ]
                }
        finally:
            session.close()

    def post(self):
        session = get_db_session()
        try:
            data = request.get_json()
            
            attribute = Attribute(
                name=data.get('name'),
                type=data.get('type'),
                summary=data.get('summary')
            )
            
            # Handle experience associations if provided
            experience_ids = data.get('experience_ids', [])
            if experience_ids:
                experiences = session.query(Experience).filter(Experience.id.in_(experience_ids)).all()
                attribute.experiences = experiences
            
            session.add(attribute)
            session.commit()
            return {
                'id': attribute.id,
                'name': attribute.name,
                'type': attribute.type,
                'summary': attribute.summary,
                'embedding': attribute.embedding,
                'experiences': [exp.id for exp in attribute.experiences]
            }, 201
        except Exception as e:
            session.rollback()
            return {'message': str(e)}, 400
        finally:
            session.close()