# 🔗 API Connection Manager - Gradio Interface

A simple Gradio web interface for managing your API connections and chatting with your database data using natural language.

## Features

- **🔐 Authentication**: Register new users and login to access your data
- **🗄️ Database Management**: Add, view, and manage your database connections
- **💬 Natural Language Chat**: Ask questions about your data in plain English
- **📊 Database Summary**: Get overview of your databases and suggested questions

## Setup

### 1. Install Dependencies

```bash
pip install -r gradio_requirements.txt
```

### 2. Start Your API Server

Make sure your FastAPI server is running on `http://localhost:8000`:

```bash
# In your API directory
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### 3. Run the Gradio App

```bash
python gradio_app.py
```

The Gradio interface will be available at `http://localhost:7860`

## Usage

### Authentication
1. **Register**: Create a new account with your name, email, and password
2. **Login**: Use your email and password to access your account

### Database Management
1. **Add Database**: Enter your database connection details:
   - Connection Name (e.g., "My Production DB")
   - Host (e.g., "localhost")
   - Port (e.g., "5432")
   - Database Name (e.g., "mydb")
   - Username and Password
2. **View Connections**: Click "Refresh" to see your database connections and their status

### Chat with Your Data
1. **Get Summary**: Click "Get Summary" to see an overview of your databases and sample questions
2. **Ask Questions**: Type natural language questions like:
   - "How many users do we have?"
   - "Show me the latest orders"
   - "What are the most expensive products?"
   - "Find customers with names containing 'John'"

## Example Questions

The app can handle various types of questions:
- **Count queries**: "How many records do we have?"
- **Data exploration**: "Show me some sample data"
- **Filtering**: "Find users created this month"
- **Aggregations**: "What's the total sales amount?"
- **Text search**: "Find products with 'phone' in the name"

## Configuration

You can modify the API base URL in `gradio_app.py`:

```python
API_BASE_URL = "http://localhost:8000"  # Change if your API runs on different port
```

## Troubleshooting

1. **API Connection Error**: Make sure your FastAPI server is running on port 8000
2. **Database Connection Failed**: Check your database credentials and network connectivity
3. **Authentication Issues**: Ensure you're registered and logged in before accessing features

## Features

- **User-friendly Interface**: Clean, intuitive Gradio interface
- **Real-time Status**: See connection status of your databases
- **Natural Language Processing**: Ask questions in plain English
- **SQL Transparency**: See the generated SQL queries
- **Error Handling**: Clear error messages and suggestions 