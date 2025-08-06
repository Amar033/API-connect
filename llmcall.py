import urllib.request
import json 
from getschema import gettables

# def query_model(
#     prompt,
#     model="llama3",
#     url="http://localhost:11434/api/generate"
# ):
#     # Create the data payload as a dictionary
#     data = {
#         "model": model,
#         "prompt":prompt,
#         "stream":True,
#         "options": {     # Settings below are required for deterministic responses
#             "seed": 123,
#             "temperature": 0,
#             "num_ctx": 2048
#         }
#     }


#     # Convert the dictionary to a JSON formatted string and encode it to bytes
#     payload = json.dumps(data).encode("utf-8")

#     # Create a request object, setting the method to POST and adding necessary headers
#     request = urllib.request.Request(
#         url,
#         data=payload,
#         method="POST"
#     )
#     request.add_header("Content-Type", "application/json")

#     # Send the request and capture the response
#     response_data = ""
#     with urllib.request.urlopen(request) as response:
#         # Read and decode the response
#         while True:
#             line = response.readline().decode("utf-8")
#             if not line:
#                 break
#             response_json = json.loads(line)
#             response_data += response_json["message"]["content"]

#     return response_data

def query_model(
    prompt,
    model="llama3",
    url="http://localhost:11434/api/generate"  # Changed to generate API
):
    # Create the data payload as a dictionary
    data = {
        "model": model,
        "prompt": prompt,
        "stream": True,
        "options": {  # Settings below are required for deterministic responses
            "seed": 123,
            "temperature": 0,
            "num_ctx": 2048
        }
    }
    
    # Convert the dictionary to a JSON formatted string and encode it to bytes
    payload = json.dumps(data).encode("utf-8")
    
    # Create a request object, setting the method to POST and adding necessary headers
    request = urllib.request.Request(
        url,
        data=payload,
        method="POST"
    )
    request.add_header("Content-Type", "application/json")
    
    # Send the request and capture the response
    response_data = ""
    with urllib.request.urlopen(request) as response:
        # Read and decode the response
        while True:
            line = response.readline().decode("utf-8")
            if not line:
                break
            response_json = json.loads(line)
            # For generate API, the content is directly in "response" field
            response_data += response_json.get("response", "")
    
    return response_data

def clean_sql_query(sql_query: str) -> str:
    """Clean and validate SQL query from LLM response"""
    if not sql_query:
        return ""
    
    # Remove extra whitespace, newlines, and tabs
    cleaned = sql_query.strip()
    
    # Replace multiple whitespaces and newlines with single spaces
    import re
    cleaned = re.sub(r'\s+', ' ', cleaned)
    
    # Remove any markdown code block markers
    cleaned = re.sub(r'```sql\n?', '', cleaned)
    cleaned = re.sub(r'```\n?', '', cleaned)
    
    # Remove trailing semicolon if present (we'll add it back if needed)
    cleaned = cleaned.rstrip(';').strip()
    
    # Ensure single semicolon at the end
    cleaned = cleaned + ';'
    
    return cleaned



def response(user_input :str , company_name:str=None):
    if not user_input or not user_input.strip():
        raise ValueError("User input cannot be empty")
    schema = gettables(company_name)
    prompt = (
        "You are an expert SQL query generator.\n"
        "You will receive user intent as a string stored in a variable called user_input.\n"
        "Your task is to generate a single-line SQL query that accurately reflects the intent.\n"
        "Only return the SQL command. Do not add explanations or comments.\n"
        "Assume a general relational database schema unless specified in the input.\n"
        "If any table or column is not explicitly mentioned, make reasonable assumptions.\n"
        "Use simple, standard SQL (MySQL/PostgreSQL-compatible).\n"
        f"user_input: {user_input}\n"
        f"Schema: {schema}"
    )

    raw_sql=query_model(prompt=prompt)
    clean_sql=clean_sql_query(raw_sql)

    return clean_sql
