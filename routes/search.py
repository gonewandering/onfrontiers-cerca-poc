from flask import request
from flask_restful import Resource
from models import Expert, Experience, Attribute, experience_attribute_association
from lib.llm_extractor import LLMExtractor
from database import get_db_session
from config import SEARCHABLE_ATTRIBUTE_TYPES, SEARCH_CONFIG, ATTRIBUTE_WEIGHTS
from datetime import datetime, date
from sqlalchemy import func, and_, text
from sqlalchemy.orm import joinedload
import time
from typing import Dict, List, Any

class ExpertSearchResource(Resource):
    def post(self):
        """
        Search for experts based on unstructured text input using LLM attribute extraction
        and knowledge-based scoring algorithm.
        """
        start_time = time.time()
        session = get_db_session()
        
        try:
            # Get input text
            content_type = request.headers.get('Content-Type', '')
            
            if 'application/json' in content_type:
                data = request.get_json()
                search_text = data.get('text', '')
                page_size = min(data.get('page_size', SEARCH_CONFIG['default_page_size']), 
                              SEARCH_CONFIG['max_page_size'])
                page = data.get('page', 1)
                
                # Parse search configuration overrides
                search_settings = data.get('settings', {})
                
            elif 'text/plain' in content_type:
                search_text = request.get_data(as_text=True)
                page_size = SEARCH_CONFIG['default_page_size']
                page = 1
                search_settings = {}  # No settings override for plain text
                
            else:
                return {'message': 'Content-Type must be application/json or text/plain'}, 400
            
            if not search_text.strip():
                return {'message': 'Search text cannot be empty'}, 400
            
            # Merge default config with user-provided settings
            def merge_config(default_config, overrides):
                """Merge default configuration with user overrides, validating types and ranges"""
                merged = default_config.copy()
                
                # Define valid overridable settings with validation
                valid_settings = {
                    'similarity_threshold': {'type': float, 'min': 0.0, 'max': 1.0},
                    'max_similar_attributes': {'type': int, 'min': 1, 'max': 100},
                    'max_attributes_per_type': {'type': int, 'min': 1, 'max': 10},
                    'scoring_base': {'type': float, 'min': 1.0, 'max': 2.0},
                    'recency_decay_factor': {'type': float, 'min': 0.0, 'max': 1.0},
                    'similarity_weight': {'type': float, 'min': 0.0, 'max': 2.0}
                }
                
                for key, value in overrides.items():
                    if key == 'attribute_weights':
                        # Special handling for attribute weights
                        merged[key] = validate_attribute_weights(value, default_config.get('attribute_weights', ATTRIBUTE_WEIGHTS))
                        print(f"DEBUG - Override attribute_weights: {merged[key]}")
                    elif key in valid_settings:
                        spec = valid_settings[key]
                        # Type validation
                        if not isinstance(value, spec['type']):
                            try:
                                value = spec['type'](value)
                            except (ValueError, TypeError):
                                continue  # Skip invalid values
                        
                        # Range validation
                        if 'min' in spec and value < spec['min']:
                            value = spec['min']
                        if 'max' in spec and value > spec['max']:
                            value = spec['max']
                        
                        merged[key] = value
                        print(f"DEBUG - Override setting: {key} = {value}")
                
                return merged
            
            def validate_attribute_weights(user_weights, default_weights):
                """Validate and merge user-provided attribute weights with defaults"""
                if not isinstance(user_weights, list):
                    return default_weights
                
                # Create a weight lookup from defaults
                weight_dict = {item['name']: item['weight'] for item in default_weights}
                
                # Process user overrides
                for weight_item in user_weights:
                    if isinstance(weight_item, dict) and 'name' in weight_item and 'weight' in weight_item:
                        attr_name = weight_item['name']
                        if attr_name in SEARCHABLE_ATTRIBUTE_TYPES:
                            try:
                                weight_value = float(weight_item['weight'])
                                # Clamp weight to reasonable range (now allowing 0 for geometric weights)
                                weight_value = max(0.0, min(10.0, weight_value))
                                weight_dict[attr_name] = weight_value
                            except (ValueError, TypeError):
                                continue  # Skip invalid weights
                
                # Convert back to list format
                return [{'name': name, 'weight': weight} for name, weight in weight_dict.items()]
            
            # Apply setting overrides
            effective_config = merge_config(SEARCH_CONFIG, search_settings)
            print(f"DEBUG - Effective weights being used: {effective_config.get('attribute_weights', ATTRIBUTE_WEIGHTS)}")
            
            # Create a helper function to get attribute weights
            def get_attribute_weight(attr_type):
                """Get the weight for a given attribute type"""
                weights = effective_config.get('attribute_weights', ATTRIBUTE_WEIGHTS)
                for weight_item in weights:
                    if weight_item['name'] == attr_type:
                        return weight_item['weight']
                return 1.0  # Default weight if not found
            
            # STEP 1: Extract 1-2 attributes from each type using LLM
            try:
                llm_start = time.time()
                print(f"DEBUG - Extracting attributes from search query: '{search_text[:100]}...'")
                
                extractor = LLMExtractor()
                llm_extracted = extractor.extract_from_template("expert_search_fast", {
                    "text": search_text,
                    "attribute_types": ', '.join(SEARCHABLE_ATTRIBUTE_TYPES)
                })
                
                llm_time = time.time() - llm_start
                print(f"DEBUG - LLM attribute extraction completed in {llm_time:.2f}s")
                print(f"DEBUG - Raw LLM output: {llm_extracted}")
                
                # STEP 2: Batch generate embeddings and find similar DB attributes
                from lib.embedding_service import embedding_service
                
                search_attributes = {}  # Final attributes to search for, with similarity scores
                extracted_attributes = {}  # For UI display
                similarity_threshold = effective_config.get('similarity_threshold', 0.4)
                
                # Collect all terms for batch embedding generation
                all_terms = []
                term_to_type = {}
                
                for attr_type in SEARCHABLE_ATTRIBUTE_TYPES:
                    attr_key = f"{attr_type}_terms"
                    if attr_key in llm_extracted and llm_extracted[attr_key]:
                        search_attributes[attr_type] = []
                        extracted_attributes[attr_type] = []
                        
                        terms = llm_extracted[attr_key][:1] if llm_extracted[attr_key] else []
                        for term in terms:
                            if term.strip():
                                all_terms.append(term.strip())
                                term_to_type[term.strip()] = attr_type
                    
                    # Always ensure extracted_attributes has an entry for each type that was extracted
                    if attr_key in llm_extracted and llm_extracted[attr_key] and attr_type not in extracted_attributes:
                        extracted_attributes[attr_type] = []
                
                # Even if no terms are extracted, show what the LLM extracted
                if not all_terms:
                    # Add all extracted terms as no_match entries
                    for attr_type in SEARCHABLE_ATTRIBUTE_TYPES:
                        attr_key = f"{attr_type}_terms"
                        if attr_key in llm_extracted and llm_extracted[attr_key]:
                            if attr_type not in extracted_attributes:
                                extracted_attributes[attr_type] = []
                            for term in llm_extracted[attr_key]:
                                if term.strip():
                                    extracted_attributes[attr_type].append({
                                        'id': None,
                                        'name': term,
                                        'type': attr_type,
                                        'relevance_score': 0.0,
                                        'source': 'no_match'
                                    })
                
                # Batch generate embeddings for all terms at once
                if all_terms:
                    try:
                        # Generate all embeddings in a single API call
                        embeddings = embedding_service.generate_batch_embeddings(all_terms)
                        
                        # Process each term with its embedding
                        for term, term_embedding in zip(all_terms, embeddings):
                            attr_type = term_to_type[term]
                            
                            # Convert embedding to pgvector format
                            embedding_str = '[' + ','.join(map(str, term_embedding)) + ']'
                            
                            # Single optimized query that returns all needed data (no similarity threshold)
                            similarity_query = text(f"""
                                SELECT id, name, type, summary, 
                                       (1 - (embedding <=> '{embedding_str}'::vector)) AS similarity
                                FROM attribute 
                                WHERE type = :attr_type 
                                  AND embedding IS NOT NULL
                                ORDER BY embedding <=> '{embedding_str}'::vector
                                LIMIT 1
                            """)
                            
                            result = session.execute(similarity_query, {
                                'attr_type': attr_type
                            }).fetchone()
                            
                            if result:
                                search_attributes[attr_type].append({
                                    'id': result.id,
                                    'name': result.name,
                                    'similarity': result.similarity,
                                    'extracted_term': term
                                })
                                extracted_attributes[attr_type].append({
                                    'id': result.id,
                                    'name': f"{term} → {result.name}",
                                    'type': attr_type,
                                    'relevance_score': result.similarity,
                                    'source': 'matched'
                                })
                            else:
                                extracted_attributes[attr_type].append({
                                    'id': None,
                                    'name': term,
                                    'type': attr_type,
                                    'relevance_score': 0.0,
                                    'source': 'no_match'
                                })
                    except Exception as embedding_error:
                        print(f"ERROR - Batch embedding generation failed: {str(embedding_error)}")
                        return {'message': f'Failed to generate embeddings: {str(embedding_error)}'}, 500
                
                # Get all attribute IDs for scoring
                all_attribute_ids = []
                for attr_type_data in search_attributes.values():
                    for attr_data in attr_type_data:
                        all_attribute_ids.append(attr_data['id'])
                
                extracted_data = {
                    'extracted_attributes': extracted_attributes,
                    'search_summary': f'Extracted {sum(len(v) for v in search_attributes.values())} searchable attributes',
                    'search_attributes': search_attributes  # For scoring
                }
                
            except Exception as llm_error:
                print(f"ERROR - LLM extraction failed: {str(llm_error)}")
                import traceback
                traceback.print_exc()
                return {'message': f'Failed to extract attributes: {str(llm_error)}'}, 500
            
            # STEP 3: Score each experience that has matching attributes
            if not all_attribute_ids:
                # No matching attributes found, but still return extracted data
                return {
                    'experts': [],
                    'search_metadata': {
                        'extracted_attributes': extracted_attributes,
                        'search_summary': f'Extracted {sum(len(v) for v in extracted_attributes.values())} attributes but no database matches found',
                        'total_experts': 0,
                        'search_time_ms': round((time.time() - start_time) * 1000, 2),
                        'message': 'No matching attributes found in database'
                    }
                }, 200
            
            print(f"DEBUG - Found {len(all_attribute_ids)} matching attribute IDs: {all_attribute_ids}")
            
            query_start = time.time()
            recency_factor = effective_config['recency_decay_factor']
            
            # Build attribute similarity lookup
            attr_similarity = {}
            for attr_type, attrs in search_attributes.items():
                for attr in attrs:
                    weight = get_attribute_weight(attr_type)
                    print(f"DEBUG - Attribute {attr['id']} ({attr_type}): weight={weight}, similarity={attr['similarity']}")
                    attr_similarity[attr['id']] = {
                        'similarity': attr['similarity'],
                        'weight': weight
                    }
            
            # Simple scoring query: years * recency * similarity * weight for each experience
            scoring_query = text("""
                SELECT 
                    e.expert_id,
                    e.id as experience_id,
                    e.start_date,
                    e.end_date,
                    e.summary,
                    e.position,
                    e.employer,
                    (e.end_date - e.start_date) / 365.0 as duration_years,
                    GREATEST(0.1, 1 - :recency_factor * (CURRENT_DATE - e.end_date) / 365.0) as recency_multiplier,
                    ea.attribute_id
                FROM experience e
                JOIN experience_attribute ea ON e.id = ea.experience_id  
                WHERE ea.attribute_id = ANY(:attribute_ids)
                ORDER BY e.expert_id, e.id
            """)
            
            results = session.execute(scoring_query, {
                'attribute_ids': all_attribute_ids,
                'recency_factor': recency_factor
            }).fetchall()
            
            # Calculate scores in Python for clarity
            expert_scores = {}
            experience_details = {}
            
            for row in results:
                expert_id = row.expert_id
                exp_id = row.experience_id
                attr_id = row.attribute_id
                
                # Get similarity and weight for this attribute
                attr_info = attr_similarity.get(attr_id, {'similarity': 1.0, 'weight': 1.0})
                
                # Calculate experience score using geometric weights: (years * recency * similarity) ** weight
                # This ensures weight=0 makes the contribution neutral (score^0 = 1), effectively eliminating the attribute
                base_score = (
                    float(row.duration_years) * 
                    float(row.recency_multiplier) * 
                    attr_info['similarity']
                )
                
                weight = attr_info['weight']
                if weight == 0:
                    # Weight of 0 means no contribution from this attribute
                    exp_score = 0.0
                else:
                    # Geometric weight application: base_score raised to the power of (weight/2)
                    # Using weight/2 to prevent extreme values while maintaining zero-effect property
                    exp_score = base_score ** (weight / 2.0)
                
                # Accumulate expert score
                if expert_id not in expert_scores:
                    expert_scores[expert_id] = 0.0
                    experience_details[expert_id] = []
                
                expert_scores[expert_id] += exp_score
                
                # Store experience details (avoid duplicates)
                exp_key = f"{exp_id}_{attr_id}"
                if not any(ed.get('key') == exp_key for ed in experience_details[expert_id]):
                    experience_details[expert_id].append({
                        'key': exp_key,
                        'experience_id': exp_id,
                        'start_date': row.start_date,
                        'end_date': row.end_date,
                        'summary': row.summary,
                        'position': row.position,
                        'employer': row.employer,
                        'attribute_id': attr_id,
                        'score': exp_score,
                        'duration_years': float(row.duration_years)
                    })
            
            # Sort experts by total score
            sorted_experts = sorted(expert_scores.items(), key=lambda x: x[1], reverse=True)
            
            # Apply pagination
            offset = (page - 1) * page_size
            paginated_experts = sorted_experts[offset:offset + page_size]
            
            query_time = time.time() - query_start
            print(f"DEBUG - Scoring completed in {query_time:.2f}s")
            print(f"DEBUG - Found {len(expert_scores)} experts with scores")
            
            if not paginated_experts:
                return {
                    'experts': [],
                    'search_metadata': {
                        'extracted_attributes': extracted_attributes,
                        'total_experts': 0,
                        'search_time_ms': round((time.time() - start_time) * 1000, 2),
                        'message': 'No experts found with matching experience'
                    }
                }, 200
            
            # STEP 4: Get detailed expert information
            expert_ids = [expert_id for expert_id, score in paginated_experts]
            
            # Query experts with their experiences and attributes
            experts = session.query(Expert).options(
                joinedload(Expert.experiences).joinedload(Experience.attributes)
            ).filter(Expert.id.in_(expert_ids)).all()
            
            # Build response in score order
            expert_results = []
            print(f"DEBUG - About to process {len(paginated_experts)} paginated experts")
            
            for expert_id, total_score in paginated_experts:
                print(f"DEBUG - Processing expert {expert_id} with score {total_score}")
                # Find the expert object
                expert = next(e for e in experts if e.id == expert_id)
                
                # Build matching experiences from our stored details
                matching_experiences = []
                exp_groups = {}  # Group by experience_id
                
                for exp_detail in experience_details[expert_id]:
                    exp_id = exp_detail['experience_id']
                    if exp_id not in exp_groups:
                        exp_groups[exp_id] = {
                            'id': exp_id,
                            'summary': exp_detail['summary'],
                            'position': exp_detail['position'],
                            'employer': exp_detail['employer'],
                            'start_date': exp_detail['start_date'].isoformat(),
                            'end_date': exp_detail['end_date'].isoformat(),
                            'total_score': 0.0,
                            'matching_attributes': []
                        }
                    
                    exp_groups[exp_id]['total_score'] += exp_detail['score']
                    
                    # Find the attribute details
                    attr_id = exp_detail['attribute_id']
                    for attr in expert.experiences:
                        if attr.id == exp_id:
                            for attribute in attr.attributes:
                                if attribute.id == attr_id:
                                    # Get weight and similarity info for this attribute
                                    attr_info = attr_similarity.get(attr_id, {'similarity': 1.0, 'weight': 1.0})
                                    
                                    exp_groups[exp_id]['matching_attributes'].append({
                                        'id': attribute.id,
                                        'name': attribute.name,
                                        'type': attribute.type,
                                        'summary': attribute.summary,
                                        'similarity_score': round(attr_info['similarity'], 3),
                                        'type_weight': attr_info['weight'],
                                        'contribution_score': round(exp_detail['score'], 3)
                                    })
                                    break
                            break
                
                # Convert to list and sort by score
                matching_experiences = list(exp_groups.values())
                matching_experiences.sort(key=lambda x: x['total_score'], reverse=True)
                
                # Round scores
                for exp in matching_experiences:
                    exp['score'] = round(exp['total_score'], 2)
                    del exp['total_score']
                
                # Calculate score breakdown by attribute type with detailed matching information
                score_by_type = {}
                print(f"DEBUG - Starting SIMPLIFIED enhanced score breakdown for expert {expert_id}")
                try:
                    # First pass: collect basic data
                    for exp_detail in experience_details[expert_id]:
                        attr_id = exp_detail['attribute_id']
                        attr_info = attr_similarity.get(attr_id, {'similarity': 1.0, 'weight': 1.0})
                        exp_years = round(float(exp_detail.get('duration_years', 0)), 1)
                        
                        # Find attribute type and name
                        attr_type = None
                        attr_name = None
                        for attr in expert.experiences:
                            if attr.id == exp_detail['experience_id']:
                                for attribute in attr.attributes:
                                    if attribute.id == attr_id:
                                        attr_type = attribute.type
                                        attr_name = attribute.name
                                        break
                                break
                        
                        if attr_type and attr_name:
                            # Initialize if needed
                            if attr_type not in score_by_type:
                                score_by_type[attr_type] = {
                                    'type_weight': attr_info['weight'],
                                    'total_contribution': 0.0,
                                    'match_count': 0,
                                    'total_years': 0.0,
                                    'matched_terms': []
                                }
                            
                            # Add to totals
                            score_by_type[attr_type]['total_contribution'] += exp_detail['score']
                            score_by_type[attr_type]['match_count'] += 1
                            score_by_type[attr_type]['total_years'] += exp_years
                            
                            # Add matched term (simple version to avoid IndexError)
                            existing_term = any(t['name'] == attr_name for t in score_by_type[attr_type]['matched_terms'])
                            if not existing_term:
                                # Simple extracted term lookup
                                extracted_term = 'N/A'
                                if attr_type in search_attributes and search_attributes[attr_type]:
                                    for attr_data in search_attributes[attr_type]:
                                        if attr_data.get('id') == attr_id:
                                            extracted_term = attr_data.get('extracted_term', 'N/A')
                                            break
                                
                                score_by_type[attr_type]['matched_terms'].append({
                                    'name': attr_name,
                                    'similarity_score': round(float(attr_info.get('similarity', 0.0)), 3),
                                    'extracted_term': extracted_term,
                                    'years': exp_years
                                })
                    
                    print(f"DEBUG - SIMPLIFIED enhanced calculation completed successfully")

                except Exception as e:
                    print(f"ERROR - Enhanced score breakdown failed: {str(e)}")
                    print(f"ERROR - Exception type: {type(e).__name__}")
                    import traceback
                    traceback.print_exc()
                    print(f"ERROR - Falling back to basic score breakdown")
                    # Fall back to basic score breakdown
                    score_by_type = {}
                    for exp_detail in experience_details[expert_id]:
                        attr_id = exp_detail['attribute_id']
                        attr_info = attr_similarity.get(attr_id, {'similarity': 1.0, 'weight': 1.0})
                        # Find basic attribute type
                        attr_type = None
                        for attr in expert.experiences:
                            if attr.id == exp_detail['experience_id']:
                                for attribute in attr.attributes:
                                    if attribute.id == attr_id:
                                        attr_type = attribute.type
                                        break
                                break
                        if attr_type:
                            if attr_type not in score_by_type:
                                score_by_type[attr_type] = {
                                    'type_weight': attr_info['weight'],
                                    'total_contribution': 0.0,
                                    'match_count': 0
                                }
                            score_by_type[attr_type]['total_contribution'] += exp_detail['score']
                            score_by_type[attr_type]['match_count'] += 1

                # Create final score breakdown with enhanced fields (if available)
                final_score_breakdown = {}
                print(f"DEBUG - Pre-final score_by_type: {score_by_type}")
                for attr_type, data in score_by_type.items():
                    breakdown_entry = {
                        'type_weight': data['type_weight'],
                        'total_contribution': round(data['total_contribution'], 2),
                        'match_count': data['match_count']
                    }
                    # Add enhanced fields if they exist
                    if 'total_years' in data:
                        breakdown_entry['total_years'] = round(data['total_years'], 1)
                    if 'matched_terms' in data:
                        breakdown_entry['matched_terms'] = data['matched_terms']
                    
                    final_score_breakdown[attr_type] = breakdown_entry
                
                print(f"DEBUG - Final score breakdown for {expert.name}: {final_score_breakdown}")

                expert_result = {
                    'id': expert.id,
                    'name': expert.name,
                    'summary': expert.summary,
                    'status': expert.status,
                    'meta': expert.meta,
                    'total_score': round(total_score, 2),
                    'matching_experiences': matching_experiences,
                    'score_breakdown': final_score_breakdown
                }
                
                print(f"DEBUG - Expert result score_breakdown: {final_score_breakdown}")
                
                expert_results.append(expert_result)
            
            # Get total count for pagination
            total_count = len(expert_scores)
            search_time_ms = round((time.time() - start_time) * 1000, 2)
            
            # Debug: Check final response data
            final_response = {
                'experts': expert_results,
                'search_metadata': {
                    'extracted_attributes': extracted_attributes,
                    'search_summary': extracted_data.get('search_summary', ''),
                    'total_experts': total_count,
                    'page': page,
                    'page_size': page_size,
                    'total_pages': (total_count + page_size - 1) // page_size,
                    'search_time_ms': search_time_ms,
                    'settings_used': {
                        'similarity_threshold': effective_config['similarity_threshold'],
                        'recency_decay_factor': effective_config['recency_decay_factor'],
                        'attribute_weights': effective_config.get('attribute_weights', ATTRIBUTE_WEIGHTS)
                    },
                    'scoring_formula': 'Score = (Duration(years) × Recency × Similarity) ^ (TypeWeight/2), 0 weight = 0 contribution',
                    'attribute_type_weights': {
                        weight_item['name']: weight_item['weight'] 
                        for weight_item in effective_config.get('attribute_weights', ATTRIBUTE_WEIGHTS)
                    }
                }
            }
            
            # Debug final response structure
            if final_response['experts']:
                first_expert = final_response['experts'][0]
                print(f"DEBUG - Final response expert score_breakdown keys: {list(first_expert['score_breakdown'].keys())}")
                for attr_type, breakdown in first_expert['score_breakdown'].items():
                    print(f"DEBUG - Final response {attr_type} breakdown keys: {list(breakdown.keys())}")
            
            return final_response, 200
            
        except Exception as e:
            print(f"ERROR - Expert search failed: {str(e)}")
            import traceback
            traceback.print_exc()
            return {'message': f'Search failed: {str(e)}'}, 500
            
        finally:
            session.close()