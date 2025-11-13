import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.tsx'
import './index.css'

// Temporarily disable StrictMode to prevent double-mounting in development
// This prevents WebSocket connection leaks caused by StrictMode's double-mount behavior
// TODO: Re-enable StrictMode once WebSocket connection reuse is fully stable
ReactDOM.createRoot(document.getElementById('root')!).render(
  // <React.StrictMode>
    <App />
  // </React.StrictMode>
)

