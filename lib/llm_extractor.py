import openai
import os
from typing import Dict, Any, Optional, List, Callable
import json
from pathlib import Path
import requests
from config import SEARCHABLE_ATTRIBUTE_TYPES

class LLMExtractor:
    def __init__(self, templates_dir: str = "promptTemplates", api_base_url: str = None):
        self.client = openai.OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        self.templates_dir = Path(templates_dir)
        self.api_base_url = api_base_url or os.getenv('API_BASE_URL', 'http://127.0.0.1:5000')
        
    def load_template(self, template_name: str) -> Dict[str, Any]:
        """
        Load a prompt template from the templates directory
        
        Args:
            template_name: Name of the template file (without .json extension)
            
        Returns:
            Template configuration as dictionary
        """
        template_path = self.templates_dir / f"{template_name}.json"
        if not template_path.exists():
            raise FileNotFoundError(f"Template not found: {template_path}")
            
        with open(template_path, 'r') as f:
            return json.load(f)
    
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
                                "enum": SEARCHABLE_ATTRIBUTE_TYPES,
                                "description": f"Type of attribute to search for ({', '.join(SEARCHABLE_ATTRIBUTE_TYPES)} are supported)"
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
            template_name: Name of the template file (without .json extension)
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
        
        # Use template metadata or overrides
        model = model_override or template.get("metadata", {}).get("model", "gpt-4o-mini")
        temperature = temperature_override or template.get("metadata", {}).get("temperature", 0.1)
        
        # Check if template specifies function calling
        template_enable_search = template.get("metadata", {}).get("enable_attribute_search", False)
        use_attribute_search = enable_attribute_search or template_enable_search
        
        print(template_enable_search)

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
    
    def extract_expert_data(self, text: str) -> Dict[str, Any]:
        """
        Extract expert data using the expert extraction template
        
        Args:
            text: Unstructured text input (resume, bio, etc.)
            
        Returns:
            Structured expert data as dictionary
        """
        return self.extract_from_template("expert_extraction", {"text": text})