import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { AlertCircle, ArrowRight, User, Microscope } from 'lucide-react'
import AuthShell from '../components/AuthShell'
import { useAuth } from '../context/AuthContext'
import { ApiError } from '../lib/api'
import { cn } from '../components/ui'

export default function Register() {
  const { register } = useAuth()
  const navigate = useNavigate()
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [role, setRole] = useState<'individual' | 'researcher'>('individual')
  const [code, setCode] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  const submit = async (event: React.FormEvent) => {
    event.preventDefault()
    if (password.length < 8) {
      setError('Password must be at least 8 characters.')
      return
    }
    setBusy(true)
    setError(null)
    try {
      await register({
        name: name.trim(),
        email: email.trim(),
        password,
        role,
        institution_code: role === 'researcher' ? code.trim() : undefined,
      })
      navigate('/app', { replace: true })
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Unable to create the account. Please try again.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <AuthShell
      title="Create your workspace."
      subtitle="Private by default. Sharing with institution aggregates is opt-in and can be withdrawn at any time."
      footer={
        <>
          Already have an account?{' '}
          <Link to="/login" className="font-medium text-forest underline decoration-sage underline-offset-2">
            Sign in
          </Link>
        </>
      }
    >
      <form onSubmit={submit} className="space-y-4">
        <div className="grid grid-cols-2 gap-2">
          {[
            { key: 'individual', label: 'Personal', description: 'Your own signals', icon: User },
            { key: 'researcher', label: 'Research', description: 'Experiments & aggregates', icon: Microscope },
          ].map((option) => {
            const Icon = option.icon
            const active = role === option.key
            return (
              <button
                key={option.key}
                type="button"
                onClick={() => setRole(option.key as 'individual' | 'researcher')}
                className={cn(
                  'rounded-xl border p-3 text-left transition',
                  active ? 'border-forest bg-[#F1F3E9]' : 'border-line bg-paper hover:border-sage',
                )}
              >
                <Icon size={15} className={active ? 'text-forest' : 'text-muted'} />
                <p className="mt-2 text-[12px] font-medium text-charcoal">{option.label}</p>
                <p className="text-[10px] text-muted">{option.description}</p>
              </button>
            )
          })}
        </div>

        <div>
          <label className="label" htmlFor="name">
            Full name
          </label>
          <input
            id="name"
            required
            className="field"
            value={name}
            onChange={(event) => setName(event.target.value)}
            placeholder="Your name"
            autoComplete="name"
          />
        </div>
        <div>
          <label className="label" htmlFor="reg-email">
            Email
          </label>
          <input
            id="reg-email"
            type="email"
            required
            className="field"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            placeholder="you@example.com"
            autoComplete="email"
          />
        </div>
        <div>
          <label className="label" htmlFor="reg-password">
            Password
          </label>
          <input
            id="reg-password"
            type="password"
            required
            minLength={8}
            className="field"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            placeholder="At least 8 characters"
            autoComplete="new-password"
          />
        </div>

        {role === 'researcher' && (
          <div>
            <label className="label" htmlFor="code">
              Institutional research code
            </label>
            <input
              id="code"
              required
              className="field"
              value={code}
              onChange={(event) => setCode(event.target.value)}
              placeholder="Provided by your institution"
            />
            <p className="mt-1.5 text-[10px] leading-relaxed text-muted">
              Demonstration code: <span className="mono text-[#5E6B58]">AURA-RESEARCH</span>. Researcher accounts can
              run experiments and view consent-based aggregates.
            </p>
          </div>
        )}

        {error && (
          <div className="flex items-start gap-2 rounded-lg border border-[#EDD2C9] bg-[#FAEDE9] px-3 py-2.5 text-[11px] text-[#A45545]">
            <AlertCircle size={14} className="mt-0.5 shrink-0" />
            {error}
          </div>
        )}

        <button type="submit" disabled={busy} className="btn btn-primary w-full py-3 text-[13px]">
          {busy ? 'Creating account…' : 'Create workspace'}
          {!busy && <ArrowRight size={15} />}
        </button>

        <p className="text-[10px] leading-relaxed text-muted">
          By creating an account you acknowledge that AuraSense is a research prototype, not a medical device, and that
          its estimates must not be used for diagnosis or treatment decisions.
        </p>
      </form>
    </AuthShell>
  )
}
