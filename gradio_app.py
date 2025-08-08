import gradio as gr
import requests
import json
from typing import List, Dict, Any
import os

# API Configuration
API_BASE_URL = "http://localhost:8000"  # Adjust if your API runs on different port

class APIClient:
    def __init__(self, base_url: str = API_BASE_URL):
        self.base_url = base_url
        self.token = None
    
    def register_user(self, name: str, email: str, password: str) -> Dict[str, Any]:
        """Register a new user"""
        url = f"{self.base_url}/users/"
        data = {
            "name": name,
            "email": email,
            "password": password
        }
        try:
            response = requests.post(url, json=data)
            return {
                "success": response.status_code == 201,
                "data": response.json() if response.status_code == 201 else response.text,
                "status_code": response.status_code
            }
        except Exception as e:
            return {"success": False, "data": str(e), "status_code": 500}
    
    def login_user(self, email: str, password: str) -> Dict[str, Any]:
        """Login user and get access token"""
        url = f"{self.base_url}/token"
        data = {
            "username": email,
            "password": password
        }
        try:
            response = requests.post(url, data=data)
            if response.status_code == 200:
                token_data = response.json()
                self.token = token_data["access_token"]
                return {
                    "success": True,
                    "data": token_data,
                    "status_code": response.status_code
                }
            else:
                return {
                    "success": False,
                    "data": response.text,
                    "status_code": response.status_code
                }
        except Exception as e:
            return {"success": False, "data": str(e), "status_code": 500}
    
    def get_headers(self):
        """Get headers with authentication token"""
        if self.token:
            return {"Authorization": f"Bearer {self.token}"}
        return {}
    
    def get_user_info(self) -> Dict[str, Any]:
        """Get current user information"""
        url = f"{self.base_url}/me"
        try:
            response = requests.get(url, headers=self.get_headers())
            return {
                "success": response.status_code == 200,
                "data": response.json() if response.status_code == 200 else response.text,
                "status_code": response.status_code
            }
        except Exception as e:
            return {"success": False, "data": str(e), "status_code": 500}
    
    def get_database_connections(self, include_status: bool = True) -> Dict[str, Any]:
        """Get user's database connections"""
        url = f"{self.base_url}/db-connections/"
        params = {"include_status": include_status}
        try:
            response = requests.get(url, headers=self.get_headers(), params=params)
            return {
                "success": response.status_code == 200,
                "data": response.json() if response.status_code == 200 else response.text,
                "status_code": response.status_code
            }
        except Exception as e:
            return {"success": False, "data": str(e), "status_code": 500}
    
    def add_database_connection(self, name: str, host: str, port: int, dbname: str, 
                               db_user: str, db_password: str, db_owner_username: str = "") -> Dict[str, Any]:
        """Add a new database connection"""
        url = f"{self.base_url}/db-connections/"
        data = {
            "name": name,
            "host": host,
            "port": port,
            "dbname": dbname,
            "db_user": db_user,
            "db_password": db_password,
            "db_owner_username": db_owner_username
        }
        try:
            response = requests.post(url, json=data, headers=self.get_headers())
            return {
                "success": response.status_code == 200,
                "data": response.json() if response.status_code == 200 else response.text,
                "status_code": response.status_code
            }
        except Exception as e:
            return {"success": False, "data": str(e), "status_code": 500}
    
    def delete_database_connection(self, connection_id: str) -> Dict[str, Any]:
        """Delete a database connection"""
        url = f"{self.base_url}/db-connections/{connection_id}"
        try:
            response = requests.delete(url, headers=self.get_headers())
            return {
                "success": response.status_code == 200,
                "data": response.json() if response.status_code == 200 else response.text,
                "status_code": response.status_code
            }
        except Exception as e:
            return {"success": False, "data": str(e), "status_code": 500}
    
    def get_database_summary(self) -> Dict[str, Any]:
        """Get database summary and sample questions"""
        url = f"{self.base_url}/llm-chat/summary"
        try:
            response = requests.get(url, headers=self.get_headers())
            return {
                "success": response.status_code == 200,
                "data": response.json() if response.status_code == 200 else response.text,
                "status_code": response.status_code
            }
        except Exception as e:
            return {"success": False, "data": str(e), "status_code": 500}
    
    def ask_question(self, question: str) -> Dict[str, Any]:
        """Ask a question about the database"""
        url = f"{self.base_url}/llm-chat/ask"
        data = {"question": question}
        try:
            response = requests.post(url, json=data, headers=self.get_headers())
            return {
                "success": response.status_code == 200,
                "data": response.json() if response.status_code == 200 else response.text,
                "status_code": response.status_code
            }
        except Exception as e:
            return {"success": False, "data": str(e), "status_code": 500}

# Initialize API client
api_client = APIClient()

def format_database_info(data: Dict[str, Any]) -> str:
    """Format database information for display"""
    if not data.get("databases"):
        return "No database connections found."
    
    result = []
    for db in data["databases"]:
        status_emoji = "🟢" if db.get("connection_status") == "connected" else "🔴"
        result.append(f"{status_emoji} **{db.get('name', 'Unknown')}**")
        result.append(f"   Host: {db.get('db_host', 'Unknown')}:{db.get('db_port', 'Unknown')}")
        result.append(f"   Database: {db.get('db_name', 'Unknown')}")
        result.append(f"   Status: {db.get('connection_status', 'Unknown')}")
        result.append(f"   Tables: {db.get('table_count', 0)}")
        if db.get("error"):
            result.append(f"   Error: {db['error']}")
        result.append("")
    
    return "\n".join(result)

def format_chat_response(data: Dict[str, Any]) -> str:
    """Format chat response for display"""
    if not data.get("answer"):
        return "No response received."
    
    result = [f"**Answer:** {data['answer']}"]
    
    if data.get("sql_used"):
        result.append(f"\n**SQL Query:**\n```sql\n{data['sql_used']}\n```")
    
    if data.get("data"):
        result.append(f"\n**Data ({len(data['data'])} rows):**")
        if data['data']:
            # Show first few rows as example
            sample_data = data['data'][:3]
            for i, row in enumerate(sample_data, 1):
                result.append(f"Row {i}: {row}")
            if len(data['data']) > 3:
                result.append(f"... and {len(data['data']) - 3} more rows")
    
    if data.get("suggestion"):
        result.append(f"\n**Suggestion:** {data['suggestion']}")
    
    if data.get("error"):
        result.append(f"\n**Error:** {data['error']}")
    
    return "\n".join(result)

# Gradio Interface Functions
def register_user(name, email, password):
    """Register a new user"""
    result = api_client.register_user(name, email, password)
    if result["success"]:
        return f"✅ User registered successfully!\nUser ID: {result['data'].get('id', 'N/A')}"
    else:
        return f"❌ Registration failed: {result['data']}"

def login_user(email, password):
    """Login user"""
    result = api_client.login_user(email, password)
    if result["success"]:
        user_info = api_client.get_user_info()
        if user_info["success"]:
            return f"✅ Login successful!\nWelcome, {user_info['data']['name']} ({user_info['data']['email']})"
        else:
            return f"✅ Login successful, but couldn't fetch user info: {user_info['data']}"
    else:
        return f"❌ Login failed: {result['data']}"

def get_databases():
    """Get user's database connections"""
    result = api_client.get_database_connections()
    if result["success"]:
        return format_database_info(result["data"])
    else:
        return f"❌ Failed to get databases: {result['data']}"

def add_database(name, host, port, dbname, db_user, db_password, db_owner_username):
    """Add a new database connection"""
    try:
        port = int(port)
    except ValueError:
        return "❌ Port must be a number"
    
    result = api_client.add_database_connection(name, host, port, dbname, db_user, db_password, db_owner_username)
    if result["success"]:
        return f"✅ Database connection added successfully!\nConnection ID: {result['data'].get('id', 'N/A')}"
    else:
        return f"❌ Failed to add database: {result['data']}"

def get_database_summary():
    """Get database summary and sample questions"""
    result = api_client.get_database_summary()
    if result["success"]:
        data = result["data"]
        summary = f"**Database Summary:**\n"
        summary += f"Total databases: {len(data.get('databases', []))}\n"
        summary += f"Total tables: {data.get('total_tables', 0)}\n\n"
        
        if data.get("sample_questions"):
            summary += "**Sample Questions You Can Ask:**\n"
            for i, question in enumerate(data["sample_questions"], 1):
                summary += f"{i}. {question}\n"
        
        return summary
    else:
        return f"❌ Failed to get summary: {result['data']}"

def ask_question(question):
    """Ask a question about the database"""
    if not question.strip():
        return "Please enter a question."
    
    result = api_client.ask_question(question)
    if result["success"]:
        return format_chat_response(result["data"])
    else:
        return f"❌ Failed to get answer: {result['data']}"

# Create Gradio Interface
with gr.Blocks(title="API Connection Manager", theme=gr.themes.Soft()) as demo:
    gr.Markdown("# 🔗 API Connection Manager")
    gr.Markdown("Manage your database connections and chat with your data using natural language!")
    
    with gr.Tabs():
        # Authentication Tab
        with gr.TabItem("🔐 Authentication"):
            gr.Markdown("### Register or Login")
            
            with gr.Row():
                with gr.Column():
                    gr.Markdown("#### Register New User")
                    reg_name = gr.Textbox(label="Name", placeholder="Enter your name")
                    reg_email = gr.Textbox(label="Email", placeholder="Enter your email")
                    reg_password = gr.Textbox(label="Password", type="password", placeholder="Enter password")
                    reg_button = gr.Button("Register", variant="primary")
                    reg_output = gr.Textbox(label="Registration Result", interactive=False)
                
                with gr.Column():
                    gr.Markdown("#### Login")
                    login_email = gr.Textbox(label="Email", placeholder="Enter your email")
                    login_password = gr.Textbox(label="Password", type="password", placeholder="Enter password")
                    login_button = gr.Button("Login", variant="primary")
                    login_output = gr.Textbox(label="Login Result", interactive=False)
            
            reg_button.click(register_user, [reg_name, reg_email, reg_password], reg_output)
            login_button.click(login_user, [login_email, login_password], login_output)
        
        # Database Management Tab
        with gr.TabItem("🗄️ Database Management"):
            gr.Markdown("### Manage Your Database Connections")
            
            with gr.Row():
                with gr.Column():
                    gr.Markdown("#### Add New Database Connection")
                    db_name = gr.Textbox(label="Connection Name", placeholder="My Database")
                    db_host = gr.Textbox(label="Host", placeholder="localhost", value="localhost")
                    db_port = gr.Textbox(label="Port", placeholder="5432", value="5432")
                    db_database = gr.Textbox(label="Database Name", placeholder="mydb")
                    db_user = gr.Textbox(label="Username", placeholder="postgres")
                    db_password = gr.Textbox(label="Password", type="password", placeholder="password")
                    db_owner = gr.Textbox(label="Owner Username (optional)", placeholder="postgres")
                    add_db_button = gr.Button("Add Database", variant="primary")
                    add_db_output = gr.Textbox(label="Add Result", interactive=False)
                
                with gr.Column():
                    gr.Markdown("#### Your Database Connections")
                    refresh_button = gr.Button("🔄 Refresh", variant="secondary")
                    databases_output = gr.Markdown(label="Database List")
            
            add_db_button.click(add_database, [db_name, db_host, db_port, db_database, db_user, db_password, db_owner], add_db_output)
            refresh_button.click(get_databases, [], databases_output)
        
        # Chat Tab
        with gr.TabItem("💬 Chat with Your Data"):
            gr.Markdown("### Ask Questions About Your Data")
            
            with gr.Row():
                with gr.Column():
                    gr.Markdown("#### Database Summary")
                    summary_button = gr.Button("📊 Get Summary", variant="secondary")
                    summary_output = gr.Markdown(label="Summary")
                
                with gr.Column():
                    gr.Markdown("#### Ask a Question")
                    question_input = gr.Textbox(
                        label="Your Question", 
                        placeholder="How many users do we have?",
                        lines=3
                    )
                    ask_button = gr.Button("Ask Question", variant="primary")
                    chat_output = gr.Markdown(label="Answer")
            
            summary_button.click(get_database_summary, [], summary_output)
            ask_button.click(ask_question, [question_input], chat_output)

# Launch the app
if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=7860, share=False) 