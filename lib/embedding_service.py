import openai
import os
import numpy as np
from typing import List, Optional, Tuple
import settings
from config import OPENAI_API_KEY

class EmbeddingService:
    def __init__(self):
        # Try config first, fall back to environment variable
        api_key = OPENAI_API_KEY or os.getenv('OPENAI_API_KEY')
        self.client = openai.OpenAI(api_key=api_key)
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
    
    def generate_batch_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for multiple texts in a single API call
        
        Args:
            texts: List of texts to generate embeddings for
            
        Returns:
            List of embedding vectors in the same order as input texts
        """
        try:
            if not texts:
                return []
            
            response = self.client.embeddings.create(
                input=texts,
                model=self.model
            )
            
            # Return embeddings in the same order as input
            return [item.embedding for item in response.data]
        except Exception as e:
            raise Exception(f"Failed to generate batch embeddings: {str(e)}")
    
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
    
    def cosine_similarity(self, embedding1: List[float], embedding2: List[float]) -> float:
        """
        Calculate cosine similarity between two embeddings
        
        Args:
            embedding1: First embedding vector
            embedding2: Second embedding vector
            
        Returns:
            Cosine similarity score between -1 and 1 (higher = more similar)
        """
        try:
            # Ensure inputs are lists/arrays
            if embedding1 is None or embedding2 is None:
                return 0.0
            
            # Convert to numpy arrays for efficient computation
            vec1 = np.array(embedding1, dtype=float)
            vec2 = np.array(embedding2, dtype=float)
            
            # Check dimensions match
            if vec1.shape != vec2.shape:
                print(f"Warning: embedding dimension mismatch: {vec1.shape} vs {vec2.shape}")
                return 0.0
            
            # Calculate norms
            norm1 = np.linalg.norm(vec1)
            norm2 = np.linalg.norm(vec2)
            
            # Handle zero vectors
            if norm1 == 0.0 or norm2 == 0.0:
                return 0.0
            
            # Calculate cosine similarity
            dot_product = np.dot(vec1, vec2)
            similarity = dot_product / (norm1 * norm2)
            
            return float(similarity)
            
        except Exception as e:
            print(f"Error calculating cosine similarity: {str(e)}")
            print(f"Embedding1 type: {type(embedding1)}, shape: {getattr(embedding1, 'shape', 'no shape')}")
            print(f"Embedding2 type: {type(embedding2)}, shape: {getattr(embedding2, 'shape', 'no shape')}")
            import traceback
            traceback.print_exc()
            return 0.0
    
    def find_similar_attributes(
        self, 
        query_embedding: List[float], 
        attribute_embeddings: List[Tuple[int, str, str, List[float]]], 
        similarity_threshold: float = 0.7,
        max_results: int = 10
    ) -> List[Tuple[int, str, str, float]]:
        """
        Find attributes similar to a query based on cosine similarity
        
        Args:
            query_embedding: The query embedding vector
            attribute_embeddings: List of (id, name, type, embedding) tuples
            similarity_threshold: Minimum similarity score to include (0-1)
            max_results: Maximum number of results to return
            
        Returns:
            List of (id, name, type, similarity_score) tuples, sorted by similarity desc
        """
        similarities = []
        
        for attr_id, attr_name, attr_type, attr_embedding in attribute_embeddings:
            if attr_embedding is not None and len(attr_embedding) > 0:  # Skip attributes without embeddings
                similarity = self.cosine_similarity(query_embedding, attr_embedding)
                if similarity >= similarity_threshold:
                    similarities.append((attr_id, attr_name, attr_type, similarity))
        
        # Sort by similarity descending and limit results
        similarities.sort(key=lambda x: x[3], reverse=True)
        return similarities[:max_results]

# Global instance for reuse
embedding_service = EmbeddingService()