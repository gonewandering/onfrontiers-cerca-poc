# Configurable Attributes for LLM Function Calling

## Technical Requirements Document (TRD)

### Overview
This feature moves the hardcoded attribute types from the LLM extractor into a configurable system, allowing developers to specify which attribute types should be available for function calling during expert data extraction.

### Background
Previously, the LLM extractor had hardcoded attribute types `["agency", "role"]` that could be searched during function calling. This limited the system's flexibility and required code changes to support additional searchable attribute types.

### Requirements

#### Functional Requirements
1. **Configuration File**: Create a `config.py` file in the project root that contains the searchable attribute types
2. **Dynamic Loading**: The LLM extractor must dynamically read the configuration instead of using hardcoded values
3. **Backward Compatibility**: Existing functionality must remain unchanged for current attribute types
4. **Developer Control**: Developers can modify the configuration without touching core LLM extractor code

#### Technical Requirements
1. **Configuration Structure**: 
   ```python
   # config.py
   SEARCHABLE_ATTRIBUTE_TYPES = ["agency", "role"]
   ```

2. **Import Pattern**: The LLM extractor imports the configuration using standard Python imports
3. **Function Schema**: The search function schema dynamically uses the configured attribute types
4. **Error Handling**: Graceful handling if config.py is missing or malformed

### Implementation Details

#### Files Modified
- `config.py` (new): Contains the `SEARCHABLE_ATTRIBUTE_TYPES` list
- `lib/llm_extractor.py`: Updated to import and use the configuration

#### Code Changes
1. **config.py**:
   ```python
   # Attributes configuration for LLM function calling
   SEARCHABLE_ATTRIBUTE_TYPES = ["agency", "role"]
   ```

2. **lib/llm_extractor.py**:
   - Added import: `from config import SEARCHABLE_ATTRIBUTE_TYPES`
   - Updated function schema to use `SEARCHABLE_ATTRIBUTE_TYPES` instead of hardcoded list
   - Dynamic description generation based on configured types

#### Function Calling Schema
The search_attributes function now dynamically generates its schema:
```python
"attribute_type": {
    "type": "string",
    "enum": SEARCHABLE_ATTRIBUTE_TYPES,
    "description": f"Type of attribute to search for ({', '.join(SEARCHABLE_ATTRIBUTE_TYPES)} are supported)"
}
```

### Usage

#### For Developers
To add new searchable attribute types, simply update `config.py`:
```python
SEARCHABLE_ATTRIBUTE_TYPES = ["agency", "role", "skill", "technology"]
```

#### For System Integration
The expert search feature (as documented in `features.searchExperts.md`) references this configuration to determine which attribute types to query during the search process.

### Testing
- Verify that existing "agency" and "role" searches continue to work
- Test adding new attribute types to the configuration
- Confirm that function calling schema updates dynamically
- Validate error handling for missing configuration

### Dependencies
- No new external dependencies required
- Relies on existing OpenAI function calling infrastructure
- Compatible with current attribute search API endpoints

### Migration Notes
- No migration required for existing data
- No API changes for consumers
- Configuration change is transparent to existing functionality

### Future Enhancements
- Consider extending configuration to include attribute-specific search parameters
- Potential for more granular control over which attributes are searchable in different contexts
- Configuration validation and schema enforcement