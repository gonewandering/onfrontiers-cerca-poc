# Expert Search Feature - Technical Requirements Document (TRD)

## Overview
This feature implements an intelligent expert search system that uses LLM-based attribute extraction and a custom knowledge-based scoring algorithm to find the most relevant experts based on unstructured text input (solicitations, job descriptions, project requirements).

## Business Requirements
- **Primary Goal**: Enable users to find experts by submitting unstructured text descriptions
- **Use Cases**: 
  - Government agencies searching for contractors based on solicitation text
  - Companies finding internal experts for specific projects
  - Recruitment teams matching candidates to job requirements
- **Success Criteria**: Relevant experts are ranked higher based on experience relevance and recency

## Technical Architecture

### Endpoint Specification
- **Method**: POST
- **Path**: `/api/experts/search`
- **Content-Type**: `application/json` or `text/plain`
- **Response**: JSON array of experts ordered by relevance score

### Algorithm Overview
The search process follows a three-step pipeline:

1. **LLM Attribute Extraction**: Extract relevant attributes from input text
2. **Experience Scoring**: Calculate knowledge scores for each experience
3. **Expert Ranking**: Aggregate and rank experts by total knowledge score

## Detailed Technical Requirements

### Step 1: LLM Attribute Extraction

#### Requirements
- Use existing `LLMExtractor` class with function calling capabilities
- Leverage `config.py` `SEARCHABLE_ATTRIBUTE_TYPES` to determine which attribute types to extract
- Extract top 1-3 attributes for each configured attribute type
- Use attribute search function to find existing attribute IDs

#### Implementation Details
```python
# Input: Unstructured text
# Output: List of attribute IDs by type
{
  "agency": [123, 456, 789],
  "role": [101, 202, 303],
  # Additional types from config.py
}
```

#### Function Calling Schema
- Use existing `search_attributes` function from `LLMExtractor`
- Dynamic schema based on `SEARCHABLE_ATTRIBUTE_TYPES`
- Limit results to top 3 per attribute type for performance

### Step 2: Experience Knowledge Scoring

#### Scoring Formula
For each experience, calculate the Experience Knowledge Score (EKS):

```
EKS = (1.1^n) × duration_days × recency_factor

Where:
- n = number of matching attributes between experience and search
- duration_days = (end_date - start_date).days
- recency_factor = 1 - (0.25 × days_since_end / 365)
```

#### Database Query Requirements
- Join `Expert`, `Experience`, and `Attribute` tables
- Use `experience_attribute_association` for many-to-many relationships
- Filter experiences that have matching attributes from Step 1
- Calculate scores using SQL expressions for performance

#### SQL Query Structure
```sql
SELECT 
    e.expert_id,
    e.id as experience_id,
    COUNT(ea.attribute_id) as matching_attributes,
    (e.end_date - e.start_date) as duration_days,
    (CURRENT_DATE - e.end_date) as days_since_end,
    POW(1.1, COUNT(ea.attribute_id)) * 
    (e.end_date - e.start_date) * 
    (1 - 0.25 * (CURRENT_DATE - e.end_date) / 365) as experience_score
FROM experience e
JOIN experience_attribute ea ON e.id = ea.experience_id
WHERE ea.attribute_id IN (extracted_attribute_ids)
GROUP BY e.expert_id, e.id, e.start_date, e.end_date
```

### Step 3: Expert Aggregation and Ranking

#### Requirements
- Sum all Experience Knowledge Scores per expert
- Order experts by total score in descending order
- Include expert details and relevant experiences in response
- Support pagination for large result sets

#### Response Format
```json
{
  "experts": [
    {
      "id": 123,
      "name": "John Doe",
      "summary": "Senior Software Engineer...",
      "total_score": 1250.75,
      "matching_experiences": [
        {
          "id": 456,
          "summary": "Led cloud migration project...",
          "start_date": "2020-01-01",
          "end_date": "2022-12-31", 
          "score": 850.25,
          "matching_attributes": [
            {"id": 101, "name": "AWS", "type": "technology"},
            {"id": 202, "name": "Technical Lead", "type": "role"}
          ]
        }
      ]
    }
  ],
  "search_metadata": {
    "extracted_attributes": {...},
    "total_experts": 25,
    "search_time_ms": 150
  }
}
```

## Implementation Plan

### Phase 1: Core Search Endpoint
1. Create `routes/search.py` with `ExpertSearchResource` class
2. Implement LLM attribute extraction using existing `LLMExtractor`
3. Build basic scoring query with hardcoded attribute types
4. Return simple ranked list of experts

### Phase 2: Advanced Scoring
1. Implement full scoring formula with recency weighting
2. Add detailed experience matching in response
3. Include search metadata and performance metrics
4. Add input validation and error handling

### Phase 3: Optimization
1. Add database indexes for performance
2. Implement query result caching
3. Add pagination support
4. Performance monitoring and logging

## Database Schema Requirements

### Existing Tables (No Changes)
- `expert`: Contains expert basic information
- `experience`: Contains work experience records
- `attribute`: Contains searchable attributes with embeddings
- `experience_attribute`: Junction table for many-to-many relationships

### Required Indexes (New)
```sql
-- For performance optimization
CREATE INDEX idx_experience_dates ON experience(start_date, end_date);
CREATE INDEX idx_experience_expert_id ON experience(expert_id);
CREATE INDEX idx_experience_attribute_compound ON experience_attribute(attribute_id, experience_id);
```

## API Integration Points

### Dependencies
- `LLMExtractor` class for attribute extraction
- `config.py` for searchable attribute types
- Existing database models (`Expert`, `Experience`, `Attribute`)
- OpenAI API for function calling

### Configuration
```python
# config.py additions
SEARCH_CONFIG = {
    "max_attributes_per_type": 3,
    "scoring_base": 1.1,
    "recency_decay_factor": 0.25,
    "default_page_size": 20,
    "max_page_size": 100
}
```

## Error Handling & Edge Cases

### Input Validation
- Empty or invalid text input
- Malformed JSON requests
- Missing OpenAI API key

### Processing Errors
- LLM extraction failures
- Database query timeouts
- No matching attributes found
- No experts with matching experiences

### Response Handling
- Empty result sets
- Large result sets requiring pagination
- Attribute extraction yielding no searchable attributes

## Performance Considerations

### Query Optimization
- Use database indexes on frequently queried columns
- Limit attribute extraction to configured types only
- Implement query result caching for repeated searches

### Scalability
- Support pagination for large expert databases
- Consider async processing for complex searches
- Monitor query performance and optimize as needed

### Caching Strategy
- Cache LLM attribute extraction results (keyed by input text hash)
- Cache frequent search queries
- Cache attribute lookup results

## Testing Requirements

### Unit Tests
- LLM attribute extraction with various input types
- Scoring formula calculations
- Database query correctness
- Edge case handling

### Integration Tests
- End-to-end search workflow
- Performance with large datasets
- Error handling scenarios
- API response format validation

### Performance Tests
- Search response time under load
- Database query performance
- Memory usage with large result sets

## Security Considerations

### Input Sanitization
- Validate and sanitize all text inputs
- Prevent SQL injection through parameterized queries
- Rate limiting on search endpoints

### Data Privacy
- Ensure no sensitive information leaks in responses
- Audit logging for search activities
- Respect expert privacy settings (if implemented)

## Deployment Requirements

### Environment Variables
- OpenAI API key configuration
- Database connection parameters
- Search configuration overrides

### Database Migrations
- Create performance indexes
- No schema changes required for existing tables

### Monitoring
- API response time metrics
- Search success/failure rates
- Database query performance
- LLM API usage and costs

## Future Enhancements

### Advanced Features
- Semantic search using attribute embeddings
- Personalized search based on user preferences
- Search result explanations and confidence scores
- Advanced filtering and faceted search

### Machine Learning
- Learn from user interactions to improve rankings
- A/B testing for different scoring algorithms
- Automated attribute extraction quality monitoring

### User Experience
- Search query suggestions and autocompletion
- Saved searches and alerts
- Export search results to various formats