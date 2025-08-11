import redis
import os
import json
from decimal import Decimal


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

