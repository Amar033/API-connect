import { useState } from 'react'
import { Routes, Route } from "react-router-dom";
import Example from './components/Hero'
import './index.css'
import Login from './components/Login';
function App() {
  const [count, setCount] = useState(0)

  return (
   <Routes>
      <Route path="/" element={<Example />} />
      <Route path="/login" element={<Login />} />
    </Routes>
  );
}

export default App
