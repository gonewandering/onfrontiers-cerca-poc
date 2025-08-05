import openai
import os
from typing import List, Optional
import settings

class EmbeddingService:
    def __init__(self):
        self.client = openai.OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        # Using OpenAI's latest text embedding model
        self.model = "text-embedding-3-small"  # More cost-effective, good performance
        # Alternative: "text-embedding-3-large" for higher quality but more expensive
    
    def generate_embedding(self, text: str) -> List[float]:
        """
        Generate an embedding for the given text using OpenAI's latest embedding model
        
        Args:
            text: The text to generate an embedding for
            
        Returns:
            List of floats representing the embedding vector
        """
        try:
            response = self.client.embeddings.create(
                input=text,
                model=self.model
            )
            return response.data[0].embedding
        except Exception as e:
            raise Exception(f"Failed to generate embedding: {str(e)}")
    
    def generate_attribute_embedding(self, name: str, type_str: str, summary: str) -> List[float]:
        """
        Generate an embedding for an attribute using name, type, and summary
        
        Args:
            name: The attribute name
            type_str: The attribute type
            summary: The attribute summary
            
        Returns:
            List of floats representing the embedding vector
        """
        # Combine attribute information into a meaningful text for embedding
        combined_text = f"{type_str}: {name} - {summary}"
        return self.generate_embedding(combined_text)

# Global instance for reuse
embedding_service = EmbeddingService()