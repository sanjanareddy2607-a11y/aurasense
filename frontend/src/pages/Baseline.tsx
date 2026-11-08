import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { ArrowRight, RefreshCw, RotateCcw, Target, TrendingUp } from 'lucide-react'
import { api, ApiError } from '../lib/api'
import type { BaselinePayload } from '../types'
import { Badge, Card, EmptyState, LoadingBlock, Modal, Notice, PageHeader, ProgressBar, SectionLabel, Stat } from '../components/ui'
import { TrendChart, CHART_COLORS } from '../components/charts'
import { dateTime, num, stressPercent } from '../lib/format'

export default function Baseline() {
  const [data, setData] = useState<BaselinePayload | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const [confirmReset, setConfirmReset] = useState(false)

  const load = async () => {
    const response = await api<BaselinePayload>('/baseline')
    setData(response)
  }

  useEffect(() => {
    load()
      .catch((err) => setError(err instanceof ApiError ? err.message : 'Unable to load your baseline.'))
      .finally(() => setLoading(false))
  }, [])

  const recalibrate = async () => {
    setBusy(true)
    setError(null)
    try {
      await api('/baseline/recalibrate', { method: 'POST' })
      await load()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Unable to recalculate the baseline.')
    } finally {
      setBusy(false)
    }
  }

  const reset = async () => {
    setBusy(true)
    setError(null)
    try {
      await api('/baseline/reset', { method: 'POST' })
      setConfirmReset(false)
      await load()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Unable to reset the baseline.')
    } finally {
      setBusy(false)
    }
  }

  const trend = useMemo(
    () =>
      [...(data?.baseline.trend ?? [])].reverse().map((item) => ({
        label: new Date(item.created_at || '').toLocaleDateString('en-GB', { day: '2-digit', month: 'short' }),
        stress: stressPercent(item.stress_probability),
        hr: item.hr_mean,
      })),
    [data],
  )

  if (loading) return <LoadingBlock label="Loading your baseline" />
  if (!data) return <Notice tone="danger">{error || 'Baseline unavailable.'}</Notice>

  const baseline = data.baseline
  const comparison = data.latest_comparison
  const featureEntries = Object.entries(baseline.features ?? {})
  const groups = Array.from(new Set(featureEntries.map(([, value]) => value.group)))
  const progress = Math.min(100, (baseline.session_count / Math.max(1, baseline.required_sessions)) * 100)
  const reliabilityTone = baseline.reliability === 'established' ? 'good' : baseline.reliability === 'provisional' ? 'fair' : 'neutral'

  return (
    <div>
      <PageHeader
        eyebrow="My Baseline"
        title="Your own reference, not a population norm."
        description="A baseline summarises how your physiology usually looks across your completed analyses, then contrasts new readings with it. It is exploratory, personal and not clinically validated."
        actions={
          <>
            <button onClick={recalibrate} disabled={busy} className="btn btn-primary">
              <RefreshCw size={14} /> {busy ? 'Calculating…' : 'Recalculate baseline'}
            </button>
            <button onClick={() => setConfirmReset(true)} disabled={busy || !baseline.exists} className="btn btn-secondary">
              <RotateCcw size={13} /> Reset
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
          label="Baseline status"
          value={baseline.reliability === 'established' ? 'Reliable' : baseline.reliability === 'provisional' ? 'Provisional' : 'Not set'}
          meta={<Badge tone={reliabilityTone}>{baseline.reliability}</Badge>}
          icon={<Target size={15} />}
          tone={baseline.reliability === 'established' ? 'sage' : 'amber'}
        />
        <Stat label="Analyses used" value={baseline.session_count} unit="of 12 max" meta={`${baseline.required_sessions} recommended`} />
        <Stat label="Features tracked" value={featureEntries.length} unit="physiological" meta="across cardiac, electrodermal and respiratory groups" />
        <Stat
          label="Latest contrast"
          value={comparison?.notable?.length ?? 0}
          unit="notable features"
          meta={comparison?.available ? `vs ${comparison.analysis_title || 'latest analysis'}` : 'No analysed reading yet'}
          icon={<TrendingUp size={15} />}
        />
      </div>

      <div className="mt-4 grid gap-4 xl:grid-cols-[1.5fr_1fr]">
        <Card className="p-5 md:p-6">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <SectionLabel>Stability</SectionLabel>
              <h2 className="mt-1.5 font-display text-xl text-forest">Stress-associated probability across analyses</h2>
            </div>
            <span className="text-[10px] text-muted">{trend.length} readings</span>
          </div>

          {trend.length >= 2 ? (
            <div className="mt-4">
              <TrendChart
                data={trend}
                series={[{ key: 'stress', label: 'Stress probability', color: CHART_COLORS.coral }]}
                height={230}
                yDomain={[0, 100]}
              />
            </div>
          ) : (
            <div className="mt-4">
              <EmptyState
                icon={<Target size={18} />}
                title="Not enough readings for a trend"
                description="Complete at least two analyses. A baseline becomes more meaningful with five or more, ideally recorded in similar conditions."
                action={
                  <Link to="/app/analysis" className="btn btn-secondary px-3 py-1.5 text-[11px]">
                    Run an analysis <ArrowRight size={12} />
                  </Link>
                }
              />
            </div>
          )}

          <div className="mt-4 rounded-xl border border-line bg-[#F9F9F2] px-4 py-3">
            <div className="flex items-center justify-between text-[11px]">
              <span className="text-charcoal">Baseline maturity</span>
              <span className="tabular text-muted">{baseline.session_count} / {baseline.required_sessions} recommended</span>
            </div>
            <ProgressBar className="mt-2" value={progress} tone={baseline.reliable ? 'sage' : 'amber'} />
            <p className="mt-2 text-[10.5px] leading-relaxed text-muted">{baseline.message}</p>
            {baseline.updated_at && <p className="mt-1 text-[9.5px] text-muted">Updated {dateTime(baseline.updated_at)}</p>}
          </div>
        </Card>

        <Card className="p-5">
          <div className="flex items-start justify-between">
            <div>
              <SectionLabel>Latest contrast</SectionLabel>
              <h2 className="mt-1 font-display text-lg text-forest">Away from your usual</h2>
            </div>
            {comparison?.available && <Badge tone="sage">Compared</Badge>}
          </div>
          {comparison?.available ? (
            <>
              <p className="mt-2 text-[11px] leading-relaxed text-muted">{comparison.summary}</p>
              <div className="mt-3 space-y-2.5">
                {comparison.notable.slice(0, 5).map((item) => (
                  <div key={item.feature}>
                    <div className="flex items-center justify-between text-[11px]">
                      <span className="truncate text-charcoal">{item.label}</span>
                      <span className={`tabular shrink-0 text-[10px] ${item.direction === 'above' ? 'text-[#A45545]' : 'text-[#47664F]'}`}>
                        {item.direction === 'above' ? '↑' : '↓'} {Math.abs(item.z_score).toFixed(1)} SD
                      </span>
                    </div>
                    <div className="mt-1 flex items-center gap-2 text-[9.5px] text-muted">
                      <span className="tabular">{num(item.value, 2)} {item.unit}</span>
                      <span>· baseline {num(item.baseline_mean, 2)}</span>
                    </div>
                  </div>
                ))}
              </div>
              {comparison.analysis_id && (
                <Link to={`/app/analysis/${comparison.analysis_id}`} className="mt-4 inline-flex items-center gap-1 text-[11px] font-medium text-forest">
                  Open compared analysis <ArrowRight size={12} />
                </Link>
              )}
            </>
          ) : (
            <div className="mt-3">
              <EmptyState title="No comparison yet" description="Once a baseline and an analysis exist, the most noticeable differences appear here." />
            </div>
          )}
        </Card>
      </div>

      <Card className="mt-4 p-5 md:p-6">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div>
            <SectionLabel>Baseline profile</SectionLabel>
            <h2 className="mt-1 font-display text-lg text-forest">Feature means and variability</h2>
          </div>
          <span className="text-[10px] text-muted">mean ± standard deviation · personal, not normative</span>
        </div>

        {featureEntries.length ? (
          <div className="mt-5 grid gap-x-8 gap-y-5 md:grid-cols-2">
            {groups.map((group) => (
              <div key={group}>
                <p className="mb-2 text-[9px] font-semibold uppercase tracking-[0.14em] text-muted">{group}</p>
                <div className="space-y-2">
                  {featureEntries
                    .filter(([, value]) => value.group === group)
                    .map(([key, value]) => (
                      <div key={key} className="flex items-center justify-between gap-3 border-b border-line/60 pb-1.5">
                        <span className="text-[11px] text-charcoal">{value.label}</span>
                        <span className="tabular shrink-0 text-[11px] text-muted">
                          {num(value.mean, 2)} <span className="text-[9.5px]">± {num(value.std, 2)} {value.unit}</span>
                        </span>
                      </div>
                    ))}
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="mt-4">
            <EmptyState title="No baseline computed" description="Recalculate after completing a few analyses to build your personal reference." />
          </div>
        )}
      </Card>

      <Notice tone="warning" className="mt-4" title="Baseline limitations">
        {baseline.disclaimer}
      </Notice>

      <Modal
        open={confirmReset}
        onClose={() => setConfirmReset(false)}
        title="Reset your baseline?"
        description="This deactivates the current baseline. Your analyses remain intact, and you can compute a new baseline later."
        footer={
          <>
            <button className="btn btn-secondary" onClick={() => setConfirmReset(false)}>
              Keep baseline
            </button>
            <button className="btn btn-danger" onClick={reset} disabled={busy}>
              {busy ? 'Resetting…' : 'Reset baseline'}
            </button>
          </>
        }
      >
        <p className="text-[11px] leading-relaxed text-muted">
          Future comparisons will be unavailable until a new baseline is created from at least three completed analyses.
        </p>
      </Modal>
    </div>
  )
}
