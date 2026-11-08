import type { ReactElement } from 'react'
import { BrowserRouter, Link, Navigate, Route, Routes, useLocation } from 'react-router-dom'
import { AuthProvider, useAuth } from './context/AuthContext'
import Layout from './components/Layout'
import Landing from './pages/Landing'
import Login from './pages/Login'
import Register from './pages/Register'
import Overview from './pages/Overview'
import Monitor from './pages/Monitor'
import AnalysisWorkspace from './pages/Analysis'
import AnalysisDetail from './pages/AnalysisDetail'
import Baseline from './pages/Baseline'
import Lab from './pages/Lab'
import Research from './pages/Research'
import Institution from './pages/Institution'
import Reports from './pages/Reports'
import Settings from './pages/Settings'

function Protected({ children }: { children: ReactElement }) {
  const { user, loading } = useAuth()
  const location = useLocation()
  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-ivory">
        <div className="text-center">
          <div className="mx-auto mb-3 h-8 w-8 animate-spin rounded-full border-2 border-line border-t-forest" />
          <p className="text-[11px] uppercase tracking-[0.16em] text-muted">Opening workspace</p>
        </div>
      </div>
    )
  }
  if (!user) return <Navigate to="/login" state={{ from: location.pathname }} replace />
  return children
}

function GuestOnly({ children }: { children: ReactElement }) {
  const { user, loading } = useAuth()
  if (loading) return <div className="min-h-screen bg-ivory" />
  if (user) return <Navigate to="/app" replace />
  return children
}

function NotFound() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-ivory px-6 text-center">
      <p className="text-[10px] uppercase tracking-[0.2em] text-muted">404</p>
      <h1 className="mt-3 font-display text-3xl text-forest">This page is not part of the signal.</h1>
      <p className="mt-2 max-w-sm text-[12px] leading-relaxed text-muted">
        The address may have changed, or the record was removed.
      </p>
      <Link to="/app" className="btn btn-primary mt-5">
        Return to overview
      </Link>
    </div>
  )
}

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          <Route path="/" element={<Landing />} />
          <Route
            path="/login"
            element={
              <GuestOnly>
                <Login />
              </GuestOnly>
            }
          />
          <Route
            path="/register"
            element={
              <GuestOnly>
                <Register />
              </GuestOnly>
            }
          />
          <Route
            path="/app"
            element={
              <Protected>
                <Layout />
              </Protected>
            }
          >
            <Route index element={<Overview />} />
            <Route path="monitor" element={<Monitor />} />
            <Route path="analysis" element={<AnalysisWorkspace />} />
            <Route path="analysis/:id" element={<AnalysisDetail />} />
            <Route path="baseline" element={<Baseline />} />
            <Route path="lab" element={<Lab />} />
            <Route path="research" element={<Research />} />
            <Route path="institution" element={<Institution />} />
            <Route path="reports" element={<Reports />} />
            <Route path="settings" element={<Settings />} />
          </Route>
          <Route path="*" element={<NotFound />} />
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  )
}
