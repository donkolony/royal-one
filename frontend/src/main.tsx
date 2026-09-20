import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import { QueryClientProvider } from '@tanstack/react-query'
import App from './App'
import { AuthProvider } from './context/AuthContext'
import { ErrorBoundary } from './components/ui'
import { queryClient } from './lib/queryClient'
import { applyTheme } from './lib/theme'
import './index.css'
import './styles.css'
import './integration.css'

// Apply the saved (or system) theme before the first paint so every page, sign-in included, is themed.
applyTheme('light')

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <ErrorBoundary fullScreen>
        <QueryClientProvider client={queryClient}>
          <BrowserRouter>
            <AuthProvider>
              <App />
            </AuthProvider>
          </BrowserRouter>
        </QueryClientProvider>
    </ErrorBoundary>
  </React.StrictMode>
)
