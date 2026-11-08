import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { ArrowLeft, FileDown, Gauge, Info, Microscope, Sparkles } from 'lucide-react'
import { api, ApiError, download } from '../lib/api'
import type { Analysis, ReportRecord } from '../types'
import {
  Badge,
  Card,
  ClassPill,
  EmptyState,
  LoadingBlock,
  Notice,
  PageHeader,
  ProgressBar,
  QualityPill,
  SectionLabel,
  SourceBadge,
} from '../components/ui'
import { ImportanceBars, ProbabilityBars } from '../components/charts'
import { dateTime, duration, featureName, num, stressPercent } from '../lib/format'

export default function AnalysisDetail() {
  const { id } = useParams<{ id: string }>()
  const [analysis, setAnalysis] = useState<Analysis | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [reporting, setReporting] = useState(false)

  useEffect(() => {
    if (!id) return
    setLoading(true)
    api<Analysis>(`/analysis/${id}`)
      .then(setAnalysis)
      .catch((err) => setError(err instanceof ApiError ? err.message : 'Unable to load this analysis.'))
      .finally(() => setLoading(false))
  }, [id])

  const generateReport = async () => {
    if (!analysis) return
    setReporting(true)
    setError(null)
    try {
      const response = await api<{ report: ReportRecord }>(`/reports/analysis/${analysis.id}`, { method: 'POST', body: {} })
      await download(`/reports/${response.report.id}/download`, `aurasense-analysis-${analysis.id.slice(0, 8)}.pdf`)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Unable to generate the PDF report.')
    } finally {
      setReporting(false)
    }
  }

  if (loading) return <LoadingBlock label="Loading analysis" />
  if (error && !analysis) {
    return (
      <div>
        <Notice tone="danger">{error}</Notice>
        <Link to="/app/analysis" className="btn btn-secondary mt-4">
          <ArrowLeft size={14} /> Back to analyses
        </Link>
      </div>
    )
  }
  if (!analysis) return null

  const local = analysis.explanation?.local ?? []
  const global = analysis.explanation?.global_top ?? []
  const features = analysis.features ? Object.entries(analysis.features) : []
  const stress = stressPercent(analysis.stress_score)
  const maxContribution = Math.max(...local.map((item) => Math.abs(item.contribution)), 0.0001)

  return (
    <div>
      <div className="mb-5 flex flex-wrap items-center gap-2 text-[11px] text-muted">
        <Link to="/app/analysis" className="inline-flex items-center gap-1 hover:text-forest">
          <ArrowLeft size={13} /> AI Analysis
        </Link>
        <span>/</span>
        <span className="truncate text-charcoal">{analysis.title}</span>
      </div>

      <PageHeader
        eyebrow="Analysis record"
        title={analysis.title}
        description={analysis.source_label}
        actions={
          <>
            <button onClick={generateReport} disabled={reporting} className="btn btn-secondary">
              <FileDown size={14} /> {reporting ? 'Generating…' : 'PDF report'}
            </button>
            <Link to="/app/lab" className="btn btn-primary">
              Analyse another signal
            </Link>
          </>
        }
      />

      <div className="flex flex-wrap items-center gap-2">
        <ClassPill predicted={analysis.predicted_class} label={analysis.predicted_label} />
        <SourceBadge sourceType={analysis.source_type} isDemo={analysis.is_demo} />
        <QualityPill score={analysis.quality?.score} grade={analysis.quality?.grade} />
        <Badge>{analysis.window_count} windows</Badge>
        <Badge>{duration(analysis.duration_seconds)}</Badge>
        <span className="text-[10.5px] text-muted">{dateTime(analysis.created_at)}</span>
        {analysis.session?.is_simulation && <Badge tone="sage">Simulated session</Badge>}
      </div>

      {error && (
        <Notice tone="danger" className="mt-4">
          {error}
        </Notice>
      )}

      <div className="mt-4 grid gap-4 xl:grid-cols-[1.35fr_1fr]">
        <div className="space-y-4">
          <Card className="p-5 md:p-6">
            <div className="flex flex-wrap items-start justify-between gap-4">
              <div>
                <SectionLabel>Model estimate</SectionLabel>
                <h2 className="mt-1.5 font-display text-[26px] leading-tight text-forest">{analysis.predicted_label}</h2>
                <p className="mt-1 text-[11px] text-muted">
                  {analysis.confidence != null ? `${(analysis.confidence * 100).toFixed(1)}% confidence` : 'No probability available'}
                  {analysis.uncertainty != null ? ` · distribution uncertainty ${analysis.uncertainty.toFixed(2)} (0–1)` : ''}
                </p>
              </div>
              <div className="rounded-xl bg-[#F6F5ED] px-4 py-3 text-right">
                <p className="text-[9px] uppercase tracking-[0.12em] text-muted">Stress-associated prob.</p>
                <p className="mt-1 font-display text-3xl text-forest">{stress != null ? `${stress.toFixed(0)}%` : '—'}</p>
              </div>
            </div>

            <div className="mt-5">
              <ProbabilityBars probabilities={analysis.class_probabilities} />
            </div>

            <div className="mt-5 grid gap-2 border-t border-line pt-4 sm:grid-cols-3">
              <div>
                <p className="text-[9px] uppercase tracking-[0.1em] text-muted">Model</p>
                <p className="mt-0.5 text-[11px] text-charcoal">Gradient boosting</p>
              </div>
              <div>
                <p className="text-[9px] uppercase tracking-[0.1em] text-muted">Version</p>
                <p className="mono mt-0.5 truncate text-[10px] text-charcoal">{analysis.model_version || '—'}</p>
              </div>
              <div>
                <p className="text-[9px] uppercase tracking-[0.1em] text-muted">Classes</p>
                <p className="mt-0.5 text-[11px] text-charcoal">Neutral · Stress · Amusement</p>
              </div>
            </div>
          </Card>

          <Card className="p-5 md:p-6">
            <div className="flex items-center justify-between">
              <div>
                <SectionLabel>Why this estimate</SectionLabel>
                <h2 className="mt-1 font-display text-lg text-forest">Feature contributions</h2>
              </div>
              <span className="text-[9.5px] text-muted">occlusion-based, local</span>
            </div>
            <p className="mt-1.5 text-[11px] leading-relaxed text-muted">
              Each feature is replaced with the reference median and the change in the predicted class probability is
              measured. Larger bars moved this reading more.
            </p>

            {local.length ? (
              <div className="mt-4 space-y-3">
                {local.map((item) => (
                  <div key={item.feature}>
                    <div className="flex items-baseline justify-between gap-3 text-[11px]">
                      <span className="text-charcoal">{item.label}</span>
                      <span className="tabular shrink-0 text-muted">
                        {num(item.value, 2)} {item.unit} <span className="text-[9.5px]">vs {num(item.reference_median, 2)}</span>
                      </span>
                    </div>
                    <div className="mt-1 flex items-center gap-2">
                      <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-[#EDEBE1]">
                        <div
                          className={`h-full rounded-full ${item.direction === 'toward' ? 'bg-coral' : 'bg-sage'}`}
                          style={{ width: `${(Math.abs(item.contribution) / maxContribution) * 100}%` }}
                        />
                      </div>
                      <span className={`w-14 text-right text-[10px] tabular ${item.direction === 'toward' ? 'text-[#A45545]' : 'text-[#47664F]'}`}>
                        {item.direction === 'toward' ? '+' : '−'}
                        {Math.abs(item.contribution).toFixed(3)}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <EmptyState title="No local explanation" description="This analysis was stored without occlusion contributions." />
            )}
            {analysis.explanation?.note && <p className="mt-3 text-[9.5px] leading-relaxed text-muted">{analysis.explanation.note}</p>}
          </Card>

          {features.length > 0 && (
            <Card className="p-5 md:p-6">
              <div className="flex items-center justify-between">
                <div>
                  <SectionLabel>Extracted features</SectionLabel>
                  <h2 className="mt-1 font-display text-lg text-forest">Window measurements</h2>
                </div>
                <Badge>{features.length} features</Badge>
              </div>
              <div className="mt-4 grid gap-x-6 gap-y-2.5 sm:grid-cols-2">
                {features.map(([key, value]) => (
                  <div key={key} className="flex items-center justify-between gap-3 border-b border-line/60 pb-1.5 text-[11px]">
                    <span className="text-muted">{featureName(key)}</span>
                    <span className="tabular text-charcoal">{value === null || value === undefined ? 'missing' : num(value, 2)}</span>
                  </div>
                ))}
              </div>
              {analysis.imputed_features.length > 0 && (
                <p className="mt-3 text-[10px] leading-relaxed text-[#8A6526]">
                  Imputed before inference: {analysis.imputed_features.map(featureName).join(', ')}. Imputation reduces the
                  reliability of this reading.
                </p>
              )}
            </Card>
          )}
        </div>

        <div className="space-y-4">
          <Card className="p-5">
            <div className="flex items-start justify-between">
              <div>
                <SectionLabel>Signal quality</SectionLabel>
                <h2 className="mt-1 font-display text-lg text-forest">
                  {analysis.quality?.score != null ? `${Math.round(analysis.quality.score)} / 100` : 'Not scored'}
                </h2>
              </div>
              <Gauge size={16} className="text-sage" />
            </div>
            <ProgressBar
              className="mt-3"
              value={analysis.quality?.score ?? 0}
              tone={analysis.quality?.grade === 'good' ? 'sage' : analysis.quality?.grade === 'fair' ? 'amber' : 'coral'}
            />
            <p className="mt-2 text-[10.5px] capitalize text-muted">{analysis.quality?.grade ?? 'unknown'} quality</p>
            {analysis.quality?.issues?.length ? (
              <ul className="mt-3 space-y-1.5">
                {analysis.quality.issues.map((issue) => (
                  <li key={issue.code} className="text-[10.5px] leading-relaxed text-[#8A6526]">
                    · {issue.message}
                  </li>
                ))}
              </ul>
            ) : (
              <p className="mt-2 text-[10.5px] leading-relaxed text-muted">No quality issues were detected in this window.</p>
            )}
          </Card>

          <Card className="p-5">
            <div className="flex items-center justify-between">
              <div>
                <SectionLabel>Model-wide signal</SectionLabel>
                <h2 className="mt-1 font-display text-lg text-forest">Global feature importance</h2>
              </div>
              <Microscope size={15} className="text-sage" />
            </div>
            <p className="mt-1.5 text-[10.5px] leading-relaxed text-muted">Permutation importance on held-out participants.</p>
            <div className="mt-3">
              {global.length ? (
                <ImportanceBars
                  items={global.map((item) => ({ feature: featureName(item.feature), share: item.share }))}
                  limit={8}
                />
              ) : (
                <p className="text-[11px] text-muted">Not available.</p>
              )}
            </div>
          </Card>

          <Card className="p-5">
            <SectionLabel>Source &amp; provenance</SectionLabel>
            <div className="mt-2 space-y-2 text-[11px]">
              <div className="flex items-start justify-between gap-2">
                <span className="text-muted">Source type</span>
                <span className="text-right capitalize text-charcoal">{analysis.source_type.replace(/_/g, ' ')}</span>
              </div>
              <div className="flex items-start justify-between gap-2">
                <span className="text-muted">Windows</span>
                <span className="tabular text-charcoal">{analysis.window_count}</span>
              </div>
              <div className="flex items-start justify-between gap-2">
                <span className="text-muted">Duration</span>
                <span className="tabular text-charcoal">{duration(analysis.duration_seconds)}</span>
              </div>
              <div className="flex items-start justify-between gap-2">
                <span className="text-muted">Created</span>
                <span className="text-right text-charcoal">{dateTime(analysis.created_at)}</span>
              </div>
              {analysis.session && (
                <div className="flex items-start justify-between gap-2">
                  <span className="text-muted">Session scenario</span>
                  <span className="text-right capitalize text-charcoal">{analysis.session.scenario.replace(/_/g, ' ')}</span>
                </div>
              )}
            </div>
            {analysis.is_demo && (
              <p className="mt-3 rounded-lg bg-[#F8EFDF] px-2.5 py-2 text-[9.5px] leading-relaxed text-[#8A6526]">
                Seeded demonstration record. Signals were generated synthetically by the simulator.
              </p>
            )}
          </Card>

          <Notice tone="warning" title="Not a diagnosis">
            <span className="inline-flex items-start gap-1.5">
              <Info size={12} className="mt-0.5 shrink-0" />
              This reading compares physiological features with patterns learned from laboratory conditions. It cannot
              establish that you are stressed, anxious or unwell.
            </span>
          </Notice>

          <Link to="/app/baseline" className="flex items-center justify-between rounded-xl border border-line bg-paper px-4 py-3 text-[11.5px] text-charcoal transition hover:border-sage">
            <span className="inline-flex items-center gap-2">
              <Sparkles size={14} className="text-sage" /> Compare with your personal baseline
            </span>
            <span className="text-muted">→</span>
          </Link>
        </div>
      </div>
    </div>
  )
}
