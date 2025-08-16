import redis
import json
import hashlib
import time
import logging
import decimal
from typing import Optional, Dict, Any

# For embeddings
try:
    from sentence_transformers import SentenceTransformer
    model = SentenceTransformer('all-MiniLM-L6-v2')
    EMBEDDINGS_AVAILABLE = True
except ImportError:
    EMBEDDINGS_AVAILABLE = False
    model = None

logger = logging.getLogger(__name__)

# Redis connection
try:
    r = redis.Redis(host="localhost", port=6379, decode_responses=True)
    r.ping()
except Exception as e:
    logger.error(f"Redis connection failed: {e}")
    r = None

def get_embedding(text: str):
    """Generate embedding for text"""
    if EMBEDDINGS_AVAILABLE and model:
        return model.encode(text.lower().strip())
    else:
        # Simple hash-based similarity for testing
        return hashlib.md5(text.lower().strip().encode()).hexdigest()

def cosine_similarity(a, b):
    """Calculate cosine similarity between two embeddings"""
    if isinstance(a, str) or isinstance(b, str):
        # Hash-based similarity
        return 1.0 if a == b else 0.7 if a[:8] == b[:8] else 0.0
    
    # Vector similarity
    import numpy as np
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

def convert_decimals_to_float(obj):
    """Convert Decimal objects to float for JSON serialization"""
    if isinstance(obj, decimal.Decimal):
        return float(obj)
    elif isinstance(obj, dict):
        return {key: convert_decimals_to_float(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [convert_decimals_to_float(item) for item in obj]
    elif isinstance(obj, tuple):
        return tuple(convert_decimals_to_float(item) for item in obj)
    else:
        return obj

def store_semantic_cache(user_id: int, query: str, response_data: Dict[str, Any], ttl_seconds: int = 600):
    """Store in simple Redis hash"""
    if not r:
        return
    
    try:
        # Convert decimals
        clean_data = convert_decimals_to_float(response_data)
        
        # Generate embedding
        embedding = get_embedding(query)
        
        # Store with hash key
        cache_key = f"semantic_cache:{user_id}"
        query_id = hashlib.md5(query.encode()).hexdigest()[:12]
        
        cache_entry = {
            "query": query,
            "embedding": json.dumps(embedding.tolist()) if hasattr(embedding, 'tolist') else str(embedding),
            "response": json.dumps(clean_data),
            "timestamp": int(time.time())
        }
        
        r.hset(cache_key, query_id, json.dumps(cache_entry))
        r.expire(cache_key, ttl_seconds)
        
        logger.info(f"✅ Stored in simple cache: {query[:30]}...")
        
    except Exception as e:
        logger.error(f"Failed to store in cache: {e}")

def find_semantic_cache(user_id: int, query: str) -> Optional[Dict[str, Any]]:
    """Find similar cached queries"""
    if not r:
        return None
    
    try:
        cache_key = f"semantic_cache:{user_id}"
        cached_queries = r.hgetall(cache_key)
        
        if not cached_queries:
            logger.info("❌ No cached queries found")
            return None
        
        query_embedding = get_embedding(query)
        best_match = None
        best_score = 0.0
        
        for query_id, cache_data_str in cached_queries.items():
            try:
                cache_data = json.loads(cache_data_str)
                cached_query = cache_data["query"]
                
                # Get cached embedding
                cached_embedding_str = cache_data["embedding"]
                if cached_embedding_str.startswith('['):
                    # Vector embedding
                    import numpy as np
                    cached_embedding = np.array(json.loads(cached_embedding_str))
                else:
                    # Hash embedding
                    cached_embedding = cached_embedding_str
                
                # Calculate similarity
                similarity = cosine_similarity(query_embedding, cached_embedding)
                
                logger.info(f"🔍 '{cached_query}' similarity: {similarity:.3f}")
                
                if similarity > best_score:
                    best_score = similarity
                    best_match = cache_data
                    
            except Exception as e:
                logger.error(f"Error processing cached entry: {e}")
                continue
        
        # Check if best match is good enough
        if best_score >= 0.65:  # Threshold
            logger.info(f"✅ Cache HIT! Score: {best_score:.3f}")
            return json.loads(best_match["response"])
        else:
            logger.info(f"❌ Best score too low: {best_score:.3f}")
            return None
            
    except Exception as e:
        logger.error(f"Cache search failed: {e}")
        return None

if __name__ == "__main__":
    # Test
    print("Testing simple cache...")
    store_semantic_cache(999, "list all teachers", {"answer": "Teachers: John, Jane"})
    result = find_semantic_cache(999, "show all teachers")
    print("Result:", result)