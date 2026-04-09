import { Component, type ErrorInfo, type ReactNode, useEffect, useState } from 'react'
import { BrowserRouter, Route, Routes } from 'react-router-dom'
import { authTelegram } from './api/client'
import { BottomNav } from './components/BottomNav'
import { Loader } from './components/Loader'
import CaseDetail from './pages/CaseDetail'
import Cases from './pages/Cases'
import Dashboard from './pages/Dashboard'
import MyRequests from './pages/MyRequests'
import RequestDetail from './pages/RequestDetail'
import RequestList from './pages/RequestList'
import SignalDetail from './pages/SignalDetail'
import Signals from './pages/Signals'
import Topics from './pages/Topics'
import WebApp from './telegram'
import './index.css'

class ErrorBoundary extends Component<{ children: ReactNode }, { error: string }> {
  state = { error: '' }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error('ErrorBoundary caught:', error, info)
    this.setState({ error: `${error.name}: ${error.message}\n\n${info.componentStack?.slice(0, 300)}` })
  }

  render() {
    if (this.state.error) {
      return (
        <div
          style={{
            padding: 16,
            fontFamily: 'monospace',
            fontSize: 12,
            color: '#ff4444',
            background: '#1a1a1a',
            minHeight: '100vh',
            whiteSpace: 'pre-wrap',
            wordBreak: 'break-all',
          }}
        >
          <div style={{ color: '#ff8888', fontSize: 14, fontWeight: 'bold', marginBottom: 8 }}>React Error</div>
          {this.state.error}
        </div>
      )
    }
    return this.props.children
  }
}

export default function App() {
  const [ready, setReady] = useState(false)
  const [error, setError] = useState('')
  const [debugInfo, setDebugInfo] = useState('')

  useEffect(() => {
    WebApp.ready()
    WebApp.expand()

    const init = async () => {
      try {
        const existingToken = localStorage.getItem('jwt_token')
        if (existingToken && existingToken !== 'undefined' && existingToken !== 'null') {
          setReady(true)
          return
        }

        localStorage.removeItem('jwt_token')

        const initData = WebApp.initData
        if (!initData) {
          setDebugInfo('browser-mode')
          setReady(true)
          return
        }

        const { access_token } = await authTelegram(initData)
        if (!access_token) throw new Error('No token in response')
        localStorage.setItem('jwt_token', access_token)
        setReady(true)
      } catch (e: any) {
        console.error('Auth error:', e)
        const msg = e?.response?.data?.detail ?? e?.message ?? 'Unknown error'
        setError(`Ошибка авторизации: ${msg}`)
        setDebugInfo(msg)
        setReady(true)
      }
    }

    init()
  }, [])

  if (!ready) {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', minHeight: '100vh' }}>
        <Loader />
        <div style={{ marginTop: 12, fontSize: 13, color: 'var(--text-soft)' }}>Загрузка мини-приложения...</div>
      </div>
    )
  }

  return (
    <ErrorBoundary>
      <BrowserRouter>
        {error && (
          <div style={{ background: '#fee2e2', color: '#b91c1c', fontSize: 13, textAlign: 'center', padding: '8px 16px' }}>
            {error}
          </div>
        )}
        {debugInfo === 'browser-mode' && (
          <div style={{ background: '#fef3c7', color: '#92400e', fontSize: 12, textAlign: 'center', padding: '6px 16px' }}>
            Приложение открыто вне Telegram, поэтому вход выполнен в режиме просмотра.
          </div>
        )}
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/signals" element={<Signals />} />
          <Route path="/topics" element={<Topics />} />
          <Route path="/signals/:id" element={<SignalDetail />} />
          <Route path="/cases" element={<Cases />} />
          <Route path="/cases/:id" element={<CaseDetail />} />
          <Route path="/requests" element={<RequestList />} />
          <Route path="/requests/:id" element={<RequestDetail />} />
          <Route path="/my" element={<MyRequests />} />
        </Routes>
        <BottomNav />
      </BrowserRouter>
    </ErrorBoundary>
  )
}
