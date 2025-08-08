# Attributes configuration for LLM function calling

import os

# Important: do not hardcode API keys in source. Use environment variables instead.
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
# OPENAI_API_KEY previously hardcoded has been removed
SEARCHABLE_ATTRIBUTE_TYPES = ["agency", "role", "seniority", "skill", "program"]

# Minimum similarity threshold for database attribute matching
ATTRIBUTE_MATCHING_THRESHOLD = 0.7

# Attribute weights for search scoring (higher = more important)
ATTRIBUTE_WEIGHTS = [
    {"name": "agency", "weight": 1.5},
    {"name": "role", "weight": 2.0}, 
    {"name": "seniority", "weight": 1.0},
    {"name": "skill", "weight": 1.8},
    {"name": "program", "weight": 1.2}
]

# Search configuration
SEARCH_CONFIG = {
    "max_attributes_per_type": 3,
    "scoring_base": 1.1,
    "recency_decay_factor": 0.1,
    "default_page_size": 20,
    "max_page_size": 100,
    # Cosine similarity settings
    "use_cosine_similarity": True,
    "similarity_threshold": 0.4,  # Minimum similarity to consider a match
    "max_similar_attributes": 20,  # Max attributes to consider per search
    "similarity_weight": 1.0,  # How much to weight similarity in scoring
    # Attribute weighting
    "attribute_weights": ATTRIBUTE_WEIGHTS
}
