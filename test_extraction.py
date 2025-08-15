#!/usr/bin/env python
"""
Test the new two-step expert extraction process
"""
import os
import json

# Load environment variables first
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

from lib.llm_extractor import LLMExtractor

def test_extraction():
    # Sample resume text
    test_text = """
    John Smith
    Senior Software Engineer
    
    Professional Experience:
    
    Google (2020 - Present)
    Senior Software Engineer
    - Led development of machine learning pipelines for YouTube recommendation system
    - Implemented distributed systems using Python and TensorFlow
    - Mentored junior engineers and conducted code reviews
    - Worked on Project Gemini, improving recommendation accuracy by 25%
    
    Microsoft (2017 - 2020) 
    Software Engineer II
    - Developed features for Azure cloud platform
    - Built RESTful APIs using C# and .NET Core
    - Implemented CI/CD pipelines using Azure DevOps
    - Contributed to Windows 11 development in the core OS team
    
    Stanford University (2013 - 2017)
    B.S. in Computer Science
    - GPA: 3.8/4.0
    - Teaching Assistant for CS106A Introduction to Programming
    - Research in Natural Language Processing under Prof. Christopher Manning
    """
    
    print("Testing Two-Step Expert Extraction")
    print("=" * 60)
    print("\nInput Text:")
    print("-" * 40)
    print(test_text)
    print("-" * 40)
    
    # Initialize extractor
    extractor = LLMExtractor()
    
    # Run extraction
    print("\nRunning extraction...")
    result = extractor.extract_expert_with_attributes(test_text)
    
    # Display results
    print("\n" + "=" * 60)
    print("EXTRACTION RESULTS")
    print("=" * 60)
    
    # Expert info
    expert = result.get('expert', {})
    print(f"\nExpert: {expert.get('name')}")
    print(f"Summary: {expert.get('summary')}")
    
    # Experiences
    experiences = result.get('experiences', [])
    print(f"\nTotal Experiences: {len(experiences)}")
    print("-" * 40)
    
    for i, exp in enumerate(experiences, 1):
        print(f"\nExperience {i}:")
        print(f"  Employer: {exp.get('employer')}")
        print(f"  Position: {exp.get('position')}")
        print(f"  Duration: {exp.get('start_date')} to {exp.get('end_date')}")
        print(f"  Activities: {exp.get('activities')[:100]}...")
        print(f"  Attribute IDs: {exp.get('attribute_ids', [])}")
        if exp.get('analysis_notes'):
            print(f"  Analysis: {exp.get('analysis_notes')[:100]}...")
    
    # Save to file for inspection
    with open('test_extraction_output.json', 'w') as f:
        json.dump(result, f, indent=2)
    
    print("\n" + "=" * 60)
    print("Full output saved to: test_extraction_output.json")

if __name__ == "__main__":
    test_extraction()