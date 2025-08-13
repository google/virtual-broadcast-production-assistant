import React from 'react'
import ReactDOM from 'react-dom/client'
import App from '@/App.jsx'
import '@/index.css'
import { AuthProvider } from './contexts/AuthContext.jsx'
import { RundownProvider } from './contexts/RundownContext.jsx'
import { SocketProvider } from './contexts/SocketContext.jsx'

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <AuthProvider>
      <SocketProvider>
        <RundownProvider>
          <App />
        </RundownProvider>
      </SocketProvider>
    </AuthProvider>
  </React.StrictMode>,
)