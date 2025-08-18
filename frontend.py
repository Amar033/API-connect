# # app.py
# import streamlit as st
# import requests
# import pandas as pd
# from typing import Optional, Dict, Any, List

# API_BASE = "http://localhost:8000"  # <-- change if your FastAPI runs elsewhere

# st.set_page_config(page_title="DataChat AI", layout="wide")

# # -------------------------
# # Session state defaults
# # -------------------------
# if "access_token" not in st.session_state:
#     st.session_state.access_token: Optional[str] = None
# if "user" not in st.session_state:
#     st.session_state.user: Optional[Dict[str, Any]] = None
# if "messages" not in st.session_state:
#     st.session_state.messages: List[Dict[str, Any]] = []
# if "credentials" not in st.session_state:
#     st.session_state.credentials = None
# if "summary" not in st.session_state:
#     st.session_state.summary = None


# # -------------------------
# # Helpers
# # -------------------------
# def auth_headers():
#     if st.session_state.access_token:
#         return {"Authorization": f"Bearer {st.session_state.access_token}"}
#     return {}

# def api_get(path: str, params: dict = None) -> Optional[requests.Response]:
#     try:
#         resp = requests.get(f"{API_BASE}{path}", headers=auth_headers(), params=params, timeout=15)
#         return resp
#     except Exception as e:
#         st.error(f"Network error: {e}")
#         return None

# def api_post(path: str, json: dict = None, data: dict = None) -> Optional[requests.Response]:
#     try:
#         if data is not None:
#             resp = requests.post(f"{API_BASE}{path}", data=data, headers=auth_headers(), timeout=15)
#         else:
#             resp = requests.post(f"{API_BASE}{path}", json=json, headers=auth_headers(), timeout=15)
#         return resp
#     except Exception as e:
#         st.error(f"Network error: {e}")
#         return None

# def api_delete(path: str) -> Optional[requests.Response]:
#     try:
#         resp = requests.delete(f"{API_BASE}{path}", headers=auth_headers(), timeout=15)
#         return resp
#     except Exception as e:
#         st.error(f"Network error: {e}")
#         return None

# # -------------------------
# # Auth functions
# # -------------------------
# def register_user(name: str, email: str, password: str):
#     payload = {"name": name, "email": email, "password": password}
#     resp = api_post("/users/", json=payload)
#     if resp is None:
#         return
#     if resp.status_code == 201:
#         st.success("Account created. Please sign in.")
#     else:
#         try:
#             st.error(resp.json().get("detail", resp.text))
#         except Exception:
#             st.error(resp.text)

# def login_user(email: str, password: str):
#     # OAuth2PasswordRequestForm expects form-encoded data
#     data = {"username": email, "password": password}
#     try:
#         resp = requests.post(f"{API_BASE}/token", data=data, headers={"Content-Type": "application/x-www-form-urlencoded"}, timeout=15)
#     except Exception as e:
#         st.error(f"Network error: {e}")
#         return

#     if resp.status_code == 200:
#         token = resp.json().get("access_token")
#         if not token:
#             st.error("Login response missing access_token")
#             return
#         st.session_state.access_token = token
#         # fetch user and connection info
#         fetch_user()
#         fetch_credentials()
#         fetch_summary()
#         st.rerun()
#     else:
#         try:
#             st.error(resp.json().get("detail", resp.text))
#         except Exception:
#             st.error(resp.text)

# def logout():
#     st.session_state.access_token = None
#     st.session_state.user = None
#     st.session_state.messages = []
#     st.session_state.credentials = None
#     st.session_state.summary = None
#     st.rerun()

# # -------------------------
# # Fetch / utility functions
# # -------------------------
# def fetch_user():
#     resp = api_get("/me")
#     if not resp:
#         return
#     if resp.status_code == 200:
#         st.session_state.user = resp.json()
#     else:
#         # token probably invalid
#         st.session_state.user = None

# def fetch_credentials():
#     """GET /db-connections returning the stored credentials (with id)."""
#     resp = api_get("/db-connections")
#     if not resp:
#         st.session_state.credentials = None
#         return
#     if resp.status_code == 200:
#         try:
#             st.session_state.credentials = resp.json()
#         except Exception:
#             st.session_state.credentials = None
#     else:
#         st.session_state.credentials = None

# def fetch_summary():
#     """GET /llm-chat/summary which returns status/table counts (may not include ids)."""
#     resp = api_get("/llm-chat/summary")
#     if not resp:
#         st.session_state.summary = None
#         return
#     if resp.status_code == 200:
#         try:
#             st.session_state.summary = resp.json()
#         except Exception:
#             st.session_state.summary = None
#     else:
#         st.session_state.summary = None

# def add_db_connection(name, host, port, dbname, db_user, db_password, owner_username=None):
#     payload = {
#         "name": name,
#         "host": host,
#         "port": int(port),
#         "dbname": dbname,
#         "db_user": db_user,
#         "db_password": db_password,
#         "db_owner_username": owner_username or db_user
#     }
#     resp = api_post("/db-connections", json=payload)
#     if resp is None:
#         return
#     if resp.status_code in (200, 201):
#         st.success("Database connection added.")
#         fetch_credentials()
#         fetch_summary()
#         st.rerun()
#     else:
#         try:
#             st.error(resp.json().get("detail", resp.text))
#         except Exception:
#             st.error(resp.text)

# def delete_db_connection(connection_id: str):
#     resp = api_delete(f"/db-connections/{connection_id}")
#     if resp is None:
#         return
#     if resp.status_code in (200, 204):
#         st.success("Deleted connection.")
#         fetch_credentials()
#         fetch_summary()
#         st.rerun()
#     else:
#         try:
#             st.error(resp.json().get("detail", resp.text))
#         except Exception:
#             st.error(resp.text)

# def ask_llm(question: str) -> Optional[Dict[str, Any]]:
#     resp = api_post("/llm-chat/ask", json={"question": question})
#     if resp is None:
#         return None
#     if resp.status_code == 200:
#         try:
#             return resp.json()
#         except Exception:
#             st.error("Invalid response from /llm-chat/ask")
#             return None
#     else:
#         try:
#             st.error(resp.json().get("detail", resp.text))
#         except Exception:
#             st.error(resp.text)
#         return None

# # -------------------------
# # UI: Sidebar (user + DB list + add/delete)
# # -------------------------
# def render_sidebar():
#     with st.sidebar:
#         st.markdown("<h3 style='margin-bottom:6px;'>Account</h3>", unsafe_allow_html=True)
#         if st.session_state.user:
#             st.markdown(f"**{st.session_state.user.get('name','-')}**")
#             st.caption(st.session_state.user.get("email", ""))
#         else:
#             st.markdown("_Not signed in_")

#         st.markdown("---")

#         st.markdown("<h4 style='margin:6px 0 4px 0;'>Connections</h4>", unsafe_allow_html=True)

#         # Prefer to show credentials (they include id). Merge summary data by dbname/host if available.
#         creds = st.session_state.credentials
#         summary = st.session_state.summary

#         # Build a simple lookup from summary by (host, database) or by name
#         summary_lookup = {}
#         if summary and isinstance(summary, dict) and "databases" in summary:
#             for item in summary["databases"]:
#                 key = (item.get("host"), item.get("database"), item.get("name"))
#                 summary_lookup[key] = item

#         if creds and isinstance(creds, list) and len(creds) > 0:
#             for cred in creds:
#                 # cred fields vary by your model: using common names used earlier
#                 cid = str(cred.get("id") or cred.get("uuid") or cred.get("connection_id") or "")
#                 cname = cred.get("name") or cred.get("db_name") or cred.get("dbname") or "Unnamed"
#                 chost = cred.get("host") or cred.get("db_host")
#                 cport = cred.get("port") or cred.get("db_port")
#                 cdbname = cred.get("dbname") or cred.get("db_name") or cred.get("database")
#                 # find matching summary
#                 s = summary_lookup.get((chost, cdbname, cname)) or summary_lookup.get((chost, cdbname, None))
#                 # Card
#                 st.markdown(
#                     f"""
#                     <div style="
#                         border: 1px solid rgba(255,255,255,0.06);
#                         background: linear-gradient(180deg, rgba(255,255,255,0.02), rgba(255,255,255,0.01));
#                         padding:10px; border-radius:8px; margin-bottom:8px;">
#                         <div style="font-weight:600;">{cname}</div>
#                         <div style="font-size:12px; color: #bfc7d6;">{chost}:{cport} — {cdbname}</div>
#                     """,
#                     unsafe_allow_html=True
#                 )
#                 # status & tables from summary if available
#                 if s:
#                     status = s.get("status", "-")
#                     tables = s.get("table_count", "-")
#                     st.markdown(f"<div style='margin-top:6px; font-size:13px;'>Status: {status} &nbsp;&nbsp; Tables: {tables}</div>", unsafe_allow_html=True)
#                 st.markdown("</div>", unsafe_allow_html=True)

#                 # delete button under each card
#                 if cid:
#                     if st.button("Delete", key=f"delete_{cid}", help=f"Delete {cname}"):
#                         delete_db_connection(cid)
#                 else:
#                     # If no id available (shouldn't happen if /db-connections returns ids), show disabled hint
#                     st.caption("No id available for deletion. Ensure /db-connections returns id.")

#         else:
#             st.info("No database connections found.")

#         st.markdown("---")
#         st.markdown("<h4 style='margin:6px 0 4px 0;'>Add Connection</h4>", unsafe_allow_html=True)
#         with st.expander("add_conn_form"):
#             add_name = st.text_input("Connection name", key="add_name")
#             add_host = st.text_input("Host", key="add_host")
#             add_port = st.number_input("Port", value=5432, min_value=1, max_value=65535, key="add_port")
#             add_dbname = st.text_input("Database name", key="add_dbname")
#             add_user = st.text_input("Database user", key="add_user")
#             add_pass = st.text_input("Database password", type="password", key="add_pass")
#             add_owner = st.text_input("Owner username (optional)", key="add_owner")
#             # submitted = st.form_submit_button("Connect")
#             if st.button("Add connection"):
#                 add_db_connection(add_name, add_host, add_port, add_dbname, add_user, add_pass, add_owner)
#             # if submitted:
#             #     if not (add_name and add_host and add_dbname and add_user and add_pass):
#             #         st.error("Please fill required fields: name, host, database, user, password")
#             #     else:
#             #         add_db_connection(add_name, add_host, add_port, add_dbname, add_user, add_pass, add_owner)

        
#         st.markdown("---")
#         if st.button("Refresh connections", key="refresh_connections"):
#             fetch_credentials()
#             fetch_summary()
#             st.rerun()
#         st.markdown("<br>", unsafe_allow_html=True)
#         if st.button("Sign out", key="signout_btn"):
#             logout()


# # -------------------------
# # UI: Login / Register or Main
# # -------------------------
# def login_register_page():
#     st.title("DataChat AI — Sign in")
#     tabs = st.tabs(["Sign in", "Register"])
#     with tabs[0]:
#         st.subheader("Sign in")
#         le = st.text_input("Email", key="login_email", label_visibility="visible")
#         lp = st.text_input("Password", type="password", key="login_password", label_visibility="visible")
#         if st.button("Sign in", key="login_submit"):
#             if not (le and lp):
#                 st.error("Enter email and password")
#             else:
#                 login_user(le, lp)

#     with tabs[1]:
#         st.subheader("Create account")
#         rn = st.text_input("Full name", key="reg_name", label_visibility="visible")
#         re = st.text_input("Email", key="reg_email", label_visibility="visible")
#         rp = st.text_input("Password", type="password", key="reg_password", label_visibility="visible")
#         if st.button("Register", key="reg_submit"):
#             if not (rn and re and rp):
#                 st.error("Fill all fields")
#             else:
#                 register_user(rn, re, rp)


# def main_chat_page():
#     st.title("Natural Language Database Chat")
#     # top quick info
#     if st.session_state.summary and isinstance(st.session_state.summary, dict):
#         total_tables = st.session_state.summary.get("total_tables", "-")
#         st.caption(f"Total tables (all connections): {total_tables}")

#     # Render chat history using st.chat_message
#     for msg in st.session_state.messages:
#         role = msg.get("role", "assistant")  # 'user' or 'assistant'
#         content = msg.get("content", "")
#         sql = msg.get("sql")
#         data = msg.get("data")
#         with st.chat_message(role):
#             # message text
#             st.write(content)
#             # SQL used
#             if sql:
#                 with st.expander("SQL used"):
#                     st.code(sql, language="sql")
#             # tabular data
#             if data and isinstance(data, list) and len(data) > 0:
#                 try:
#                     df = pd.DataFrame(data)
#                     st.dataframe(df)
#                 except Exception:
#                     st.write(data)

#     # Chat input
#     prompt = st.chat_input("Ask something about your databases...")
#     if prompt:
#         # append user message
#         st.session_state.messages.append({"role": "user", "content": prompt})
#         # render immediate user bubble
#         with st.chat_message("user"):
#             st.write(prompt)

#         # call LLM API
#         res = ask_llm(prompt)
#         if res:
#             answer = res.get("answer", res.get("message", "No answer"))
#             sql_used = res.get("sql_used") or res.get("sql")
#             data = res.get("data")
#             suggestion = res.get("suggestion")
#             # store assistant msg
#             st.session_state.messages.append({
#                 "role": "assistant",
#                 "content": answer,
#                 "sql": sql_used,
#                 "data": data
#             })
#             # display assistant bubble
#             with st.chat_message("assistant"):
#                 st.write(answer)
#                 if sql_used:
#                     with st.expander("SQL used"):
#                         st.code(sql_used, language="sql")
#                 if data and isinstance(data, list) and len(data) > 0:
#                     try:
#                         df = pd.DataFrame(data)
#                         st.dataframe(df)
#                     except Exception:
#                         st.write(data)
#                 if suggestion:
#                     st.info(suggestion)
#         else:
#             st.session_state.messages.append({
#                 "role": "assistant",
#                 "content": "Error: no response from server."
#             })
#             st.error("Failed to get a response from the API.")

# # -------------------------
# # App entry
# # -------------------------
# # Render sidebar always so user can login/register or manage connections after auth
# render_sidebar()

# if not st.session_state.access_token:
#     login_register_page()
# else:
#     # ensure we have current user & summaries
#     if not st.session_state.user:
#         fetch_user()
#     if st.session_state.credentials is None:
#         fetch_credentials()
#     if st.session_state.summary is None:
#         fetch_summary()
#     main_chat_page()




# app.py - Enhanced with async support
import streamlit as st
import requests
import pandas as pd
from typing import Optional, Dict, Any, List
import time
import threading

API_BASE = "http://localhost:8000"  # <-- change if your FastAPI runs elsewhere

st.set_page_config(page_title="DataChat AI", layout="wide")

# -------------------------
# Session state defaults (UNCHANGED)
# -------------------------
if "access_token" not in st.session_state:
    st.session_state.access_token: Optional[str] = None
if "user" not in st.session_state:
    st.session_state.user: Optional[Dict[str, Any]] = None
if "messages" not in st.session_state:
    st.session_state.messages: List[Dict[str, Any]] = []
if "credentials" not in st.session_state:
    st.session_state.credentials = None
if "summary" not in st.session_state:
    st.session_state.summary = None

# NEW: Async task management
if "active_tasks" not in st.session_state:
    st.session_state.active_tasks: Dict[str, Dict] = {}
if "processing_mode" not in st.session_state:
    st.session_state.processing_mode = "sync"  # "sync", "async", "stream"


# -------------------------
# Helpers (UNCHANGED)
# -------------------------
def auth_headers():
    if st.session_state.access_token:
        return {"Authorization": f"Bearer {st.session_state.access_token}"}
    return {}

def api_get(path: str, params: dict = None) -> Optional[requests.Response]:
    try:
        resp = requests.get(f"{API_BASE}{path}", headers=auth_headers(), params=params, timeout=15)
        return resp
    except Exception as e:
        st.error(f"Network error: {e}")
        return None

def api_post(path: str, json: dict = None, data: dict = None) -> Optional[requests.Response]:
    try:
        if data is not None:
            resp = requests.post(f"{API_BASE}{path}", data=data, headers=auth_headers(), timeout=15)
        else:
            resp = requests.post(f"{API_BASE}{path}", json=json, headers=auth_headers(), timeout=15)
        return resp
    except Exception as e:
        st.error(f"Network error: {e}")
        return None

def api_delete(path: str) -> Optional[requests.Response]:
    try:
        resp = requests.delete(f"{API_BASE}{path}", headers=auth_headers(), timeout=15)
        return resp
    except Exception as e:
        st.error(f"Network error: {e}")
        return None

# -------------------------
# Auth functions (UNCHANGED)
# -------------------------
def register_user(name: str, email: str, password: str):
    payload = {"name": name, "email": email, "password": password}
    resp = api_post("/users/", json=payload)
    if resp is None:
        return
    if resp.status_code == 201:
        st.success("Account created. Please sign in.")
    else:
        try:
            st.error(resp.json().get("detail", resp.text))
        except Exception:
            st.error(resp.text)

def login_user(email: str, password: str):
    data = {"username": email, "password": password}
    try:
        resp = requests.post(f"{API_BASE}/token", data=data, headers={"Content-Type": "application/x-www-form-urlencoded"}, timeout=15)
    except Exception as e:
        st.error(f"Network error: {e}")
        return

    if resp.status_code == 200:
        token = resp.json().get("access_token")
        if not token:
            st.error("Login response missing access_token")
            return
        st.session_state.access_token = token
        fetch_user()
        fetch_credentials()
        fetch_summary()
        st.rerun()
    else:
        try:
            st.error(resp.json().get("detail", resp.text))
        except Exception:
            st.error(resp.text)

def logout():
    st.session_state.access_token = None
    st.session_state.user = None
    st.session_state.messages = []
    st.session_state.credentials = None
    st.session_state.summary = None
    st.session_state.active_tasks = {}
    st.rerun()

# -------------------------
# Fetch functions (UNCHANGED)
# -------------------------
def fetch_user():
    resp = api_get("/me")
    if not resp:
        return
    if resp.status_code == 200:
        st.session_state.user = resp.json()
    else:
        st.session_state.user = None

def fetch_credentials():
    resp = api_get("/db-connections")
    if not resp:
        st.session_state.credentials = None
        return
    if resp.status_code == 200:
        try:
            st.session_state.credentials = resp.json()
        except Exception:
            st.session_state.credentials = None
    else:
        st.session_state.credentials = None

def fetch_summary():
    resp = api_get("/llm-chat/summary")
    if not resp:
        st.session_state.summary = None
        return
    if resp.status_code == 200:
        try:
            st.session_state.summary = resp.json()
        except Exception:
            st.session_state.summary = None
    else:
        st.session_state.summary = None

def add_db_connection(name, host, port, dbname, db_user, db_password, owner_username=None):
    payload = {
        "name": name,
        "host": host,
        "port": int(port),
        "dbname": dbname,
        "db_user": db_user,
        "db_password": db_password,
        "db_owner_username": owner_username or db_user
    }
    resp = api_post("/db-connections", json=payload)
    if resp is None:
        return
    if resp.status_code in (200, 201):
        st.success("Database connection added.")
        fetch_credentials()
        fetch_summary()
        st.rerun()
    else:
        try:
            st.error(resp.json().get("detail", resp.text))
        except Exception:
            st.error(resp.text)

def delete_db_connection(connection_id: str):
    resp = api_delete(f"/db-connections/{connection_id}")
    if resp is None:
        return
    if resp.status_code in (200, 204):
        st.success("Deleted connection.")
        fetch_credentials()
        fetch_summary()
        st.rerun()
    else:
        try:
            st.error(resp.json().get("detail", resp.text))
        except Exception:
            st.error(resp.text)

# -------------------------
# NEW: Async LLM functions
# -------------------------
def ask_llm_sync(question: str) -> Optional[Dict[str, Any]]:
    """Your original sync function - unchanged"""
    resp = api_post("/llm-chat/ask", json={"question": question})
    if resp is None:
        return None
    if resp.status_code == 200:
        try:
            return resp.json()
        except Exception:
            st.error("Invalid response from /llm-chat/ask")
            return None
    else:
        try:
            st.error(resp.json().get("detail", resp.text))
        except Exception:
            st.error(resp.text)
        return None

def ask_llm_async(question: str) -> Optional[str]:
    """Submit question for async processing, returns task_id"""
    resp = api_post("/llm-chat/ask-async", json={"question": question, "timeout_seconds": 300})
    if resp is None:
        return None
    if resp.status_code == 200:
        try:
            result = resp.json()
            task_id = result.get("task_id")
            if task_id:
                # Store task info in session state
                st.session_state.active_tasks[task_id] = {
                    "question": question,
                    "status": "pending",
                    "submitted_at": time.time(),
                    "result": None
                }
            return task_id
        except Exception:
            st.error("Invalid response from /llm-chat/ask-async")
            return None
    else:
        try:
            st.error(resp.json().get("detail", resp.text))
        except Exception:
            st.error(resp.text)
        return None

def check_task_status(task_id: str) -> Optional[Dict[str, Any]]:
    """Check status of an async task"""
    resp = api_get(f"/llm-chat/task/{task_id}")
    if resp is None:
        return None
    if resp.status_code == 200:
        try:
            return resp.json()
        except Exception:
            return None
    else:
        return None

def poll_active_tasks():
    """Poll all active tasks and update their status"""
    tasks_to_remove = []
    
    for task_id, task_info in st.session_state.active_tasks.items():
        if task_info["status"] in ["completed", "failed", "timeout"]:
            continue  # Skip already finished tasks
            
        status_data = check_task_status(task_id)
        if status_data:
            st.session_state.active_tasks[task_id].update({
                "status": status_data.get("status", "unknown"),
                "progress": status_data.get("progress"),
                "result": status_data.get("result"),
                "error": status_data.get("error")
            })
            
            # If task completed, add to chat messages
            if (status_data.get("status") == "completed" and 
                status_data.get("result") and 
                "added_to_chat" not in task_info):
                
                result = status_data["result"]
                answer = result.get("answer", "Task completed")
                sql_used = result.get("sql_used")
                data = result.get("data")
                suggestion = result.get("suggestion")
                
                # Add to chat messages
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": answer,
                    "sql": sql_used,
                    "data": data,
                    "async_task": True,
                    "task_id": task_id
                })
                
                # Mark as added to avoid duplicates
                st.session_state.active_tasks[task_id]["added_to_chat"] = True
                
                if suggestion:
                    st.info(f"💡 Suggestion: {suggestion}")
        
        # Remove old tasks (older than 1 hour)
        if time.time() - task_info["submitted_at"] > 3600:
            tasks_to_remove.append(task_id)
    
    # Clean up old tasks
    for task_id in tasks_to_remove:
        del st.session_state.active_tasks[task_id]

# -------------------------
# UI: Sidebar (Enhanced with async task status)
# -------------------------
def render_sidebar():
    with st.sidebar:
        st.markdown("<h3 style='margin-bottom:6px;'>Account</h3>", unsafe_allow_html=True)
        if st.session_state.user:
            st.markdown(f"**{st.session_state.user.get('name','-')}**")
            st.caption(st.session_state.user.get("email", ""))
        else:
            st.markdown("_Not signed in_")

        st.markdown("---")

        # NEW: Processing Mode Selection
        st.markdown("<h4 style='margin:6px 0 4px 0;'>Processing Mode</h4>", unsafe_allow_html=True)
        mode = st.selectbox(
            "Choose processing mode:",
            ["sync", "async"],
            index=0 if st.session_state.processing_mode == "sync" else 1,
            format_func=lambda x: {
                "sync": "🚀 Sync (Fast, may timeout)",
                "async": "⏳ Async (Survives timeouts)"
            }[x]
        )
        st.session_state.processing_mode = mode

        if mode == "async":
            st.info("🔄 Questions will be processed in background. Results appear when ready!")

        # NEW: Active Tasks Status
        if st.session_state.active_tasks:
            st.markdown("---")
            st.markdown("<h4 style='margin:6px 0 4px 0;'>Active Tasks</h4>", unsafe_allow_html=True)
            
            for task_id, task_info in st.session_state.active_tasks.items():
                status = task_info.get("status", "unknown")
                question = task_info.get("question", "")[:40] + "..."
                
                status_emoji = {
                    "pending": "⏳",
                    "processing": "🔄",
                    "completed": "✅",
                    "failed": "❌",
                    "timeout": "⏰"
                }.get(status, "❓")
                
                st.markdown(f"**{status_emoji} {status.title()}**")
                st.caption(question)
                
                if task_info.get("progress"):
                    st.caption(f"Progress: {task_info['progress']}")
                
                if status in ["failed", "timeout"] and task_info.get("error"):
                    st.error(f"Error: {task_info['error']}")

        st.markdown("---")

        # Database connections (UNCHANGED)
        st.markdown("<h4 style='margin:6px 0 4px 0;'>Connections</h4>", unsafe_allow_html=True)

        creds = st.session_state.credentials
        summary = st.session_state.summary

        summary_lookup = {}
        if summary and isinstance(summary, dict) and "databases" in summary:
            for item in summary["databases"]:
                key = (item.get("host"), item.get("database"), item.get("name"))
                summary_lookup[key] = item

        if creds and isinstance(creds, list) and len(creds) > 0:
            for cred in creds:
                cid = str(cred.get("id") or cred.get("uuid") or cred.get("connection_id") or "")
                cname = cred.get("name") or cred.get("db_name") or cred.get("dbname") or "Unnamed"
                chost = cred.get("host") or cred.get("db_host")
                cport = cred.get("port") or cred.get("db_port")
                cdbname = cred.get("dbname") or cred.get("db_name") or cred.get("database")
                s = summary_lookup.get((chost, cdbname, cname)) or summary_lookup.get((chost, cdbname, None))
                
                st.markdown(
                    f"""
                    <div style="
                        border: 1px solid rgba(255,255,255,0.06);
                        background: linear-gradient(180deg, rgba(255,255,255,0.02), rgba(255,255,255,0.01));
                        padding:10px; border-radius:8px; margin-bottom:8px;">
                        <div style="font-weight:600;">{cname}</div>
                        <div style="font-size:12px; color: #bfc7d6;">{chost}:{cport} — {cdbname}</div>
                    """,
                    unsafe_allow_html=True
                )
                if s:
                    status = s.get("status", "-")
                    tables = s.get("table_count", "-")
                    st.markdown(f"<div style='margin-top:6px; font-size:13px;'>Status: {status} &nbsp;&nbsp; Tables: {tables}</div>", unsafe_allow_html=True)
                st.markdown("</div>", unsafe_allow_html=True)

                if cid:
                    if st.button("Delete", key=f"delete_{cid}", help=f"Delete {cname}"):
                        delete_db_connection(cid)
                else:
                    st.caption("No id available for deletion. Ensure /db-connections returns id.")

        else:
            st.info("No database connections found.")

        st.markdown("---")
        st.markdown("<h4 style='margin:6px 0 4px 0;'>Add Connection</h4>", unsafe_allow_html=True)
        with st.expander("add_conn_form"):
            add_name = st.text_input("Connection name", key="add_name")
            add_host = st.text_input("Host", key="add_host")
            add_port = st.number_input("Port", value=5432, min_value=1, max_value=65535, key="add_port")
            add_dbname = st.text_input("Database name", key="add_dbname")
            add_user = st.text_input("Database user", key="add_user")
            add_pass = st.text_input("Database password", type="password", key="add_pass")
            add_owner = st.text_input("Owner username (optional)", key="add_owner")
            
            if st.button("Add connection"):
                add_db_connection(add_name, add_host, add_port, add_dbname, add_user, add_pass, add_owner)

        st.markdown("---")
        if st.button("Refresh connections", key="refresh_connections"):
            fetch_credentials()
            fetch_summary()
            st.rerun()
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("Sign out", key="signout_btn"):
            logout()

# -------------------------
# UI: Login / Register (UNCHANGED)
# -------------------------
def login_register_page():
    st.title("DataChat AI — Sign in")
    tabs = st.tabs(["Sign in", "Register"])
    with tabs[0]:
        st.subheader("Sign in")
        le = st.text_input("Email", key="login_email", label_visibility="visible")
        lp = st.text_input("Password", type="password", key="login_password", label_visibility="visible")
        if st.button("Sign in", key="login_submit"):
            if not (le and lp):
                st.error("Enter email and password")
            else:
                login_user(le, lp)

    with tabs[1]:
        st.subheader("Create account")
        rn = st.text_input("Full name", key="reg_name", label_visibility="visible")
        re = st.text_input("Email", key="reg_email", label_visibility="visible")
        rp = st.text_input("Password", type="password", key="reg_password", label_visibility="visible")
        if st.button("Register", key="reg_submit"):
            if not (rn and re and rp):
                st.error("Fill all fields")
            else:
                register_user(rn, re, rp)

# -------------------------
# UI: Enhanced Chat Page
# -------------------------
def main_chat_page():
    st.title("Natural Language Database Chat")
    
    # Poll active tasks every time the page loads
    if st.session_state.active_tasks:
        poll_active_tasks()
    
    # Top info bar
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        if st.session_state.summary and isinstance(st.session_state.summary, dict):
            total_tables = st.session_state.summary.get("total_tables", "-")
            st.caption(f"Total tables: {total_tables}")
    
    with col2:
        if st.button("🔄 Poll Tasks", help="Check for completed async tasks"):
            poll_active_tasks()
            st.rerun()
    
    with col3:
        active_count = len([t for t in st.session_state.active_tasks.values() 
                          if t.get("status") in ["pending", "processing"]])
        if active_count > 0:
            st.caption(f"🔄 {active_count} tasks running")

    # Render chat history
    for msg in st.session_state.messages:
        role = msg.get("role", "assistant")
        content = msg.get("content", "")
        sql = msg.get("sql")
        data = msg.get("data")
        is_async = msg.get("async_task", False)
        
        with st.chat_message(role):
            if is_async:
                st.info("🔄 This response was processed asynchronously")
            
            st.write(content)
            
            if sql:
                with st.expander("SQL used"):
                    st.code(sql, language="sql")
            
            if data and isinstance(data, list) and len(data) > 0:
                try:
                    df = pd.DataFrame(data)
                    st.dataframe(df)
                except Exception:
                    st.write(data)

    # Chat input
    prompt = st.chat_input("Ask something about your databases...")
    if prompt:
        # Add user message
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        # Show user message immediately
        with st.chat_message("user"):
            st.write(prompt)

        # Process based on selected mode
        if st.session_state.processing_mode == "sync":
            # Original sync processing
            with st.chat_message("assistant"):
                with st.spinner("Processing your question..."):
                    res = ask_llm_sync(prompt)
                
                if res:
                    answer = res.get("answer", res.get("message", "No answer"))
                    sql_used = res.get("sql_used") or res.get("sql")
                    data = res.get("data")
                    suggestion = res.get("suggestion")
                    
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": answer,
                        "sql": sql_used,
                        "data": data
                    })
                    
                    st.write(answer)
                    if sql_used:
                        with st.expander("SQL used"):
                            st.code(sql_used, language="sql")
                    if data and isinstance(data, list) and len(data) > 0:
                        try:
                            df = pd.DataFrame(data)
                            st.dataframe(df)
                        except Exception:
                            st.write(data)
                    if suggestion:
                        st.info(suggestion)
                else:
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": "Error: no response from server."
                    })
                    st.error("Failed to get a response from the API.")
        
        elif st.session_state.processing_mode == "async":
            # New async processing
            with st.chat_message("assistant"):
                with st.spinner("Submitting question for background processing..."):
                    task_id = ask_llm_async(prompt)
                
                if task_id:
                    st.success(f"✅ Question submitted! Task ID: `{task_id[:8]}...`")
                    st.info("🔄 Your question is being processed in the background. The result will appear here when ready. You can continue using the app or come back later!")
                    
                    # Add a placeholder message
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": f"⏳ Processing your question in the background... (Task: {task_id[:8]}...)",
                        "task_id": task_id,
                        "async_placeholder": True
                    })
                else:
                    st.error("Failed to submit question for async processing.")

        # Auto-refresh to show completed tasks
        time.sleep(1)
        st.rerun()

# -------------------------
# App entry (UNCHANGED)
# -------------------------
render_sidebar()

if not st.session_state.access_token:
    login_register_page()
else:
    if not st.session_state.user:
        fetch_user()
    if st.session_state.credentials is None:
        fetch_credentials()
    if st.session_state.summary is None:
        fetch_summary()
    main_chat_page()