from sentence_transformers import SentenceTransformer
import numpy as np


embedding_model = SentenceTransformer("all-MiniLM-L6-v2")

def get_embedding(text: str) -> np.ndarray:
    """Generate an embedding vector for a given text."""
    return embedding_model.encode([text], convert_to_numpy=True)[0]
