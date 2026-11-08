import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { Building2, Download, FileDown, Lock, ShieldCheck, Users } from 'lucide-react'
import { api, ApiError, download } from '../lib/api'
import { useAuth } from '../context/AuthContext'
import type { InstitutionOverview } from '../types'
import { Badge, Card, EmptyState, LoadingBlock, Notice, PageHeader, SectionLabel, Stat } from '../components/ui'
import { WeeklyBars } from '../components/charts'
import { num } from '../lib/format'

function sharePercent(share: number): number {
  return Math.max(0, Math.min(100, share > 1 ? share : share * 100))
}

export default function Institution() {
  const { user } = useAuth()
  const [data, setData] = useState<InstitutionOverview | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const [weeks, setWeeks] = useState(8)

  const load = async (windowWeeks: number) => {
    setLoading(true)
    try {
      const response = await api<InstitutionOverview>(`/institution/overview?weeks=${windowWeeks}`)
      setData(response)
      setError(null)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Unable to load institution insights.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (user && user.role !== 'individual') void load(weeks)
    else setLoading(false)
  }, [user, weeks])

  const exportCsv = async () => {
    setBusy(true)
    try {
      await download(`/institution/export?weeks=${weeks}`, 'aurasense-aggregate.csv')
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Unable to export the aggregate CSV.')
    } finally {
      setBusy(false)
    }
  }

  const institutionReport = async () => {
    setBusy(true)
    try {
      const response = await api<{ report: { id: string } }>(`/reports/institution?weeks=${weeks}`, { method: 'POST', body: {} })
      await download(`/reports/${response.report.id}/download`, 'aurasense-institution-report.pdf')
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Unable to generate the institution report.')
    } finally {
      setBusy(false)
    }
  }

  if (loading) return <LoadingBlock label="Aggregating consented records" />

  if (user?.role === 'individual') {
    return (
      <div>
        <PageHeader
          eyebrow="Institution Insights"
          title="Aggregate views are restricted."
          description="Institution-level analytics are available to researcher and institution accounts. Individual accounts never see, and are never shown in, another person's data."
        />
        <Card className="mx-auto max-w-xl p-8 text-center">
          <span className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-[#EEF1E5] text-[#4C6449]">
            <Lock size={20} />
          </span>
          <h2 className="mt-4 font-display text-xl text-forest">Consent-based, cohort-level only</h2>
          <p className="mx-auto mt-2 max-w-md text-[12px] leading-relaxed text-muted">
            Institution Insights shows only aggregate statistics from users who explicitly opted in, and suppresses any
            group below the minimum cohort. No individual records, identifiers or raw signals are exposed.
          </p>
          <p className="mt-4 rounded-lg bg-[#F6F5ED] px-3 py-2 text-[11px] text-muted">
            Sign in with the institution demonstration account to see the aggregate view.
          </p>
          <div className="mt-5 flex justify-center gap-2">
            <Link to="/app/settings" className="btn btn-secondary">
              Manage sharing settings
            </Link>
            <Link to="/app" className="btn btn-primary">
              Back to overview
            </Link>
          </div>
        </Card>
      </div>
    )
  }

  if (!data) return <Notice tone="danger">{error || 'Aggregate data unavailable.'}</Notice>

  return (
    <div>
      <PageHeader
        eyebrow="Institution Insights"
        title="Patterns across a consented cohort."
        description="Only aggregate, de-identified statistics from users who opted in. Groups below the minimum cohort are suppressed rather than partially shown."
        actions={
          <>
            <select className="field !w-auto !py-2 text-[11px]" value={weeks} onChange={(event) => setWeeks(Number(event.target.value))}>
              <option value={4}>Last 4 weeks</option>
              <option value={8}>Last 8 weeks</option>
              <option value={12}>Last 12 weeks</option>
              <option value={26}>Last 26 weeks</option>
            </select>
            <button onClick={exportCsv} disabled={busy} className="btn btn-secondary">
              <Download size={14} /> CSV
            </button>
            <button onClick={institutionReport} disabled={busy} className="btn btn-primary">
              <FileDown size={14} /> Aggregate PDF
            </button>
          </>
        }
      />

      {error && (
        <Notice tone="danger" className="mb-4">
          {error}
        </Notice>
      )}

      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <Stat
          label="Analysed sessions"
          value={data.summary.sessions}
          unit="in window"
          meta={`${data.summary.demo_sessions} seeded demo records`}
          icon={<Building2 size={15} />}
        />
        <Stat
          label="Consenting participants"
          value={data.summary.participants}
          meta={`${data.summary.consenting_users} users opted in`}
          icon={<Users size={15} />}
          tone="sage"
        />
        <Stat
          label="Mean stress probability"
          value={data.summary.mean_stress_probability != null ? `${data.summary.mean_stress_probability.toFixed(0)}%` : '—'}
          meta="Model output, not a prevalence estimate"
          tone="amber"
        />
        <Stat
          label="Mean signal quality"
          value={data.summary.mean_quality != null ? Math.round(data.summary.mean_quality) : '—'}
          unit="/ 100"
          meta="Poor-quality readings should be interpreted cautiously"
        />
      </div>

      <div className="mt-4 grid gap-4 xl:grid-cols-[1.5fr_1fr]">
        <Card className="p-5 md:p-6">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <SectionLabel>Weekly composition</SectionLabel>
              <h2 className="mt-1 font-display text-xl text-forest">Estimated pattern mix</h2>
              <p className="mt-1 text-[10.5px] text-muted">Share of analysed sessions by model estimate and week.</p>
            </div>
            <Badge tone="sage">
              <ShieldCheck size={11} /> Small-cell suppressed
            </Badge>
          </div>

          {data.weekly.length ? (
            <div className="mt-4">
              <WeeklyBars
                data={data.weekly.map((week) => ({
                  ...week,
                  week_start: new Date(week.week_start).toLocaleDateString('en-GB', { day: '2-digit', month: 'short' }),
                }))}
              />
              <div className="mt-2 flex flex-wrap items-center gap-4 text-[10px] text-muted">
                <span className="inline-flex items-center gap-1.5"><span className="h-1.5 w-3 rounded-full bg-[#91A58E]" /> Neutral</span>
                <span className="inline-flex items-center gap-1.5"><span className="h-1.5 w-3 rounded-full bg-[#A4A477]" /> Amusement</span>
                <span className="inline-flex items-center gap-1.5"><span className="h-1.5 w-3 rounded-full bg-[#D49A45]" /> Stress-associated</span>
                <span className="ml-auto">Weeks with fewer than {data.privacy.min_sessions_per_group} sessions are withheld</span>
              </div>
            </div>
          ) : (
            <EmptyState title="No aggregate data in this window" description="Widen the time range or wait for consented sessions to accumulate." />
          )}
        </Card>

        <div className="space-y-4">
          <Card className="p-5">
            <SectionLabel>Privacy guarantees</SectionLabel>
            <div className="mt-3 space-y-3">
              {[
                { label: 'Minimum cohort', value: `${data.min_cohort} sessions` },
                { label: 'Minimum participants', value: `${data.privacy.min_participants_per_group} per group` },
                { label: 'Suppressed groups', value: String(data.privacy.suppressed_groups) },
                { label: 'Sharing basis', value: 'Explicit opt-in' },
                { label: 'Demo data', value: data.privacy.demo_data_included ? 'Included & labelled' : 'Excluded' },
              ].map((item) => (
                <div key={item.label} className="flex items-center justify-between border-b border-line/60 pb-1.5 text-[11px]">
                  <span className="text-muted">{item.label}</span>
                  <span className="text-right text-charcoal">{item.value}</span>
                </div>
              ))}
            </div>
            <p className="mt-3 text-[10px] leading-relaxed text-muted">{data.privacy.note}</p>
          </Card>

          <Card className="p-5">
            <SectionLabel>Estimate distribution</SectionLabel>
            <div className="mt-3 space-y-2.5">
              {Object.entries(data.class_distribution).map(([name, value]) => (
                <div key={name}>
                  <div className="flex items-center justify-between text-[11px]">
                    <span className="capitalize text-charcoal">{name}</span>
                    <span className="tabular text-muted">{value.count} · {sharePercent(value.share).toFixed(0)}%</span>
                  </div>
                  <div className="mt-1 h-1.5 overflow-hidden rounded-full bg-[#EDEBE1]">
                    <div
                      className="h-full rounded-full"
                      style={{
                        width: `${sharePercent(value.share)}%`,
                        background: name === 'stress' ? '#D49A45' : name === 'amusement' ? '#A4A477' : '#91A58E',
                      }}
                    />
                  </div>
                </div>
              ))}
            </div>
            <div className="mt-4 border-t border-line pt-3">
              <p className="text-[9px] font-semibold uppercase tracking-[0.12em] text-muted">Signal sources</p>
              <div className="mt-2 space-y-1">
                {Object.entries(data.sources).map(([source, count]) => (
                  <div key={source} className="flex justify-between text-[10.5px]">
                    <span className="capitalize text-muted">{source.replace(/_/g, ' ')}</span>
                    <span className="tabular text-charcoal">{count}</span>
                  </div>
                ))}
              </div>
            </div>
          </Card>
        </div>
      </div>

      <div className="mt-4 grid gap-4 md:grid-cols-2">
        <Card className="p-5">
          <SectionLabel>What this view is for</SectionLabel>
          <ul className="mt-2 space-y-2 text-[10.5px] leading-relaxed text-muted">
            <li>· Understanding whether stress-associated patterns vary across weeks in a consented group.</li>
            <li>· Evaluating signal quality and data completeness at a programme level.</li>
            <li>· Supporting research reporting without exposing any individual record.</li>
          </ul>
        </Card>
        <Card className="p-5">
          <SectionLabel>What it must not be used for</SectionLabel>
          <ul className="mt-2 space-y-2 text-[10.5px] leading-relaxed text-muted">
            <li>· Surveillance, ranking or performance assessment of individuals or teams.</li>
            <li>· Screening, diagnosis or triage of any health condition.</li>
            <li>· Estimating population prevalence — the cohort is self-selected and small.</li>
          </ul>
        </Card>
      </div>

      <Notice tone="warning" className="mt-4" title="Aggregate data statement">
        {data.disclaimer} Mean values: stress probability {num(data.summary.mean_stress_probability, 1)}%, quality{' '}
        {num(data.summary.mean_quality, 0)}/100. Generated {new Date(data.generated_at).toLocaleString('en-GB')}.
      </Notice>
    </div>
  )
}
