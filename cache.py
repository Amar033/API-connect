import redis
import os
import json
from decimal import Decimal
import numpy as np
from embedding import get_embedding
import hashlib
import logging


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

'''Initialize redis client'''
redis_client=redis.Redis(
    host=os.getenv("REDIS_HOST","localhost"),
    port=int(os.getenv("REDIS_PORT",6379)),
    db=0,
    decode_responses= True
)

def get_cache(key:str):
    '''Retrieve cached values'''
    data=redis_client.get(key)
    return json.loads(data)  if data else None

def set_cache(key:str, value,ttl:int=3600):
    '''Store the cached values'''
    redis_client.setex(key,ttl,json.dumps(value,default=_json_default))




def _json_default(obj):
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError(f"Type {type(obj)} not serializable")



import json
from numpy.linalg import norm

SIMILARITY_THRESHOLD = 0.85 # adjust as needed

def cosine_similarity(vec_a, vec_b):
    return np.dot(vec_a, vec_b) / (norm(vec_a) * norm(vec_b))

def find_semantic_cache(user_id: str, query: str):
    query_emb = get_embedding(query)

    # Get all keys for that user
    keys = redis_client.keys(f"semantic_cache:{user_id}:*")
    
    best_key, best_sim = None, 0
    for key in keys:
        stored = redis_client.get(key)
        if not stored:
            continue
        stored_data = json.loads(stored)
        emb = np.array(stored_data["embedding"])
        sim = cosine_similarity(query_emb, emb)
        if sim > best_sim:
            
            best_key, best_sim = key, sim

    if best_key and best_sim >= SIMILARITY_THRESHOLD:
        logger.info(f"Semantic cache HIT for key: {best_key} (similarity={best_sim:.4f})")
        return json.loads(redis_client.get(best_key))["response"]
    logger.info(f"Semantic cache MISS for query: '{query}' (best similarity={best_sim:.4f})")
    return None

def store_semantic_cache(user_id: str, query: str, response: dict, ttl: int = 3600):
    emb = get_embedding(query).tolist()
    cache_data = {
        "embedding": emb,
        "response": response
    }
    key = f"semantic_cache:{user_id}:{hashlib.sha256(query.encode()).hexdigest()}"
    redis_client.setex(key, ttl, json.dumps(cache_data,cls=EnhancedJSONEncoder))
    logger.info(f"Cache STORED for key: {key} (TTL={ttl}s)")


class EnhancedJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super().default(obj)