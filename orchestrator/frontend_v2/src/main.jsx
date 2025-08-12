import React from 'react'
import ReactDOM from 'react-dom/client'
import App from '@/App.jsx'
import '@/index.css'
import { AuthProvider } from './contexts/AuthContext.jsx'
import { RundownProvider } from './contexts/RundownContext.jsx'

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <AuthProvider>
      <RundownProvider>
        <App />
      </RundownProvider>
    </AuthProvider>
  </React.StrictMode>,
)