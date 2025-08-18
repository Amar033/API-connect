import redis
import numpy as np
import json
import logging
from typing import Optional, Dict, Any
from redis.commands.search.query import Query
from redis.commands.search.field import VectorField, TextField, NumericField, TagField
from redis.exceptions import ResponseError
import hashlib
import time
import decimal
import re

# For real semantic embeddings - install: pip install sentence-transformers
try:
    from sentence_transformers import SentenceTransformer
    EMBEDDINGS_AVAILABLE = True
except ImportError:
    EMBEDDINGS_AVAILABLE = False
    print("Warning: sentence-transformers not installed. Install with: pip install sentence-transformers")

logger = logging.getLogger(__name__)

# Redis connection for Docker container
try:
    r = redis.Redis(
        host="localhost",  # Change to your Docker container IP if needed
        port=6379,
        decode_responses=False,
        socket_connect_timeout=5,
        socket_timeout=5
    )
    # Test connection
    r.ping()
    print("✅ Redis connection successful")
except Exception as e:
    print(f"❌ Redis connection failed: {e}")
    r = None

INDEX_NAME = "semantic_cache_v2"
VECTOR_DIM = 384  # all-MiniLM-L6-v2 dimension
VECTOR_FIELD = "embedding"
SIMILARITY_THRESHOLD = 0.84  # Optimized for better semantic matching (0.6-0.8)

# Initialize embedding model
embedding_model = None
if EMBEDDINGS_AVAILABLE:
    try:
        embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
        print("✅ Sentence transformer model loaded")
    except Exception as e:
        print(f"❌ Failed to load embedding model: {e}")
        EMBEDDINGS_AVAILABLE = False

def create_index():
    """Create Redis search index for semantic caching"""
    if not r:
        return False
        
    try:
        # Try to drop existing index first
        try:
            r.ft(INDEX_NAME).dropindex()
            print(f"Dropped existing index {INDEX_NAME}")
        except:
            pass
            
        schema = (
            # Change from TextField to TagField for better handling of IDs
            TagField("user_id"),
            TextField("query"), 
            TextField("answer"),
            NumericField("timestamp"),
            VectorField(VECTOR_FIELD, "HNSW", {
                "TYPE": "FLOAT32",
                "DIM": VECTOR_DIM,
                "DISTANCE_METRIC": "COSINE"
            }),
        )
        r.ft(INDEX_NAME).create_index(schema)
        print(f"✅ Index {INDEX_NAME} created successfully")
        return True
    except ResponseError as e:
        if "Index already exists" in str(e):
            print(f"✅ Index {INDEX_NAME} already exists")
            return True
        print(f"❌ Failed to create index: {e}")
        return False

def get_embedding(text: str) -> Optional[np.ndarray]:
    """Generate semantic embedding for text"""
    if not EMBEDDINGS_AVAILABLE or not embedding_model:
        # Fallback to hash-based "embedding" for testing
        hash_val = int(hashlib.md5(text.lower().encode()).hexdigest(), 16)
        np.random.seed(hash_val % (2**32))
        return np.random.rand(VECTOR_DIM).astype(np.float32)
    
    try:
        # Normalize the query for better semantic matching
        normalized_text = text.lower().strip()
        embedding = embedding_model.encode(normalized_text)
        return embedding.astype(np.float32)
    except Exception as e:
        logger.error(f"Error generating embedding: {e}")
        return None

def store_semantic_cache(user_id: str, query: str, response_data: Dict[str, Any], ttl_seconds: int = 600):
    """Store query and response in semantic cache"""
    if not r:
        logger.warning("Redis not available, skipping cache storage")
        return
    
    try:
        # Generate embedding
        embedding = get_embedding(query)
        if embedding is None:
            logger.error("Failed to generate embedding, skipping cache storage")
            return
            
        # Create document ID
        query_hash = hashlib.md5(f"{user_id}:{query}".encode()).hexdigest()
        doc_id = f"semantic_cache:{query_hash}"
        
        # Prepare document
        doc_data = {
            "user_id": user_id,
            "query": query,
            "answer": json.dumps(response_data, cls=EnhancedJSONEncoder),
            "timestamp": int(time.time()),
            VECTOR_FIELD: embedding.tobytes()
        }
        
        # Store in Redis with TTL
        r.hset(doc_id, mapping=doc_data)
        r.expire(doc_id, ttl_seconds)
        
        logger.info(f"✅ Stored in semantic cache: {query[:50]}... (TTL: {ttl_seconds}s)")
        
    except Exception as e:
        logger.error(f"Failed to store in semantic cache: {e}")

def find_semantic_cache(user_id: str, query: str, k: int = 5) -> Optional[Dict[str, Any]]:
    """Find semantically similar cached responses using a combined query."""
    if not r:
        logger.warning("Redis not available, cache miss")
        return None

    try:
        # Generate embedding for the query
        embedding = get_embedding(query)
        if embedding is None:
            logger.error("Failed to generate embedding for search")
            return None

        # The fix: Escape hyphens and other special characters in the user_id.
        escaped_user_id = user_id.replace('-', '\\-')
        
        # Build the query with the escaped user_id.
        # This prevents the parser from misinterpreting the hyphen as a subtraction operator.
        base_query = f"(@user_id:{{{escaped_user_id}}})=>[KNN {k} @{VECTOR_FIELD} $vec AS score]"
        
        search_query = (
            Query(base_query)
            .sort_by("score")
            .return_fields("query", "answer", "score")
            .dialect(2)
        )

        results = r.ft(INDEX_NAME).search(
            search_query, 
            query_params={"vec": embedding.tobytes()}
        )
        
        if not results.docs:
            logger.info(f"❌ No semantic matches found for user {user_id}")
            return None

        # The first document will be the best match because we sorted by score
        best_match = results.docs[0]
        similarity_score = 1 - float(best_match.score) # Convert distance to similarity
        
        logger.info(f"🔍 Best semantic match for '{query}': '{best_match.query}' (similarity: {similarity_score:.3f})")
        
        if similarity_score >= SIMILARITY_THRESHOLD:
            logger.info(f"✅ Semantic cache HIT! Using cached response for similar query")
            try:
                cached_data = json.loads(best_match.answer)
                return cached_data
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse cached response: {e}")
                return None
        else:
            logger.info(f"❌ Similarity too low ({similarity_score:.3f} < {SIMILARITY_THRESHOLD})")
            return None
            
    except Exception as e:
        logger.error(f"Semantic cache search failed: {e}", exc_info=True)
        return None

def get_cache_stats(user_id: str) -> Dict[str, Any]:
    """Get cache statistics for a user"""
    if not r:
        return {"error": "Redis not available"}
        
    try:
        escaped_user_id = user_id.replace('-', '\\-')
        search_query = Query(f"@user_id:{{{escaped_user_id}}}").return_fields("query", "timestamp")
        results = r.ft(INDEX_NAME).search(search_query)
        
        entries = []
        for doc in results.docs:
            entries.append({
                "query": doc.query,
                "cached_at": doc.timestamp
            })
            
        return {
            "user_id": user_id,
            "total_cached_queries": len(entries),
            "entries": sorted(entries, key=lambda x: int(x["cached_at"]), reverse=True)[:10]
        }
    except Exception as e:
        return {"error": str(e)}

def clear_user_cache(user_id: str) -> bool:
    """Clear all cache entries for a user"""
    if not r:
        return False
        
    try:
        escaped_user_id = user_id.replace('-', '\\-')
        # Find all documents for the user
        search_query = Query(f"@user_id:{{{escaped_user_id}}}")
        results = r.ft(INDEX_NAME).search(search_query)
        
        # Delete each document
        deleted_count = 0
        for doc in results.docs:
            r.delete(doc.id)
            deleted_count += 1
            
        logger.info(f"Cleared {deleted_count} cache entries for user {user_id}")
        return True
    except Exception as e:
        logger.error(f"Failed to clear user cache: {e}")
        return False

def test_semantic_matching():
    """Test semantic matching functionality"""
    if not r:
        print("❌ Redis not available for testing")
        return
        
    print("🧪 Testing semantic cache...")
    
    # Test data
    test_user_id = "999-test-user-id"
    test_queries = [
        ("list all teachers", {"answer": "Here are all teachers: John, Jane, Bob", "sql": "SELECT * FROM teachers"}),
        ("show customer data", {"answer": "Customer data retrieved", "sql": "SELECT * FROM customers"}),
        ("count total orders", {"answer": "Total orders: 150", "sql": "SELECT COUNT(*) FROM orders"})
    ]
    
    # Store test data
    print("📝 Storing test queries...")
    for query, response in test_queries:
        store_semantic_cache(test_user_id, query, response, 300)
    
    # Wait for Redis to index the vectors
    print("⏳ Waiting for indexing...")
    time.sleep(2)
    
    # Check what's actually stored
    try:
        search_query = Query(f"@user_id:{{{test_user_id}}}").return_fields("query")
        results = r.ft(INDEX_NAME).search(search_query)
        print(f"📊 Found {len(results.docs)} stored queries:")
        for doc in results.docs:
            print(f"   - '{doc.query}'")
    except Exception as e:
        print(f"❌ Error checking stored queries: {e}")
        
    # Test similar queries with debug info
    similar_queries = [
        "show all teachers",  # Should match "list all teachers"
        "display teachers",   # Should match "list all teachers"  
        "get customer info",  # Should match "show customer data"
        "how many orders",    # Should match "count total orders"
        "list all students"   # Should NOT match anything
    ]
    
    print(f"\n🔍 Testing semantic matches (threshold: {SIMILARITY_THRESHOLD}):")
    for test_query in similar_queries:
        print(f"\n🔎 Searching for: '{test_query}'")
        result = find_semantic_cache_debug(test_user_id, test_query)
        status = "✅ HIT" if result else "❌ MISS"
        print(f"{status}: '{test_query}'")
        if result:
            print(f"     → Found: {result['answer'][:50]}...")
    
    # Clean up
    clear_user_cache(test_user_id)
    print("\n🧹 Test data cleaned up")

def find_semantic_cache_debug(user_id: str, query: str, k: int = 5) -> Optional[Dict[str, Any]]:
    """Debug version of find_semantic_cache with detailed logging"""
    if not r:
        print("❌ Redis not available")
        return None
    
    try:
        # Generate embedding for the query
        embedding = get_embedding(query)
        if embedding is None:
            print("❌ Failed to generate embedding")
            return None
            
        print(f"✅ Generated embedding for query")
        
        escaped_user_id = user_id.replace('-', '\\-')
        # Search for similar vectors
        search_query = (
            Query(f"(@user_id:{{{escaped_user_id}}})=>[KNN {k} @{VECTOR_FIELD} $vec AS score]")
            .sort_by("score")
            .return_fields("query", "answer", "score", "timestamp")
            .dialect(2)
        )
        
        results = r.ft(INDEX_NAME).search(
            search_query, 
            query_params={"vec": embedding.tobytes()}
        )
        
        print(f"📊 Found {len(results.docs)} potential matches")
        
        if not results.docs:
            print("❌ No documents found")
            return None
            
        # Show all matches for debugging
        for i, doc in enumerate(results.docs):
            similarity_score = 1 - float(doc.score)
            print(f"   {i+1}. '{doc.query}' - similarity: {similarity_score:.3f}")
        
        # Check the best match
        best_match = results.docs[0]
        similarity_score = 1 - float(best_match.score)
        
        print(f"🎯 Best match: '{best_match.query}' (similarity: {similarity_score:.3f}, threshold: {SIMILARITY_THRESHOLD})")
        
        if similarity_score >= SIMILARITY_THRESHOLD:
            print(f"✅ Similarity above threshold - returning cached result")
            try:
                cached_data = json.loads(best_match.answer)
                return cached_data
            except json.JSONDecodeError as e:
                print(f"❌ Failed to parse cached response: {e}")
                return None
        else:
            print(f"❌ Similarity too low ({similarity_score:.3f} < {SIMILARITY_THRESHOLD})")
            return None
            
    except Exception as e:
        print(f"❌ Search failed: {e}")
        return None
    
class EnhancedJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, decimal.Decimal):
            # Convert Decimals to float (or str, depending on your needs)
            return float(obj)
        return super().default(obj)


# Initialize index on import
if __name__ == "__main__":
    print("🚀 Initializing semantic cache...")
    success = create_index()
    if success:
        test_semantic_matching()
    else:
        print("❌ Failed to initialize semantic cache")
else:
    # Auto-initialize when imported
    create_index()