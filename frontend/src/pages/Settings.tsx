import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { Download, KeyRound, ShieldCheck, Trash2, UserRound } from 'lucide-react'
import { api, ApiError, download } from '../lib/api'
import { useAuth } from '../context/AuthContext'
import type { Profile, User } from '../types'
import { Badge, Card, Field, LoadingBlock, Modal, Notice, PageHeader, SectionLabel, Toggle } from '../components/ui'

export default function Settings() {
  const { user, setUser, logout } = useAuth()
  const [name, setName] = useState('')
  const [profile, setProfile] = useState<Profile | null>(null)
  const [saving, setSaving] = useState(false)
  const [message, setMessage] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [currentPassword, setCurrentPassword] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [passwordBusy, setPasswordBusy] = useState(false)
  const [deleteOpen, setDeleteOpen] = useState(false)
  const [deletePassword, setDeletePassword] = useState('')
  const [deleteBusy, setDeleteBusy] = useState(false)
  const [exporting, setExporting] = useState(false)

  useEffect(() => {
    if (user) {
      setName(user.name)
      setProfile(user.profile)
    }
  }, [user])

  if (!user || !profile) return <LoadingBlock label="Loading account" />

  const save = async () => {
    setSaving(true)
    setMessage(null)
    setError(null)
    try {
      const updated = await api<User>('/auth/profile', {
        method: 'PATCH',
        body: {
          name,
          display_name: profile.display_name,
          organisation: profile.organisation,
          share_aggregate: profile.share_aggregate,
          store_raw_signals: profile.store_raw_signals,
          allow_baseline: profile.allow_baseline,
          baseline_min_sessions: profile.baseline_min_sessions,
          data_note: profile.data_note,
        },
      })
      setUser(updated)
      setMessage('Account and privacy preferences saved.')
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Unable to save your settings.')
    } finally {
      setSaving(false)
    }
  }

  const changePassword = async (event: React.FormEvent) => {
    event.preventDefault()
    setPasswordBusy(true)
    setMessage(null)
    setError(null)
    try {
      await api('/auth/password', { method: 'POST', body: { current_password: currentPassword, new_password: newPassword } })
      setCurrentPassword('')
      setNewPassword('')
      setMessage('Password updated.')
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Unable to change the password.')
    } finally {
      setPasswordBusy(false)
    }
  }

  const exportData = async () => {
    setExporting(true)
    setError(null)
    try {
      await download('/auth/export', 'aurasense-export.json')
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Unable to export your data.')
    } finally {
      setExporting(false)
    }
  }

  const deleteAccount = async () => {
    setDeleteBusy(true)
    setError(null)
    try {
      await api('/auth/account', { method: 'DELETE', body: { password: deletePassword } })
      logout()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Unable to delete the account.')
      setDeleteBusy(false)
    }
  }

  const update = <K extends keyof Profile>(key: K, value: Profile[K]) => setProfile({ ...profile, [key]: value })

  return (
    <div>
      <PageHeader
        eyebrow="Settings & Account"
        title="Your data, on your terms."
        description="Manage your profile, sharing preferences, password and data export. Sharing is off by default and can be withdrawn at any time."
        actions={
          <button onClick={save} disabled={saving} className="btn btn-primary">
            {saving ? 'Saving…' : 'Save changes'}
          </button>
        }
      />

      {message && (
        <Notice tone="success" className="mb-4">
          {message}
        </Notice>
      )}
      {error && (
        <Notice tone="danger" className="mb-4">
          {error}
        </Notice>
      )}

      <div className="grid gap-4 xl:grid-cols-[1.2fr_1fr]">
        <div className="space-y-4">
          <Card className="p-5 md:p-6">
            <div className="flex items-center gap-2">
              <UserRound size={15} className="text-sage" />
              <SectionLabel>Profile</SectionLabel>
            </div>
            <div className="mt-3 grid gap-4 sm:grid-cols-2">
              <Field label="Full name">
                <input className="field" value={name} onChange={(event) => setName(event.target.value)} />
              </Field>
              <Field label="Display name">
                <input
                  className="field"
                  value={profile.display_name || ''}
                  onChange={(event) => update('display_name', event.target.value)}
                  placeholder="Shown inside your workspace"
                />
              </Field>
              <Field label="Email">
                <input className="field bg-[#F5F4EC] text-muted" value={user.email} disabled />
              </Field>
              <Field label="Organisation">
                <input
                  className="field"
                  value={profile.organisation || ''}
                  onChange={(event) => update('organisation', event.target.value)}
                  placeholder="Optional"
                />
              </Field>
            </div>
            <div className="mt-3">
              <Field label="Personal note" hint="Stored with your account; not included in aggregates.">
                <textarea
                  className="field min-h-[80px] resize-y"
                  value={profile.data_note || ''}
                  onChange={(event) => update('data_note', event.target.value)}
                  placeholder="Recording context, sensor placement, anything that helps you interpret your own data."
                />
              </Field>
            </div>
            <div className="mt-3 flex items-center gap-2 text-[10px] text-muted">
              <Badge tone="sage">{user.role}</Badge>
              {user.is_demo && <Badge tone="amber">Demonstration account</Badge>}
              <span>Account ID <span className="mono">{user.id.slice(0, 8)}</span></span>
            </div>
          </Card>

          <Card className="p-5 md:p-6">
            <div className="flex items-center gap-2">
              <ShieldCheck size={15} className="text-sage" />
              <SectionLabel>Privacy & data</SectionLabel>
            </div>
            <div className="mt-2 divide-y divide-line">
              <Toggle
                checked={profile.share_aggregate}
                onChange={(value) => update('share_aggregate', value)}
                label="Include my analyses in institution aggregates"
                description="Only de-identified aggregate statistics are shown, and only when the cohort is large enough. Individual records are never exposed."
              />
              <Toggle
                checked={profile.store_raw_signals}
                onChange={(value) => update('store_raw_signals', value)}
                label="Retain raw simulated signal files"
                description="When off, completed simulated sessions keep their derived features and analysis but not the raw waveform file."
              />
              <Toggle
                checked={profile.allow_baseline}
                onChange={(value) => update('allow_baseline', value)}
                label="Allow personal baseline calculation"
                description="Baselines are computed from your own completed analyses and shown only to you."
              />
            </div>
            <div className="mt-3 max-w-[220px]">
              <Field label="Baseline minimum analyses" hint="Between 3 and 12.">
                <select
                  className="field"
                  value={profile.baseline_min_sessions}
                  onChange={(event) => update('baseline_min_sessions', Number(event.target.value))}
                >
                  {[3, 4, 5, 6, 8, 10, 12].map((value) => (
                    <option key={value} value={value}>
                      {value} analyses
                    </option>
                  ))}
                </select>
              </Field>
            </div>
          </Card>

          <Card className="p-5 md:p-6">
            <div className="flex items-center gap-2">
              <KeyRound size={15} className="text-sage" />
              <SectionLabel>Password</SectionLabel>
            </div>
            <form onSubmit={changePassword} className="mt-3 grid gap-3 sm:grid-cols-2">
              <Field label="Current password">
                <input
                  type="password"
                  className="field"
                  value={currentPassword}
                  onChange={(event) => setCurrentPassword(event.target.value)}
                  required
                  autoComplete="current-password"
                />
              </Field>
              <Field label="New password" hint="At least 8 characters.">
                <input
                  type="password"
                  className="field"
                  value={newPassword}
                  onChange={(event) => setNewPassword(event.target.value)}
                  required
                  minLength={8}
                  autoComplete="new-password"
                />
              </Field>
              <div className="sm:col-span-2">
                <button type="submit" disabled={passwordBusy} className="btn btn-secondary">
                  {passwordBusy ? 'Updating…' : 'Update password'}
                </button>
              </div>
            </form>
          </Card>
        </div>

        <div className="space-y-4">
          <Card className="p-5">
            <SectionLabel>Your data</SectionLabel>
            <h2 className="mt-1 font-display text-lg text-forest">Portable and removable</h2>
            <p className="mt-2 text-[11px] leading-relaxed text-muted">
              Export your account details, analyses, baselines and monitoring sessions as JSON. Raw waveform files are
              not included.
            </p>
            <button onClick={exportData} disabled={exporting} className="btn btn-secondary mt-3 w-full">
              <Download size={14} /> {exporting ? 'Preparing export…' : 'Export my data (JSON)'}
            </button>
            <div className="mt-4 border-t border-line pt-4">
              <p className="text-[11px] font-medium text-[#A45545]">Delete account</p>
              <p className="mt-1 text-[10px] leading-relaxed text-muted">
                Removes your account and associated analyses, sessions, baselines and reports. This cannot be undone.
              </p>
              <button onClick={() => setDeleteOpen(true)} className="btn btn-danger mt-2 w-full">
                <Trash2 size={13} /> Delete my account
              </button>
            </div>
          </Card>

          <Card className="p-5">
            <SectionLabel>About this workspace</SectionLabel>
            <div className="mt-2 space-y-2 text-[11px]">
              <div className="flex justify-between gap-3">
                <span className="text-muted">Product</span>
                <span className="text-charcoal">AuraSense v1.0.0</span>
              </div>
              <div className="flex justify-between gap-3">
                <span className="text-muted">Model</span>
                <span className="text-charcoal">Gradient boosting</span>
              </div>
              <div className="flex justify-between gap-3">
                <span className="text-muted">Dataset</span>
                <span className="text-charcoal">WESAD (15 participants)</span>
              </div>
              <div className="flex justify-between gap-3">
                <span className="text-muted">Evaluation</span>
                <span className="text-right text-charcoal">GroupKFold by participant</span>
              </div>
            </div>
            <div className="mt-3 space-y-2 border-t border-line pt-3">
              <Link to="/app/research" className="block text-[10.5px] text-forest underline underline-offset-2">
                View the research evaluation
              </Link>
              <p className="text-[9.5px] leading-relaxed text-muted">
                AuraSense is a research prototype, not a medical device. It does not diagnose, treat or prevent any
                condition.
              </p>
            </div>
          </Card>
        </div>
      </div>

      <Modal
        open={deleteOpen}
        onClose={() => setDeleteOpen(false)}
        title="Delete your account?"
        description="This permanently removes your account and associated analyses, sessions, baselines and report files."
        footer={
          <>
            <button className="btn btn-secondary" onClick={() => setDeleteOpen(false)}>
              Cancel
            </button>
            <button className="btn btn-danger" onClick={deleteAccount} disabled={deleteBusy || !deletePassword}>
              {deleteBusy ? 'Deleting…' : 'Permanently delete'}
            </button>
          </>
        }
      >
        <Field label="Confirm with your password">
          <input
            type="password"
            className="field"
            value={deletePassword}
            onChange={(event) => setDeletePassword(event.target.value)}
            placeholder="Current password"
            autoComplete="current-password"
          />
        </Field>
        {user.is_demo && (
          <p className="mt-2 text-[10px] leading-relaxed text-[#8A6526]">
            Demonstration accounts cannot be deleted. Create your own account to manage your data.
          </p>
        )}
      </Modal>
    </div>
  )
}
