import { useState } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { ArrowRight, AlertCircle } from 'lucide-react'
import AuthShell from '../components/AuthShell'
import { useAuth } from '../context/AuthContext'
import { ApiError } from '../lib/api'

const DEMOS = [
  { label: 'Individual demo', email: 'demo@aurasense.app', password: 'Demo1234!' },
  { label: 'Researcher demo', email: 'researcher@aurasense.app', password: 'Research1234!' },
  { label: 'Institution demo', email: 'institution@aurasense.app', password: 'Institution1234!' },
]

export default function Login() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  const submit = async (event: React.FormEvent) => {
    event.preventDefault()
    setBusy(true)
    setError(null)
    try {
      await login(email.trim(), password)
      const from = (location.state as { from?: string } | null)?.from
      navigate(from && from.startsWith('/app') ? from : '/app', { replace: true })
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Unable to sign in. Please try again.')
    } finally {
      setBusy(false)
    }
  }

  const fillDemo = (demo: (typeof DEMOS)[number]) => {
    setEmail(demo.email)
    setPassword(demo.password)
    setError(null)
  }

  return (
    <AuthShell
      title="Welcome back."
      subtitle="Sign in to review your signal history, baselines and research analyses."
      footer={
        <>
          New to AuraSense?{' '}
          <Link to="/register" className="font-medium text-forest underline decoration-sage underline-offset-2">
            Create a workspace
          </Link>
        </>
      }
    >
      <form onSubmit={submit} className="space-y-4">
        <div>
          <label className="label" htmlFor="email">
            Email
          </label>
          <input
            id="email"
            type="email"
            required
            autoComplete="email"
            className="field"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            placeholder="you@example.com"
          />
        </div>
        <div>
          <label className="label" htmlFor="password">
            Password
          </label>
          <input
            id="password"
            type="password"
            required
            autoComplete="current-password"
            className="field"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            placeholder="••••••••"
          />
        </div>

        {error && (
          <div className="flex items-start gap-2 rounded-lg border border-[#EDD2C9] bg-[#FAEDE9] px-3 py-2.5 text-[11px] text-[#A45545]">
            <AlertCircle size={14} className="mt-0.5 shrink-0" />
            {error}
          </div>
        )}

        <button type="submit" disabled={busy} className="btn btn-primary w-full py-3 text-[13px]">
          {busy ? 'Signing in…' : 'Sign in'}
          {!busy && <ArrowRight size={15} />}
        </button>
      </form>

      <div className="mt-7">
        <div className="mb-3 flex items-center gap-3">
          <div className="hairline flex-1" />
          <span className="text-[10px] uppercase tracking-[0.14em] text-muted">Demonstration accounts</span>
          <div className="hairline flex-1" />
        </div>
        <div className="grid grid-cols-3 gap-2">
          {DEMOS.map((demo) => (
            <button
              key={demo.email}
              type="button"
              onClick={() => fillDemo(demo)}
              className="rounded-lg border border-line bg-paper px-2 py-2.5 text-[10.5px] font-medium text-[#5E665F] transition hover:border-sage hover:text-forest"
            >
              {demo.label}
            </button>
          ))}
        </div>
        <p className="mt-2.5 text-center text-[10px] leading-relaxed text-muted">
          Demonstration data is synthetic and clearly labelled. Click a role, then sign in.
        </p>
      </div>
    </AuthShell>
  )
}
