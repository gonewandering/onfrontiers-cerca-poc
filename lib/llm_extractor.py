import openai
import os
from typing import Dict, Any, Optional, List, Callable
import json
from pathlib import Path
import requests
from config import SEARCHABLE_ATTRIBUTE_TYPES, OPENAI_API_KEY

class LLMExtractor:
    def __init__(self, templates_dir: str = "promptTemplates", api_base_url: str = None):
        # Try config first, fall back to environment variable
        api_key = OPENAI_API_KEY or os.getenv('OPENAI_API_KEY')
        self.client = openai.OpenAI(api_key=api_key)
        self.templates_dir = Path(templates_dir)
        self.api_base_url = api_base_url or os.getenv('API_BASE_URL', 'http://127.0.0.1:5001')
        
    def load_template(self, template_name: str) -> Dict[str, Any]:
        """
        Load a prompt template from the database via API
        
        Args:
            template_name: Name of the template (e.g., "expert_extraction")
            
        Returns:
            Template configuration as dictionary
        """
        try:
            url = f"{self.api_base_url}/api/prompts/by-name/{template_name}"
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            
            return response.json()
            
        except requests.RequestException as e:
            # Fallback to file-based templates if API fails
            print(f"Warning: Failed to load template from database, falling back to files: {str(e)}")
            template_path = self.templates_dir / f"{template_name}.json"
            if not template_path.exists():
                raise FileNotFoundError(f"Template not found in database or files: {template_name}")
                
            with open(template_path, 'r') as f:
                return json.load(f)
    
    def get_existing_attribute(self, attribute_type: str, attribute_name: str) -> Dict[str, Any]:
        """
        DEPRECATED: Use search_attributes() instead.
        Find an existing attribute by exact name and type match.
        This method does NOT create new attributes.
        
        Args:
            attribute_type: Type of attribute (agency, role, etc.)
            attribute_name: Name of the attribute
            
        Returns:
            Dictionary with attribute info if found, empty dict otherwise
        """
        try:
            url = f"{self.api_base_url}/api/attributes"
            
            # Try to find existing attribute with exact name and type
            params = {
                'type': attribute_type,
                'q': attribute_name,
                'limit': 50  # Get more results to find exact matches
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            existing_attributes = response.json().get('attributes', [])
            
            # Look for exact match (case-insensitive)
            for attr in existing_attributes:
                if (attr.get('name', '').lower() == attribute_name.lower() and 
                    attr.get('type', '').lower() == attribute_type.lower()):
                    print(f"DEBUG - Found existing {attribute_type}: {attribute_name} (ID: {attr['id']})")
                    return attr
            
            # No exact match found - return empty dict
            print(f"DEBUG - No existing {attribute_type} found for: {attribute_name}")
            return {}
            
        except Exception as e:
            print(f"Warning: Failed to get attribute '{attribute_name}' ({attribute_type}): {str(e)}")
            return {}

    def search_attributes(self, attribute_type: str, search_query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Search for existing attributes by type and query
        
        Args:
            attribute_type: Type of attribute to search for
            search_query: Search query string
            limit: Maximum number of results to return
            
        Returns:
            List of matching attributes with id, name, type, summary
        """
        try:
            url = f"{self.api_base_url}/api/attributes"
            params = {
                'type': attribute_type,
                'q': search_query,
                'limit': limit
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            return data.get('attributes', [])
            
        except Exception as e:
            print(f"Warning: Failed to search attributes: {str(e)}")
            return []
    
    def extract_structured_data(
        self, 
        system_prompt: str, 
        user_prompt: str, 
        response_schema: Dict[str, Any],
        model: str = "gpt-4o-mini",
        temperature: float = 0.1,
        functions: List[Dict[str, Any]] = None,
        enable_attribute_search: bool = False
    ) -> Dict[str, Any]:
        """
        General purpose structured data extraction using OpenAI's structured outputs
        
        Args:
            system_prompt: System prompt defining the task and guidelines
            user_prompt: User prompt with the specific request and input data
            response_schema: JSON schema defining the expected output structure
            model: OpenAI model to use (default: gpt-4o-mini)
            temperature: Response randomness (default: 0.1 for consistency)
            functions: List of function definitions for function calling
            enable_attribute_search: Enable built-in attribute search function
            
        Returns:
            Structured data as a dictionary matching the provided schema
        """
        try:
            # Prepare function definitions
            available_functions = functions or []
            
            if enable_attribute_search:
                search_function = {
                    "name": "search_attributes",
                    "description": "Search for existing attributes by type and query to find IDs of pre-defined attributes",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "attribute_type": {
                                "type": "string",
                                "enum": ["agency", "role"],  # Only agency and role for better quality
                                "description": "Type of attribute to search for (agency or role)"
                            },
                            "search_query": {
                                "type": "string",
                                "description": "Search query to find matching attributes"
                            },
                            "limit": {
                                "type": "integer",
                                "default": 10,
                                "description": "Maximum number of results to return"
                            }
                        },
                        "required": ["attribute_type", "search_query"]
                    }
                }
                available_functions.append(search_function)
            
            # Build the request
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
            
            # Use function calling if functions are provided
            if available_functions:
                response = self.client.chat.completions.create(
                    model=model,
                    messages=messages,
                    functions=available_functions,
                    function_call="auto",
                    temperature=temperature
                )
                
                # Handle function calls
                while response.choices[0].message.function_call:
                    function_call = response.choices[0].message.function_call
                    function_name = function_call.name
                    function_args = json.loads(function_call.arguments)
                    
                    # Execute the function
                    if function_name == "search_attributes" and enable_attribute_search:
                        search_results = self.search_attributes(
                            function_args.get("attribute_type"),
                            function_args.get("search_query"),
                            function_args.get("limit", 10)
                        )
                        function_result = json.dumps(search_results)
                    else:
                        function_result = json.dumps({"error": f"Unknown function: {function_name}"})
                    
                    # Add function call and result to messages
                    messages.append({
                        "role": "assistant",
                        "content": None,
                        "function_call": {
                            "name": function_name,
                            "arguments": function_call.arguments
                        }
                    })
                    messages.append({
                        "role": "function",
                        "name": function_name,
                        "content": function_result
                    })
                    
                    # Get next response
                    response = self.client.chat.completions.create(
                        model=model,
                        messages=messages,
                        functions=available_functions,
                        function_call="auto",
                        temperature=temperature
                    )
                
                # After function calls, get structured output
                messages.append({
                    "role": "assistant", 
                    "content": response.choices[0].message.content
                })
                
                # Final structured parsing
                final_response = self.client.beta.chat.completions.parse(
                    model=model,
                    messages=messages,
                    response_format={"type": "json_schema", "json_schema": {"name": "structured_output", "schema": response_schema}},
                    temperature=temperature
                )
                
                return json.loads(final_response.choices[0].message.content)
                
            else:
                # No functions, use direct structured output
                response = self.client.beta.chat.completions.parse(
                    model=model,
                    messages=messages,
                    response_format={"type": "json_schema", "json_schema": {"name": "structured_output", "schema": response_schema}},
                    temperature=temperature
                )
                
                return json.loads(response.choices[0].message.content)
            
        except Exception as e:
            raise Exception(f"Failed to extract structured data: {str(e)}")
    
    def extract_from_template(
        self, 
        template_name: str, 
        template_variables: Dict[str, Any] = None,
        model_override: str = None,
        temperature_override: float = None,
        enable_attribute_search: bool = False
    ) -> Dict[str, Any]:
        """
        Extract structured data using a template
        
        Args:
            template_name: Name of the template (e.g., "expert_extraction")
            template_variables: Variables to substitute in the template (e.g., {text: "..."})
            model_override: Override the model specified in template
            temperature_override: Override the temperature specified in template
            enable_attribute_search: Enable built-in attribute search function
            
        Returns:
            Structured data as dictionary
        """
        template = self.load_template(template_name)
        template_variables = template_variables or {}
        
        # Format user prompt with variables
        user_prompt = template["user_prompt_template"].format(**template_variables)
        
        # Use template metadata or overrides (database format)
        metadata = template.get("metadata", {})
        model = model_override or metadata.get("model") or template.get("model", "gpt-4o-mini")
        temperature = temperature_override or metadata.get("temperature") or template.get("temperature", 0.1)
        
        # Check if template specifies function calling (database format)
        template_enable_search = metadata.get("enable_attribute_search") or template.get("enable_attribute_search", False)
        use_attribute_search = enable_attribute_search or template_enable_search
        
        print(f"DEBUG - Using template: {template_name}, model: {model}, enable_search: {use_attribute_search}")

        out = self.extract_structured_data(
            system_prompt=template["system_prompt"],
            user_prompt=user_prompt,
            response_schema=template["response_schema"],
            model=model,
            temperature=temperature,
            functions=template.get("functions"),
            enable_attribute_search=use_attribute_search
        )
        
        print(out)
        return out
    
    def extract_expert_structured(self, text: str) -> Dict[str, Any]:
        """
        Extract structured expert and experience data without attributes
        
        Args:
            text: Unstructured text input (resume, bio, etc.)
            
        Returns:
            Structured expert data with experiences (no attributes)
        """
        return self.extract_from_template("expert_extraction_structured", {"text": text})
    
    def analyze_experience_attributes(self, experience: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze a single experience and identify relevant attributes from database
        
        Args:
            experience: Dictionary with employer, position, activities, start_date, end_date
            
        Returns:
            Dictionary with attribute_ids and analysis_notes
        """
        return self.extract_from_template(
            "experience_attribute_analysis",
            {
                "employer": experience.get("employer", ""),
                "position": experience.get("position", ""),
                "summary": experience.get("summary", experience.get("activities", "")),  # Support both for backwards compatibility
                "start_date": experience.get("start_date", ""),
                "end_date": experience.get("end_date", "")
            },
            enable_attribute_search=True
        )
    
    def extract_expert_with_attributes_fast(self, text: str) -> Dict[str, Any]:
        """
        Optimized extraction using structured LLM call + intelligent tool calling for attributes
        
        Args:
            text: Unstructured text input (resume, bio, etc.)
            
        Returns:
            Complete expert data with experiences and matched attributes
        """
        import time
        
        # Step 1: Extract structured expert and experience data (single LLM call)
        print("Step 1: Extracting structured expert data...")
        start_time = time.time()
        structured_data = self.extract_expert_structured(text)
        extraction_time = time.time() - start_time
        print(f"Extraction completed in {extraction_time:.2f}s")
        
        experiences = structured_data.get("experiences", [])
        if not experiences:
            return {
                "expert": structured_data.get("expert", {}),
                "experiences": []
            }
        
        # Step 2: Use intelligent LLM-guided tool calling for attribute matching
        print(f"Step 2: Analyzing attributes for {len(experiences)} experiences with LLM guidance...")
        analysis_start = time.time()
        
        try:
            # Batch analyze all experiences with intelligent tool calling
            experiences_with_attributes = self.analyze_experiences_with_tools(experiences)
            
            analysis_time = time.time() - analysis_start
            print(f"LLM-guided attribute analysis completed in {analysis_time:.2f}s")
            print(f"Total extraction time: {extraction_time + analysis_time:.2f}s")
            
            return {
                "expert": structured_data.get("expert", {}),
                "experiences": experiences_with_attributes
            }
            
        except Exception as e:
            print(f"Warning: Tool-based analysis failed, falling back to basic processing: {str(e)}")
            return self.extract_expert_with_attributes_fallback(structured_data, extraction_time)
    
    def analyze_experiences_with_tools(self, experiences: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Analyze experiences using LLM with tool calling for intelligent attribute matching
        Only searches for agency and role attributes
        """
        experiences_text = ""
        for i, exp in enumerate(experiences):
            experiences_text += f"\nExperience {i+1}:\n"
            experiences_text += f"Employer: {exp.get('employer', '')}\n"
            experiences_text += f"Position: {exp.get('position', '')}\n"
            experiences_text += f"Summary: {exp.get('summary', '')}\n"
            experiences_text += f"Duration: {exp.get('start_date', '')} to {exp.get('end_date', '')}\n"
        
        system_prompt = """You are an expert at analyzing professional experiences and identifying relevant attributes.

Your task is to analyze professional experiences and identify the most relevant agencies and roles from the database.

You MUST use the search_attributes function to find existing attributes in the database. Only search for:
- agency: The organization/company/institution (be smart about variations, acronyms, and official names)
- role: The job function or title (search for the core role, not the full title with modifiers)

IMPORTANT:
- For agencies, search for the actual organization name, not generic terms
- For roles, search for the job function (e.g., "Program Manager" not "Senior Program Manager Level III")
- Use intelligent search queries that will match database entries
- If an organization has common abbreviations or variations, try those too
- Only return attribute IDs that exist in the database
- Focus on quality over quantity - only match clear, relevant attributes"""

        user_prompt = f"Analyze these professional experiences and identify relevant agencies and roles from the database:\n{experiences_text}\n\nFor each experience, intelligently search for the most likely agency and role matches in the database."
        
        response_schema = {
            "type": "object",
            "properties": {
                "experiences": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "experience_index": {
                                "type": "integer",
                                "description": "Index of the experience (1-based)"
                            },
                            "attribute_ids": {
                                "type": "array",
                                "items": {"type": "integer"},
                                "description": "List of attribute IDs from the database"
                            },
                            "search_notes": {
                                "type": "string",
                                "description": "What you searched for and why"
                            }
                        },
                        "required": ["experience_index", "attribute_ids", "search_notes"]
                    }
                }
            },
            "required": ["experiences"]
        }
        
        # Use structured extraction with function calling
        batch_analysis = self.extract_structured_data(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            response_schema=response_schema,
            model="gpt-4o-mini",
            temperature=0.2,
            enable_attribute_search=True
        )
        
        # Merge results back with original experiences
        experiences_with_attributes = []
        analysis_results = {result["experience_index"]: result for result in batch_analysis.get("experiences", [])}
        
        for i, experience in enumerate(experiences):
            exp_index = i + 1
            analysis = analysis_results.get(exp_index, {"attribute_ids": [], "search_notes": "No analysis available"})
            
            exp_with_attrs = {
                "employer": experience.get("employer"),
                "position": experience.get("position"),
                "summary": experience.get("summary", ""),
                "start_date": experience.get("start_date"),
                "end_date": experience.get("end_date"),
                "attribute_ids": analysis.get("attribute_ids", []),
                "analysis_notes": analysis.get("search_notes", "")
            }
            experiences_with_attributes.append(exp_with_attrs)
            
            print(f"  Experience {exp_index}: {len(analysis.get('attribute_ids', []))} attributes matched")
            if analysis.get("search_notes"):
                print(f"    Search notes: {analysis.get('search_notes')}")
        
        return experiences_with_attributes
    
    def match_attributes_locally(self, experiences: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Match attributes using the existing search API - optimized for speed and accuracy
        """
        from config import SEARCHABLE_ATTRIBUTE_TYPES
        import requests
        
        experiences_with_attributes = []
        
        for i, experience in enumerate(experiences):
            print(f"  Processing experience {i+1}/{len(experiences)}: {experience.get('position', 'Unknown')} at {experience.get('employer', 'Unknown')}")
            
            matched_attribute_ids = []
            
            # Agency search - use employer only, be specific
            if experience.get('employer'):
                try:
                    response = requests.get(
                        f"{self.api_base_url}/api/attributes",
                        params={
                            'type': 'agency',
                            'q': experience['employer'],
                            'limit': 5  # Get more results to find good matches
                        },
                        timeout=3
                    )
                    
                    if response.status_code == 200:
                        results = response.json().get('attributes', [])
                        # Take the top result if similarity is good, or if name is very similar
                        for attr in results[:2]:  # Take top 2 agencies max
                            similarity = attr.get('similarity_score', 0)
                            # Lower threshold for agencies since exact matches are important
                            if similarity > 0.5 or experience['employer'].lower() in attr['name'].lower():
                                matched_attribute_ids.append(attr['id'])
                                print(f"    Matched agency: {attr['name']} (ID: {attr['id']}, similarity: {similarity:.3f})")
                                break  # Only take the best agency match
                except Exception as e:
                    print(f"    Warning: Error searching agency: {str(e)}")
            
            # Role search - use position only
            if experience.get('position'):
                try:
                    response = requests.get(
                        f"{self.api_base_url}/api/attributes",
                        params={
                            'type': 'role',
                            'q': experience['position'],
                            'limit': 3
                        },
                        timeout=3
                    )
                    
                    if response.status_code == 200:
                        results = response.json().get('attributes', [])
                        for attr in results[:1]:  # Take top role match
                            similarity = attr.get('similarity_score', 0)
                            if similarity > 0.6:  # Lower threshold for roles
                                matched_attribute_ids.append(attr['id'])
                                print(f"    Matched role: {attr['name']} (ID: {attr['id']}, similarity: {similarity:.3f})")
                except Exception as e:
                    print(f"    Warning: Error searching role: {str(e)}")
            
            # Skip seniority, skill, and program searches for now to improve speed
            # These are less critical and slow down the process significantly
            
            # Create experience with attributes
            exp_with_attrs = {
                "employer": experience.get("employer"),
                "position": experience.get("position"), 
                "summary": experience.get("summary", experience.get("activities", "")),
                "start_date": experience.get("start_date"),
                "end_date": experience.get("end_date"),
                "attribute_ids": matched_attribute_ids,
                "analysis_notes": f"Fast API search found {len(matched_attribute_ids)} key attributes"
            }
            experiences_with_attributes.append(exp_with_attrs)
            print(f"    Total: {len(matched_attribute_ids)} attributes matched")
        
        return experiences_with_attributes
    
    def analyze_all_experiences_batch(self, experiences: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Analyze all experiences in a single LLM call for better performance
        """
        # Create batch prompt
        experiences_text = ""
        for i, exp in enumerate(experiences):
            experiences_text += f"\nExperience {i+1}:\n"
            experiences_text += f"Employer: {exp.get('employer', '')}\n"
            experiences_text += f"Position: {exp.get('position', '')}\n"
            experiences_text += f"Summary: {exp.get('summary', exp.get('activities', ''))}\n"
            experiences_text += f"Duration: {exp.get('start_date', '')} to {exp.get('end_date', '')}\n"
        
        # Use structured extraction with function calling
        system_prompt = """You are an expert at analyzing professional experiences and identifying relevant attributes.

Your task is to analyze multiple professional experiences and identify the most relevant attributes from the database for each one.

You MUST use the search_attributes function to find existing attributes in the database. DO NOT suggest attributes that don't exist in the database.

For each experience, search for and identify:
- Agency: The organization/company (search in 'agency' type)
- Roles: Job functions and titles (search in 'role' type) 
- Seniority: Level of responsibility (search in 'seniority' type)
- Skills: Technical and professional competencies demonstrated (search in 'skill' type)
- Programs: Specific projects or initiatives mentioned (search in 'program' type)

IMPORTANT:
- Only return attribute IDs that exist in the database
- Use the search function to find the best matches
- If no good match exists for a term, do not include it
- Focus on the most relevant and specific attributes (quality over quantity)
- Aim for 3-10 total attributes per experience"""

        user_prompt = f"Analyze these professional experiences and identify relevant attributes from the database for each one:\n{experiences_text}\n\nFor each experience, search the database for relevant attributes and return only those that exist."
        
        response_schema = {
            "type": "object",
            "properties": {
                "experiences": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "experience_index": {
                                "type": "integer",
                                "description": "Index of the experience (1-based)"
                            },
                            "attribute_ids": {
                                "type": "array",
                                "items": {"type": "integer"},
                                "description": "List of attribute IDs from the database"
                            },
                            "analysis_notes": {
                                "type": "string",
                                "description": "Brief explanation of attribute selection"
                            }
                        },
                        "required": ["experience_index", "attribute_ids", "analysis_notes"]
                    }
                }
            },
            "required": ["experiences"]
        }
        
        batch_analysis = self.extract_structured_data(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            response_schema=response_schema,
            model="gpt-4o-mini",
            temperature=0.2,
            enable_attribute_search=True
        )
        
        # Merge results back with original experiences
        experiences_with_attributes = []
        analysis_results = {result["experience_index"]: result for result in batch_analysis.get("experiences", [])}
        
        for i, experience in enumerate(experiences):
            exp_index = i + 1
            analysis = analysis_results.get(exp_index, {"attribute_ids": [], "analysis_notes": "No analysis available"})
            
            exp_with_attrs = {
                "employer": experience.get("employer"),
                "position": experience.get("position"),
                "summary": experience.get("summary", experience.get("activities", "")),
                "start_date": experience.get("start_date"),
                "end_date": experience.get("end_date"),
                "attribute_ids": analysis.get("attribute_ids", []),
                "analysis_notes": analysis.get("analysis_notes", "")
            }
            experiences_with_attributes.append(exp_with_attrs)
            
            print(f"  Experience {exp_index}: {len(analysis.get('attribute_ids', []))} attributes")
        
        return {"experiences": experiences_with_attributes}
    
    def extract_expert_with_attributes_fallback(self, structured_data: Dict[str, Any], extraction_time: float) -> Dict[str, Any]:
        """
        Fallback to individual experience processing if batch fails
        """
        print("Step 2 (fallback): Analyzing attributes for each experience individually...")
        analysis_start = time.time()
        
        experiences_with_attributes = []
        for i, experience in enumerate(structured_data.get("experiences", [])):
            print(f"  Analyzing experience {i+1}/{len(structured_data.get('experiences', []))}: {experience.get('position')} at {experience.get('employer')}")
            
            try:
                attribute_analysis = self.analyze_experience_attributes(experience)
                attribute_ids = attribute_analysis.get("attribute_ids", [])
                
                exp_with_attrs = {
                    "employer": experience.get("employer"),
                    "position": experience.get("position"),
                    "summary": experience.get("summary", experience.get("activities", "")),
                    "start_date": experience.get("start_date"),
                    "end_date": experience.get("end_date"),
                    "attribute_ids": attribute_ids,
                    "analysis_notes": attribute_analysis.get("analysis_notes", "")
                }
                experiences_with_attributes.append(exp_with_attrs)
                
                print(f"    Found {len(attribute_ids)} relevant attributes")
                
            except Exception as e:
                print(f"    Warning: Failed to analyze attributes for experience: {str(e)}")
                experiences_with_attributes.append({
                    **experience,
                    "attribute_ids": [],
                    "analysis_notes": f"Attribute analysis failed: {str(e)}"
                })
        
        analysis_time = time.time() - analysis_start
        print(f"Fallback attribute analysis completed in {analysis_time:.2f}s")
        print(f"Total extraction time: {extraction_time + analysis_time:.2f}s")
        
        return {
            "expert": structured_data.get("expert", {}),
            "experiences": experiences_with_attributes
        }

    def extract_expert_with_attributes(self, text: str) -> Dict[str, Any]:
        """
        Two-step extraction: first extract structured data, then analyze attributes
        Uses fast batch processing by default
        
        Args:
            text: Unstructured text input (resume, bio, etc.)
            
        Returns:
            Complete expert data with experiences and matched attributes
        """
        return self.extract_expert_with_attributes_fast(text)
    
    def extract_expert_data(self, text: str) -> Dict[str, Any]:
        """
        Extract expert data using the expert extraction template
        
        Args:
            text: Unstructured text input (resume, bio, etc.)
            
        Returns:
            Structured expert data as dictionary
        """
        return self.extract_from_template("expert_extraction", {"text": text})
    
    def extract_expert_data_fast(self, text: str) -> Dict[str, Any]:
        """
        Fast expert data extraction without function calling
        
        Args:
            text: Unstructured text input (resume, bio, etc.)
            
        Returns:
            Structured expert data with attribute terms for separate searching
        """
        import time
        
        # Step 1: Extract basic structure without function calling
        extraction_start = time.time()
        raw_data = self.extract_from_template("expert_extraction_fast", {"text": text})
        extraction_time = time.time() - extraction_start
        print(f"DEBUG - Fast extraction completed in {extraction_time:.2f}s")
        
        # Step 2: Search for attributes in database
        search_start = time.time()
        experiences = []
        
        for exp_data in raw_data.get('experiences', []):
            # Handle "present" dates
            end_date = exp_data.get('end_date', '')
            if end_date.lower() in ['present', 'current', 'ongoing', 'now']:
                from datetime import datetime
                end_date = datetime.now().date().isoformat()
            
            experience = {
                'start_date': exp_data.get('start_date'),
                'end_date': end_date,
                'summary': exp_data.get('summary', ''),
                'attributes': []
            }
            
            # Process all configured attribute types dynamically
            total_processed = 0
            total_skipped = 0
            
            for attr_type in SEARCHABLE_ATTRIBUTE_TYPES:
                attr_key = f"{attr_type}_terms"
                terms = exp_data.get(attr_key, [])
                
                for term in terms:
                    if term.strip():
                        experience['attributes'].append({
                            'name': term,
                            'type': attr_type,
                            'summary': f"{attr_type.title()}: {term}"
                        })
                        total_processed += 1
                
                if terms:
                    print(f"DEBUG - Processed {len(terms)} {attr_type} terms")
            
            # Count skipped terms (other_terms not in configured types)
            other_terms = exp_data.get('other_terms', [])
            if other_terms:
                total_skipped = len(other_terms)
                print(f"DEBUG - Skipped {total_skipped} other_terms (not in SEARCHABLE_ATTRIBUTE_TYPES: {SEARCHABLE_ATTRIBUTE_TYPES})")
            
            print(f"DEBUG - Total processed: {total_processed} attributes, skipped: {total_skipped}")
            
            experiences.append(experience)
        
        search_time = time.time() - search_start  
        print(f"DEBUG - Attribute search completed in {search_time:.2f}s")
        
        return {
            'expert': raw_data.get('expert', {}),
            'experiences': experiences
        }