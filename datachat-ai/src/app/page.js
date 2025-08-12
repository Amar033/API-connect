// import Image from "next/image";
// import styles from "./page.module.css";

// export default function Home() {
//   return (
//     <div className={styles.page}>
//       <main className={styles.main}>
//         <Image
//           className={styles.logo}
//           src="/next.svg"
//           alt="Next.js logo"
//           width={180}
//           height={38}
//           priority
//         />
//         <ol>
//           <li>
//             Get started by editing <code>src/app/page.js</code>.
//           </li>
//           <li>Save and see your changes instantly.</li>
//         </ol>

//         <div className={styles.ctas}>
//           <a
//             className={styles.primary}
//             href="https://vercel.com/new?utm_source=create-next-app&utm_medium=appdir-template&utm_campaign=create-next-app"
//             target="_blank"
//             rel="noopener noreferrer"
//           >
//             <Image
//               className={styles.logo}
//               src="/vercel.svg"
//               alt="Vercel logomark"
//               width={20}
//               height={20}
//             />
//             Deploy now
//           </a>
//           <a
//             href="https://nextjs.org/docs?utm_source=create-next-app&utm_medium=appdir-template&utm_campaign=create-next-app"
//             target="_blank"
//             rel="noopener noreferrer"
//             className={styles.secondary}
//           >
//             Read our docs
//           </a>
//         </div>
//       </main>
//       <footer className={styles.footer}>
//         <a
//           href="https://nextjs.org/learn?utm_source=create-next-app&utm_medium=appdir-template&utm_campaign=create-next-app"
//           target="_blank"
//           rel="noopener noreferrer"
//         >
//           <Image
//             aria-hidden
//             src="/file.svg"
//             alt="File icon"
//             width={16}
//             height={16}
//           />
//           Learn
//         </a>
//         <a
//           href="https://vercel.com/templates?framework=next.js&utm_source=create-next-app&utm_medium=appdir-template&utm_campaign=create-next-app"
//           target="_blank"
//           rel="noopener noreferrer"
//         >
//           <Image
//             aria-hidden
//             src="/window.svg"
//             alt="Window icon"
//             width={16}
//             height={16}
//           />
//           Examples
//         </a>
//         <a
//           href="https://nextjs.org?utm_source=create-next-app&utm_medium=appdir-template&utm_campaign=create-next-app"
//           target="_blank"
//           rel="noopener noreferrer"
//         >
//           <Image
//             aria-hidden
//             src="/globe.svg"
//             alt="Globe icon"
//             width={16}
//             height={16}
//           />
//           Go to nextjs.org →
//         </a>
//       </footer>
//     </div>
//   );
// }


// pages/index.js - Next.js DataChat AI




"use client";
import { useState, useEffect, useRef } from 'react'
import { useRouter } from 'next/navigation';

const API_BASE = 'http://localhost:8000'

export default function DataChatApp() {
  const [user, setUser] = useState(null)
  const [token, setToken] = useState(null)
  const [messages, setMessages] = useState([])
  const [activeTasks, setActiveTasks] = useState({})
  const [connections, setConnections] = useState([])
  const [summary, setSummary] = useState(null)
  const [processingMode, setProcessingMode] = useState('async')
  const [currentQuestion, setCurrentQuestion] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [showAuth, setShowAuth] = useState(true)
  const [showConnectionManager, setShowConnectionManager] = useState(false)
  
  const eventSourceRef = useRef(null)
  const pollIntervalRef = useRef(null)
  const router = useRouter()

  // API helpers
  const apiCall = async (endpoint, options = {}) => {
    const headers = {
      ...(token && { 'Authorization': `Bearer ${token}` }),
      ...options.headers
    }
    
    // Handle form data specifically for the login endpoint
    if (options.body && options.body instanceof FormData) {
      delete headers['Content-Type'];
    } else if (options.body) {
      headers['Content-Type'] = 'application/json';
    }

    const response = await fetch(`${API_BASE}${endpoint}`, {
      ...options,
      headers
    })

    if (response.status === 401) {
      logout()
      return null
    }

    return response
  }

  // Auth functions
  const login = async (email, password) => {
    try {
      const formData = new FormData()
      formData.append('username', email)
      formData.append('password', password)
      
      const response = await apiCall('/token', {
        method: 'POST',
        body: formData
      })
      
      if (response?.ok) {
        const data = await response.json()
        setToken(data.access_token)
        localStorage.setItem('token', data.access_token)
        await fetchUserData(data.access_token)
        setShowAuth(false)
      } else {
        alert('Login failed')
      }
    } catch (error) {
      console.error('Login error:', error)
      alert('Login error: ' + error.message)
    }
  }

  const register = async (name, email, password) => {
    try {
      const response = await apiCall('/users/', {
        method: 'POST',
        body: JSON.stringify({ name, email, password })
      })
      
      if (response?.status === 201) {
        alert('Account created! Please sign in.')
      } else {
        const error = await response?.json()
        alert('Registration failed: ' + error?.detail)
      }
    } catch (error) {
      alert('Registration error: ' + error.message)
    }
  }

  const logout = () => {
    setToken(null)
    setUser(null)
    setMessages([])
    setActiveTasks({})
    setConnections([])
    setSummary(null)
    localStorage.removeItem('token')
    setShowAuth(true)
    
    if (eventSourceRef.current) {
      eventSourceRef.current.close()
    }
    if (pollIntervalRef.current) {
      clearInterval(pollIntervalRef.current)
    }
  }

  // Data fetching
  const fetchUserData = async (authToken = token) => {
    if (!authToken) return

    try {
      // Fetch user info
      const userResponse = await apiCall('/me', { headers: { 'Authorization': `Bearer ${authToken}` } })
      if (userResponse?.ok) {
        setUser(await userResponse.json())
      }

      // Fetch connections with status
      const connResponse = await apiCall('/db-connections?include_status=true', { headers: { 'Authorization': `Bearer ${authToken}` } })
      if (connResponse?.ok) {
        const data = await connResponse.json()
        setConnections(data.databases || [])
      }

      // Fetch summary
      const summaryResponse = await apiCall('/llm-chat/summary', { headers: { 'Authorization': `Bearer ${authToken}` } })
      if (summaryResponse?.ok) {
        setSummary(await summaryResponse.json())
      }
    } catch (error) {
      console.error('Error fetching data:', error)
    }
  }

  // Connection management
  const createConnection = async (connData) => {
    try {
      const response = await apiCall('/db-connections/', {
        method: 'POST',
        body: JSON.stringify(connData)
      })
      if (response?.ok) {
        alert('Connection created successfully.')
        fetchUserData()
        return true
      } else {
        const error = await response?.json()
        alert('Failed to create connection: ' + error?.detail)
        return false
      }
    } catch (error) {
      console.error('Create connection error:', error)
      return false
    }
  }

  const deleteConnection = async (connectionId) => {
    if (!confirm('Are you sure you want to delete this connection?')) {
      return
    }
    try {
      const response = await apiCall(`/db-connections/${connectionId}`, {
        method: 'DELETE'
      })
      if (response?.ok) {
        alert('Connection deleted successfully.')
        fetchUserData()
      } else {
        const error = await response?.json()
        alert('Failed to delete connection: ' + error?.detail)
      }
    } catch (error) {
      console.error('Delete connection error:', error)
    }
  }

  // Async question handling
  const submitAsyncQuestion = async (question) => {
    try {
      const response = await apiCall('/llm-chat/ask-async', {
        method: 'POST',
        body: JSON.stringify({ question, timeout_seconds: 300 })
      })

      if (response?.ok) {
        const result = await response.json()
        const taskId = result.task_id
        
        setActiveTasks(prev => ({
          ...prev,
          [taskId]: {
            question,
            status: 'pending',
            submittedAt: Date.now(),
            result: null
          }
        }))

        setMessages(prev => [...prev, 
          { role: 'user', content: question },
          { 
            role: 'assistant', 
            content: `⏳ Processing in background... (Task: ${taskId.slice(0, 8)}...)`,
            taskId,
            isPlaceholder: true
          }
        ])
      }
    } catch (error) {
      console.error('Error submitting async question:', error)
    }
  }

  // Sync question handling
  const submitSyncQuestion = async (question) => {
    try {
      setIsLoading(true)
      const response = await apiCall('/llm-chat/ask', {
        method: 'POST',
        body: JSON.stringify({ question })
      })

      if (response?.ok) {
        const result = await response.json()
        
        setMessages(prev => [...prev,
          { role: 'user', content: question },
          { 
            role: 'assistant', 
            content: result.answer,
            sql: result.sql_used,
            data: result.data,
            suggestion: result.suggestion
          }
        ])
      }
    } catch (error) {
      console.error('Error with sync question:', error)
      setMessages(prev => [...prev, { role: 'user', content: question }, { role: 'assistant', content: `❌ Error: ${error.message}` }])
    } finally {
      setIsLoading(false)
    }
  }

  // Streaming question handling
  const submitStreamQuestion = async (question) => {
    setMessages(prev => [...prev, { role: 'user', content: question }])
    
    let assistantMessage = { role: 'assistant', content: '🔄 Processing...', isStreaming: true }
    setMessages(prev => [...prev, assistantMessage])

    try {
      const response = await apiCall('/llm-chat/ask-stream', {
        method: 'POST',
        body: JSON.stringify({ question })
      })

      if (!response?.body) {
        throw new Error('Streaming not supported or API error');
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        
        const chunk = decoder.decode(value, { stream: true });
        const lines = chunk.split('\n').filter(line => line.trim());
        
        for (const line of lines) {
          try {
            const data = JSON.parse(line);
            
            setMessages(prev => prev.map((msg, idx) => {
              if (idx === prev.length - 1 && msg.isStreaming) {
                if (data.status === 'info') {
                  return { ...msg, content: `🔄 ${data.message}` };
                } else if (data.status === 'done' && data.data) {
                  return { 
                    ...msg, 
                    content: data.data.answer,
                    sql: data.data.sql_used,
                    data: data.data.data,
                    suggestion: data.data.suggestion,
                    isStreaming: false
                  };
                } else if (data.status === 'error') {
                  
                  return { ...msg, content: `❌ Error: ${data.message}`, isStreaming: false };
                }
              }
              return msg;
            }));
          } catch (e) {
            console.log('Non-JSON line:', line);
          }
        }
      }
    } catch (error) {
      console.error('Streaming error:', error);
      setMessages(prev => prev.map((msg, idx) => 
        idx === prev.length - 1 && msg.isStreaming 
          ? { ...msg, content: `❌ Streaming failed: ${error.message}`, isStreaming: false }
          : msg
      ));
    }
  };

  // Task polling
  const pollTasks = async () => {
    const tasksToPoll = Object.entries(activeTasks).filter(([_, taskInfo]) => 
      taskInfo.status === 'pending' || taskInfo.status === 'processing'
    );
    
    if (tasksToPoll.length === 0) return

    for (const [taskId, taskInfo] of tasksToPoll) {
      try {
        const response = await apiCall(`/llm-chat/task/${taskId}`)
        if (response?.ok) {
          const statusData = await response.json()
          
          setActiveTasks(prev => ({
            ...prev,
            [taskId]: {
              ...prev[taskId],
              status: statusData.status,
              progress: statusData.progress,
              result: statusData.result,
              error: statusData.error
            }
          }))

          if (statusData.status === 'completed' && statusData.result) {
            setMessages(prev => prev.map(msg => 
              msg.taskId === taskId && msg.isPlaceholder
                ? {
                    role: 'assistant',
                    content: statusData.result.answer,
                    sql: statusData.result.sql_used,
                    data: statusData.result.data,
                    suggestion: statusData.result.suggestion,
                    taskId,
                    isPlaceholder: false,
                    isAsync: true
                  }
                : msg
            ))
          }
        }
      } catch (error) {
        console.error(`Error polling task ${taskId}:`, error)
      }
    }
  }

  // Handle question submission
  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!currentQuestion.trim() || isLoading) return

    const question = currentQuestion.trim()
    setCurrentQuestion('')

    switch (processingMode) {
      case 'sync':
        await submitSyncQuestion(question)
        break
      case 'async':
        await submitAsyncQuestion(question)
        break
      case 'stream':
        await submitStreamQuestion(question)
        break
    }
  }

  // Effects
  useEffect(() => {
    const savedToken = localStorage.getItem('token')
    if (savedToken) {
      setToken(savedToken)
      fetchUserData(savedToken)
      setShowAuth(false)
    }
  }, [])

  useEffect(() => {
    if (token && Object.keys(activeTasks).length > 0) {
      pollIntervalRef.current = setInterval(pollTasks, 2000) // Poll every 2 seconds
      return () => clearInterval(pollIntervalRef.current)
    }
  }, [token, activeTasks])

  // Render auth form
  if (showAuth) {
    return (
      <div style={{
        minHeight: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)'
      }}>
        <AuthForm onLogin={login} onRegister={register} />
      </div>
    )
  }

  // Main app render
  return (
    <div style={{ display: 'flex', height: '100vh', fontFamily: 'system-ui' }}>
      {/* Sidebar */}
      <div style={{
        width: '350px',
        background: '#1a1a1a',
        color: 'white',
        padding: '20px',
        overflowY: 'auto'
      }}>
        <Sidebar 
          user={user}
          connections={connections}
          summary={summary}
          activeTasks={activeTasks}
          processingMode={processingMode}
          onProcessingModeChange={setProcessingMode}
          onLogout={logout}
          onRefresh={() => fetchUserData()}
          onManageConnections={() => setShowConnectionManager(true)}
        />
      </div>

      {/* Main chat area */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
        <ChatArea 
          messages={messages}
          currentQuestion={currentQuestion}
          onQuestionChange={setCurrentQuestion}
          onSubmit={handleSubmit}
          isLoading={isLoading}
          processingMode={processingMode}
        />
      </div>
      
      {/* Connection Manager Modal */}
      {showConnectionManager && (
        <ConnectionManager
          connections={connections}
          onCreateConnection={createConnection}
          onDeleteConnection={deleteConnection}
          onClose={() => setShowConnectionManager(false)}
        />
      )}
    </div>
  )
}

// Auth component (unchanged)
function AuthForm({ onLogin, onRegister }) {
  const [isLogin, setIsLogin] = useState(true)
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [name, setName] = useState('')

  const handleSubmit = (e) => {
    e.preventDefault()
    if (isLogin) {
      onLogin(email, password)
    } else {
      onRegister(name, email, password)
    }
  }

  return (
    <div style={{
      background: 'white',
      padding: '40px',
      borderRadius: '10px',
      boxShadow: '0 10px 25px rgba(0,0,0,0.1)',
      minWidth: '400px'
    }}>
      <h1 style={{ marginBottom: '30px', textAlign: 'center' }}>
        DataChat AI
      </h1>
      
      <div style={{ marginBottom: '20px', textAlign: 'center' }}>
        <button 
          onClick={() => setIsLogin(true)}
          style={{
            padding: '10px 20px',
            margin: '0 5px',
            border: 'none',
            borderRadius: '5px',
            background: isLogin ? '#667eea' : '#f0f0f0',
            color: isLogin ? 'white' : 'black',
            cursor: 'pointer'
          }}
        >
          Sign In
        </button>
        <button 
          onClick={() => setIsLogin(false)}
          style={{
            padding: '10px 20px',
            margin: '0 5px',
            border: 'none',
            borderRadius: '5px',
            background: !isLogin ? '#667eea' : '#f0f0f0',
            color: !isLogin ? 'white' : 'black',
            cursor: 'pointer'
          }}
        >
          Register
        </button>
      </div>

      <form onSubmit={handleSubmit}>
        {!isLogin && (
          <input
            type="text"
            placeholder="Full Name"
            value={name}
            onChange={(e) => setName(e.target.value)}
            style={{
              width: '100%',
              padding: '12px',
              margin: '10px 0',
              border: '1px solid #ddd',
              borderRadius: '5px'
            }}
            required
          />
        )}
        
        <input
          type="email"
          placeholder="Email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          style={{
            width: '100%',
            padding: '12px',
            margin: '10px 0',
            border: '1px solid #ddd',
            borderRadius: '5px'
          }}
          required
        />
        
        <input
          type="password"
          placeholder="Password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          style={{
            width: '100%',
            padding: '12px',
            margin: '10px 0',
            border: '1px solid #ddd',
            borderRadius: '5px'
          }}
          required
        />
        
        <button
          type="submit"
          style={{
            width: '100%',
            padding: '12px',
            margin: '20px 0 10px 0',
            border: 'none',
            borderRadius: '5px',
            background: '#667eea',
            color: 'white',
            fontSize: '16px',
            cursor: 'pointer'
          }}
        >
          {isLogin ? 'Sign In' : 'Register'}
        </button>
      </form>
    </div>
  )
}

// Sidebar component
function Sidebar({ user, connections, summary, activeTasks, processingMode, onProcessingModeChange, onLogout, onRefresh, onManageConnections }) {
  return (
    <div>
      <h3>Account</h3>
      {user && (
        <div style={{ margin: '10px 0' }}>
          <div><strong>{user.name}</strong></div>
          <div style={{ fontSize: '12px', color: '#bbb' }}>{user.email}</div>
        </div>
      )}
      
      <hr style={{ margin: '20px 0', borderColor: '#333' }} />
      
      <h4>Processing Mode</h4>
      <select 
        value={processingMode} 
        onChange={(e) => onProcessingModeChange(e.target.value)}
        style={{
          width: '100%',
          padding: '8px',
          margin: '10px 0',
          borderRadius: '5px',
          border: '1px solid #333',
          background: '#2a2a2a',
          color: 'white'
        }}
      >
        <option value="sync">🚀 Sync (Fast, may timeout)</option>
        <option value="async">⏳ Async (Survives timeouts)</option>
        <option value="stream">🌊 Stream (Real-time updates)</option>
      </select>
      
      {Object.keys(activeTasks).length > 0 && (
        <>
          <hr style={{ margin: '20px 0', borderColor: '#333' }} />
          <h4>Active Tasks</h4>
          {Object.entries(activeTasks).map(([taskId, task]) => (
            <div key={taskId} style={{ 
              background: '#2a2a2a', 
              padding: '10px', 
              margin: '5px 0', 
              borderRadius: '5px',
              fontSize: '12px'
            }}>
              <div>{getStatusEmoji(task.status)} {task.status}</div>
              <div style={{ color: '#bbb' }}>{task.question.slice(0, 40)}...</div>
              {task.progress && <div style={{ color: '#888' }}>{task.progress}</div>}
            </div>
          ))}
        </>
      )}
      
      <hr style={{ margin: '20px 0', borderColor: '#333' }} />
      
      <h4>Connections</h4>
      <button onClick={onManageConnections} style={{
        width: '100%',
        padding: '10px',
        marginBottom: '10px',
        border: 'none',
        borderRadius: '5px',
        background: '#444',
        color: 'white',
        cursor: 'pointer'
      }}>
        ⚙️ Manage Connections
      </button>

      {connections && connections.length > 0 ? (
        connections.map((conn) => (
          <div key={conn.id} style={{
            background: '#2a2a2a',
            padding: '10px',
            margin: '5px 0',
            borderRadius: '5px',
            fontSize: '12px'
          }}>
            <div><strong>{conn.name}</strong> ({conn.db_name})</div>
            <div style={{ color: conn.connection_status === 'connected' ? '#4CAF50' : '#F44336' }}>
              {conn.connection_status === 'connected' ? `✅ Connected (${conn.table_count} tables)` : `❌ ${conn.connection_status}`}
            </div>
          </div>
        ))
      ) : (
        <p style={{ color: '#888' }}>No connections</p>
      )}
      
      <hr style={{ margin: '20px 0', borderColor: '#333' }} />
      
      <button onClick={onRefresh} style={{
        width: '100%',
        padding: '10px',
        margin: '5px 0',
        border: 'none',
        borderRadius: '5px',
        background: '#333',
        color: 'white',
        cursor: 'pointer'
      }}>
        🔄 Refresh
      </button>
      
      <button onClick={onLogout} style={{
        width: '100%',
        padding: '10px',
        margin: '5px 0',
        border: 'none',
        borderRadius: '5px',
        background: '#dc3545',
        color: 'white',
        cursor: 'pointer'
      }}>
        Sign Out
      </button>
    </div>
  )
}

// Chat area component (unchanged)
function ChatArea({ messages, currentQuestion, onQuestionChange, onSubmit, isLoading, processingMode }) {
  const messagesEndRef = useRef(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" })
  }

  useEffect(scrollToBottom, [messages])

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      {/* Header */}
      <div style={{
        padding: '20px',
        borderBottom: '1px solid #eee',
        background: 'white'
      }}>
        <h1>Natural Language Database Chat</h1>
        <p style={{ color: '#666', margin: '5px 0 0 0' }}>
          Mode: {processingMode} | Ask questions about your databases
        </p>
      </div>
      
      {/* Messages */}
      <div style={{
        flex: 1,
        overflowY: 'auto',
        padding: '20px',
        background: '#f8f9fa'
      }}>
        {messages.map((message, idx) => (
          <MessageBubble key={idx} message={message} />
        ))}
        {isLoading && (
          <div style={{ textAlign: 'center', color: '#666' }}>
            🔄 Processing...
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>
      
      {/* Input */}
      <form onSubmit={onSubmit} style={{
        padding: '20px',
        borderTop: '1px solid #eee',
        background: 'white',
        display: 'flex',
        gap: '10px'
      }}>
        <input
          type="text"
          value={currentQuestion}
          onChange={(e) => onQuestionChange(e.target.value)}
          placeholder="Ask something about your databases..."
          style={{
            flex: 1,
            padding: '12px',
            border: '1px solid #ddd',
            borderRadius: '25px',
            fontSize: '16px'
          }}
        />
        <button
          type="submit"
          disabled={isLoading || !currentQuestion.trim()}
          style={{
            padding: '12px 24px',
            border: 'none',
            borderRadius: '25px',
            background: '#667eea',
            color: 'white',
            cursor: 'pointer',
            fontSize: '16px'
          }}
        >
          Send
        </button>
      </form>
    </div>
  )
}

// Message bubble component (unchanged)
function MessageBubble({ message }) {
  const isUser = message.role === 'user'
  
  return (
    <div style={{
      display: 'flex',
      justifyContent: isUser ? 'flex-end' : 'flex-start',
      margin: '10px 0'
    }}>
      <div style={{
        maxWidth: '70%',
        padding: '12px 16px',
        borderRadius: '18px',
        background: isUser ? '#667eea' : 'white',
        color: isUser ? 'white' : 'black',
        boxShadow: '0 1px 3px rgba(0,0,0,0.1)'
      }}>
        {message.isAsync && <div style={{ fontSize: '12px', opacity: 0.7 }}>🔄 Async Result</div>}
        
        <div>{message.content}</div>
        
        {message.sql && (
          <details style={{ marginTop: '10px' }}>
            <summary style={{ cursor: 'pointer', fontSize: '12px', opacity: 0.8 }}>
              SQL Query
            </summary>
            <pre style={{
              background: '#f1f1f1',
              padding: '8px',
              borderRadius: '4px',
              fontSize: '12px',
              overflow: 'auto',
              marginTop: '5px'
            }}>
              {message.sql}
            </pre>
          </details>
        )}
        
        {message.data && message.data.length > 0 && (
          <details style={{ marginTop: '10px' }}>
            <summary style={{ cursor: 'pointer', fontSize: '12px', opacity: 0.8 }}>
              Data ({message.data.length} rows)
            </summary>
            <div style={{ marginTop: '5px', fontSize: '12px' }}>
              <DataTable data={message.data.slice(0, 10)} />
              {message.data.length > 10 && <p>... and {message.data.length - 10} more rows</p>}
            </div>
          </details>
        )}
        
        {message.suggestion && (
          <div style={{
            marginTop: '10px',
            padding: '8px',
            background: 'rgba(255,255,255,0.1)',
            borderRadius: '8px',
            fontSize: '12px',
            opacity: 0.9
          }}>
            💡 {message.suggestion}
          </div>
        )}
      </div>
    </div>
  )
}

// Data table component (unchanged)
function DataTable({ data }) {
  if (!data || data.length === 0) return null
  
  const columns = Object.keys(data[0])
  
  return (
    <div style={{ overflowX: 'auto' }}>
      <table style={{
        width: '100%',
        borderCollapse: 'collapse',
        fontSize: '11px'
      }}>
        <thead>
          <tr style={{ background: '#f0f0f0' }}>
            {columns.map(col => (
              <th key={col} style={{
                padding: '4px 8px',
                border: '1px solid #ddd',
                textAlign: 'left'
              }}>
                {col}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {data.map((row, idx) => (
            <tr key={idx}>
              {columns.map(col => (
                <td key={col} style={{
                  padding: '4px 8px',
                  border: '1px solid #ddd'
                }}>
                  {String(row[col] || '')}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

// New Connection Manager component
function ConnectionManager({ connections, onCreateConnection, onDeleteConnection, onClose }) {
  const [name, setName] = useState('')
  const [db_owner_username, setDbOwnerUsername] = useState('')
  const [host, setHost] = useState('')
  const [port, setPort] = useState(5432)
  const [dbname, setDbname] = useState('')
  const [db_user, setDbUser] = useState('')
  const [db_password, setDbPassword] = useState('')

  const handleCreate = async (e) => {
    e.preventDefault()
    const success = await onCreateConnection({
      name, db_owner_username, host, port: Number(port), dbname, db_user, db_password
    })
    if (success) {
      setName('')
      setDbOwnerUsername('')
      setHost('')
      setPort(5432)
      setDbname('')
      setDbUser('')
      setDbPassword('')
    }
  }

  return (
    <div style={{
      position: 'fixed',
      top: 0,
      left: 0,
      width: '100%',
      height: '100%',
      background: 'rgba(0,0,0,0.5)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      zIndex: 1000
    }}>
      <div style={{
        background: 'white',
        padding: '30px',
        borderRadius: '10px',
        width: '600px',
        maxHeight: '80vh',
        overflowY: 'auto',
        position: 'relative'
      }}>
        <button onClick={onClose} style={{
          position: 'absolute',
          top: '10px',
          right: '10px',
          background: 'none',
          border: 'none',
          fontSize: '24px',
          cursor: 'pointer'
        }}>
          &times;
        </button>
        <h2 style={{ marginBottom: '20px' }}>Manage Connections</h2>

        <div style={{ maxHeight: '200px', overflowY: 'auto', marginBottom: '20px' }}>
          <h3 style={{ marginBottom: '10px' }}>Existing Connections</h3>
          {connections.length > 0 ? (
            connections.map(conn => (
              <div key={conn.id} style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                padding: '10px',
                border: '1px solid #ddd',
                borderRadius: '5px',
                marginBottom: '5px'
              }}>
                <div>
                  <strong>{conn.name}</strong> ({conn.db_name})
                  <div style={{ fontSize: '12px', color: conn.connection_status === 'connected' ? '#4CAF50' : '#F44336' }}>
                    {conn.connection_status}
                  </div>
                </div>
                <button 
                  onClick={() => onDeleteConnection(conn.id)}
                  style={{
                    background: '#dc3545',
                    color: 'white',
                    border: 'none',
                    padding: '5px 10px',
                    borderRadius: '5px',
                    cursor: 'pointer'
                  }}
                >
                  Delete
                </button>
              </div>
            ))
          ) : (
            <p>No connections found.</p>
          )}
        </div>

        <h3 style={{ marginBottom: '10px' }}>Add New Connection</h3>
        <form onSubmit={handleCreate} style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '15px' }}>
          <input
            type="text"
            placeholder="Connection Name"
            value={name}
            onChange={(e) => setName(e.target.value)}
            style={{ padding: '10px', border: '1px solid #ddd', borderRadius: '5px' }}
            required
          />
          <input
            type="text"
            placeholder="DB Owner Username (e.g., postgres)"
            value={db_owner_username}
            onChange={(e) => setDbOwnerUsername(e.target.value)}
            style={{ padding: '10px', border: '1px solid #ddd', borderRadius: '5px' }}
            required
          />
          <input
            type="text"
            placeholder="Host"
            value={host}
            onChange={(e) => setHost(e.target.value)}
            style={{ padding: '10px', border: '1px solid #ddd', borderRadius: '5px' }}
            required
          />
          <input
            type="number"
            placeholder="Port"
            value={port}
            onChange={(e) => setPort(e.target.value)}
            style={{ padding: '10px', border: '1px solid #ddd', borderRadius: '5px' }}
            required
          />
          <input
            type="text"
            placeholder="Database Name"
            value={dbname}
            onChange={(e) => setDbname(e.target.value)}
            style={{ padding: '10px', border: '1px solid #ddd', borderRadius: '5px' }}
            required
          />
          <input
            type="text"
            placeholder="Database User"
            value={db_user}
            onChange={(e) => setDbUser(e.target.value)}
            style={{ padding: '10px', border: '1px solid #ddd', borderRadius: '5px' }}
            required
          />
          <input
            type="password"
            placeholder="Database Password"
            value={db_password}
            onChange={(e) => setDbPassword(e.target.value)}
            style={{ padding: '10px', border: '1px solid #ddd', borderRadius: '5px' }}
            required
          />
          <div style={{ gridColumn: '1 / 3' }}>
            <button
              type="submit"
              style={{
                width: '100%',
                padding: '12px',
                border: 'none',
                borderRadius: '5px',
                background: '#667eea',
                color: 'white',
                cursor: 'pointer'
              }}
            >
              Add Connection
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

// Helper functions (unchanged)
function getStatusEmoji(status) {
  const emojis = {
    pending: '⏳',
    processing: '🔄',
    completed: '✅',
    failed: '❌',
    timeout: '⏰'
  }
  return emojis[status] || '❓'
}