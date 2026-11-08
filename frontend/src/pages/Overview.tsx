import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  Activity,
  ArrowRight,
  ArrowUpRight,
  BrainCircuit,
  FileText,
  FlaskConical,
  Gauge,
  Sparkles,
  Target,
} from 'lucide-react'
import { api, ApiError } from '../lib/api'
import { useAuth } from '../context/AuthContext'
import type { Analysis, BaselinePayload, Session } from '../types'
import { dateShort, duration, relative, stressPercent } from '../lib/format'
import { Badge, Card, ClassPill, EmptyState, LoadingBlock, Notice, PageHeader, QualityPill, SectionLabel, SourceBadge, Stat } from '../components/ui'
import { ProbabilityBars, TrendChart, CHART_COLORS } from '../components/charts'

interface ModelInfo {
  available: boolean
  model_name?: string
  model_version?: string
  global_metrics?: { balanced_accuracy: number; f1_macro: number; accuracy: number }
}

export default function Overview() {
  const { user } = useAuth()
  const [analyses, setAnalyses] = useState<Analysis[]>([])
  const [baseline, setBaseline] = useState<BaselinePayload | null>(null)
  const [sessions, setSessions] = useState<Session[]>([])
  const [model, setModel] = useState<ModelInfo | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let active = true
    const load = async () => {
      try {
        const [analysisResponse, baselineResponse, sessionResponse, modelResponse] = await Promise.all([
          api<{ analyses: Analysis[] }>('/analysis?limit=8'),
          api<BaselinePayload>('/baseline'),
          api<{ sessions: Session[] }>('/sessions?limit=6'),
          api<ModelInfo>('/model/info'),
        ])
        if (!active) return
        setAnalyses(analysisResponse.analyses)
        setBaseline(baselineResponse)
        setSessions(sessionResponse.sessions)
        setModel(modelResponse)
      } catch (err) {
        if (active) setError(err instanceof ApiError ? err.message : 'Unable to load your overview.')
      } finally {
        if (active) setLoading(false)
      }
    }
    void load()
    return () => {
      active = false
    }
  }, [])

  const latest = analyses[0]
  const trend = useMemo(
    () =>
      [...analyses]
        .reverse()
        .map((item) => ({
          label: dateShort(item.created_at).replace(/\s\d{4}$/, ''),
          stress: stressPercent(item.stress_score),
          quality: item.quality?.score ?? null,
          hr: item.features?.hr_mean ?? null,
        })),
    [analyses],
  )

  const local = latest?.explanation?.local?.slice(0, 3) ?? []
  const reliability = baseline?.baseline?.reliability ?? 'none'
  const greeting = new Date().getHours() < 12 ? 'Good morning' : new Date().getHours() < 18 ? 'Good afternoon' : 'Good evening'
  const firstName = (user?.name || 'there').split(' ')[0]

  if (loading) return <LoadingBlock label="Assembling your workspace" />

  return (
    <div>
      <PageHeader
        eyebrow="Overview"
        title={`${greeting}, ${firstName}.`}
        description="A calm view of your recent physiological analyses, signal quality and baseline. Every estimate is shown with its source and uncertainty."
        actions={
          <>
            <Link to="/app/lab" className="btn btn-secondary">
              <FlaskConical size={14} /> Upload a signal
            </Link>
            <Link to="/app/monitor" className="btn btn-primary">
              <Activity size={14} /> Simulated live session
            </Link>
          </>
        }
      />

      {error && (
        <Notice tone="danger" className="mb-5">
          {error}
        </Notice>
      )}

      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <Stat
          label="Latest estimate"
          value={latest ? latest.predicted_label.replace('-associated pattern', '').replace(' / positive-affect pattern', '') : '—'}
          meta={
            latest ? (
              <span className="flex flex-wrap items-center gap-2">
                <span className="tabular">{latest.confidence ? `${Math.round(latest.confidence * 100)}% confidence` : 'No probability'}</span>
                <SourceBadge sourceType={latest.source_type} isDemo={latest.is_demo} />
              </span>
            ) : (
              'Run an analysis to begin'
            )
          }
          icon={<BrainCircuit size={15} />}
          tone="sage"
        />
        <Stat
          label="Signal quality"
          value={latest?.quality?.score != null ? Math.round(latest.quality.score) : '—'}
          unit="/ 100"
          meta={latest ? <QualityPill score={latest.quality.score} grade={latest.quality.grade} /> : 'Quality is assessed per window'}
          icon={<Gauge size={15} />}
          tone={latest?.quality?.grade === 'poor' ? 'coral' : 'neutral'}
        />
        <Stat
          label="Stored analyses"
          value={analyses.length}
          unit="recent records"
          meta={<span>{sessions.length} monitoring sessions · {dateShort(latest?.created_at)}</span>}
          icon={<FileText size={15} />}
        />
        <Stat
          label="Personal baseline"
          value={reliability === 'established' ? 'Stable' : reliability === 'provisional' ? 'Provisional' : 'Not set'}
          meta={
            <span>
              {baseline?.baseline?.session_count ?? 0} of {baseline?.baseline?.required_sessions ?? 5} recommended
              analyses
            </span>
          }
          icon={<Target size={15} />}
          tone={reliability === 'established' ? 'sage' : 'amber'}
        />
      </div>

      <div className="mt-4 grid gap-4 xl:grid-cols-[1.5fr_1fr]">
        <Card className="p-5 md:p-6">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <SectionLabel>Pattern history</SectionLabel>
              <h2 className="mt-1.5 font-display text-xl text-forest">Stress-associated probability over time</h2>
              <p className="mt-1 text-[11px] text-muted">Model-estimated probability, with signal quality overlaid.</p>
            </div>
            <Link to="/app/analysis" className="btn btn-ghost px-2 py-1 text-[11px]">
              All analyses <ArrowRight size={13} />
            </Link>
          </div>

          {trend.length >= 2 ? (
            <>
              <div className="mt-5">
                <TrendChart
                  data={trend}
                  series={[
                    { key: 'stress', label: 'Stress probability', color: CHART_COLORS.coral },
                    { key: 'quality', label: 'Signal quality', color: CHART_COLORS.sage },
                  ]}
                  rightAxis
                  height={230}
                  yDomain={[0, 100]}
                />
              </div>
              <div className="mt-2 flex flex-wrap items-center gap-4 text-[10px] text-muted">
                <span className="inline-flex items-center gap-1.5">
                  <span className="h-1.5 w-4 rounded-full" style={{ background: CHART_COLORS.coral }} /> Stress probability (%)
                </span>
                <span className="inline-flex items-center gap-1.5">
                  <span className="h-1.5 w-4 rounded-full" style={{ background: CHART_COLORS.sage }} /> Signal quality (%)
                </span>
                <span className="ml-auto">last {trend.length} analyses</span>
              </div>
            </>
          ) : (
            <div className="mt-5">
              <EmptyState
                icon={<Sparkles size={18} />}
                title="Not enough history yet"
                description="Run at least two analyses — from a simulated session, an uploaded CSV or a WESAD reference window — to see how the pattern changes."
                action={
                  <Link to="/app/analysis" className="btn btn-secondary px-3 py-1.5 text-[11px]">
                    Run an analysis
                  </Link>
                }
              />
            </div>
          )}
        </Card>

        <Card className="p-5 md:p-6">
          <div className="flex items-start justify-between gap-3">
            <div>
              <SectionLabel>Latest model reading</SectionLabel>
              <h2 className="mt-1.5 font-display text-xl text-forest">What the model saw</h2>
            </div>
            {latest && <ClassPill predicted={latest.predicted_class} label={latest.predicted_label.split(' /')[0]} />}
          </div>

          {latest ? (
            <>
              <p className="mt-2 line-clamp-2 text-[11px] leading-relaxed text-muted">{latest.source_label}</p>
              <div className="mt-4 rounded-xl bg-[#F6F5ED] p-3.5">
                <ProbabilityBars probabilities={latest.class_probabilities} compact />
              </div>
              <div className="mt-4">
                <div className="mb-2 flex items-center justify-between">
                  <span className="text-[10px] font-medium uppercase tracking-[0.12em] text-muted">Features that moved this reading</span>
                  <span className="text-[9px] text-muted">occlusion estimates</span>
                </div>
                {local.length ? (
                  <div className="space-y-1.5">
                    {local.map((item) => (
                      <div key={item.feature} className="flex items-center justify-between gap-2 text-[11px]">
                        <span className="truncate text-charcoal">{item.label}</span>
                        <span className={`tabular shrink-0 ${item.direction === 'toward' ? 'text-[#A45545]' : 'text-[#47664F]'}`}>
                          {item.direction === 'toward' ? '↑' : '↓'} {Math.abs(item.contribution).toFixed(2)}
                        </span>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-[11px] text-muted">No local explanation stored for this analysis.</p>
                )}
              </div>
              <div className="mt-4 flex items-center justify-between border-t border-line pt-3">
                <span className="text-[10px] text-muted">{relative(latest.created_at)} · {latest.window_count} windows</span>
                <Link to={`/app/analysis/${latest.id}`} className="inline-flex items-center gap-1 text-[11px] font-medium text-forest">
                  Full analysis <ArrowUpRight size={13} />
                </Link>
              </div>
            </>
          ) : (
            <div className="mt-5">
              <EmptyState
                icon={<BrainCircuit size={18} />}
                title="No analyses yet"
                description="Start with a simulated session or upload a CSV to see probabilities, quality and feature contributions."
              />
            </div>
          )}
        </Card>
      </div>

      <div className="mt-4 grid gap-4 xl:grid-cols-[1.5fr_1fr]">
        <Card className="overflow-hidden">
          <div className="flex items-center justify-between px-5 pb-3 pt-5">
            <div>
              <SectionLabel>Recent records</SectionLabel>
              <h2 className="mt-1 font-display text-lg text-forest">Analyses</h2>
            </div>
            <Link to="/app/reports" className="text-[11px] text-muted hover:text-forest">
              History & reports
            </Link>
          </div>
          {analyses.length ? (
            <div className="scroll-thin overflow-x-auto">
              <table className="w-full min-w-[560px] text-left text-[11.5px]">
                <thead>
                  <tr className="border-y border-line bg-[#FAFAF4] text-[9px] uppercase tracking-[0.12em] text-muted">
                    <th className="px-5 py-2 font-medium">Analysis</th>
                    <th className="px-3 py-2 font-medium">Estimate</th>
                    <th className="px-3 py-2 font-medium">Stress</th>
                    <th className="px-3 py-2 font-medium">Quality</th>
                    <th className="px-3 py-2 font-medium">When</th>
                  </tr>
                </thead>
                <tbody>
                  {analyses.slice(0, 6).map((item) => (
                    <tr key={item.id} className="border-b border-line/70 transition hover:bg-[#FBFAF3]">
                      <td className="px-5 py-2.5">
                        <Link to={`/app/analysis/${item.id}`} className="font-medium text-forest hover:underline">
                          {item.title}
                        </Link>
                        <div className="mt-1 flex items-center gap-1.5">
                          <SourceBadge sourceType={item.source_type} isDemo={item.is_demo} />
                          <span className="text-[9.5px] text-muted">{item.window_count} windows</span>
                        </div>
                      </td>
                      <td className="px-3 py-2.5">
                        <ClassPill predicted={item.predicted_class} label={item.predicted_label.split(' /')[0]} />
                      </td>
                      <td className="tabular px-3 py-2.5 text-charcoal">{stressPercent(item.stress_score)?.toFixed(0) ?? '—'}%</td>
                      <td className="px-3 py-2.5">
                        <span className="tabular text-muted">{item.quality?.score != null ? `${Math.round(item.quality.score)}/100` : '—'}</span>
                      </td>
                      <td className="px-3 py-2.5 text-muted">{relative(item.created_at)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="px-5 pb-5">
              <EmptyState title="No stored analyses" description="Your completed simulated sessions and uploads will appear here." />
            </div>
          )}
        </Card>

        <div className="space-y-4">
          <Card className="p-5">
            <SectionLabel>Signal sources</SectionLabel>
            <h2 className="mt-1 font-display text-lg text-forest">Ways to analyse</h2>
            <div className="mt-3 space-y-2">
              {[
                { to: '/app/monitor', icon: Activity, title: 'Simulated live session', body: '5 scenarios · labelled synthetic' },
                { to: '/app/lab', icon: FlaskConical, title: 'BioSignal Lab', body: 'CSV upload · channel mapping' },
                { to: '/app/analysis', icon: BrainCircuit, title: 'WESAD reference window', body: 'Genuine inference on cached features' },
              ].map((item) => {
                const Icon = item.icon
                return (
                  <Link
                    key={item.to}
                    to={item.to}
                    className="group flex items-center gap-3 rounded-xl border border-line bg-[#FBFAF4] px-3 py-2.5 transition hover:border-sage"
                  >
                    <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-[#EEF1E5] text-[#4C6449]">
                      <Icon size={14} />
                    </span>
                    <span className="min-w-0 flex-1">
                      <span className="block text-[12px] font-medium text-charcoal">{item.title}</span>
                      <span className="block text-[10px] text-muted">{item.body}</span>
                    </span>
                    <ArrowRight size={13} className="text-muted transition group-hover:translate-x-0.5 group-hover:text-forest" />
                  </Link>
                )
              })}
            </div>
          </Card>

          <Card className="p-5">
            <div className="flex items-start justify-between">
              <div>
                <SectionLabel>Model</SectionLabel>
                <h2 className="mt-1 font-display text-lg text-forest">{model?.model_name || 'Model unavailable'}</h2>
              </div>
              <Badge tone={model?.available ? 'good' : 'poor'}>{model?.available ? 'Loaded' : 'Missing'}</Badge>
            </div>
            <div className="mt-3 grid grid-cols-2 gap-3">
              <div className="rounded-lg bg-[#F6F5ED] px-3 py-2">
                <p className="text-[9px] uppercase tracking-[0.1em] text-muted">Balanced acc.</p>
                <p className="mt-0.5 font-display text-lg text-forest">
                  {model?.global_metrics?.balanced_accuracy != null
                    ? `${(model.global_metrics.balanced_accuracy * 100).toFixed(1)}%`
                    : '—'}
                </p>
              </div>
              <div className="rounded-lg bg-[#F6F5ED] px-3 py-2">
                <p className="text-[9px] uppercase tracking-[0.1em] text-muted">Macro F1</p>
                <p className="mt-0.5 font-display text-lg text-forest">
                  {model?.global_metrics?.f1_macro != null ? `${(model.global_metrics.f1_macro * 100).toFixed(1)}%` : '—'}
                </p>
              </div>
            </div>
            <p className="mono mt-2.5 truncate text-[9px] text-muted">{model?.model_version || 'no artifact'}</p>
            <p className="mt-2 text-[10px] leading-relaxed text-muted">
              Participant-independent evaluation. Not a clinical accuracy figure.
            </p>
          </Card>

          {sessions.length > 0 && (
            <Card className="p-5">
              <SectionLabel>Monitoring sessions</SectionLabel>
              <div className="mt-2 space-y-2">
                {sessions.slice(0, 3).map((session) => (
                  <div key={session.id} className="flex items-center justify-between gap-2 text-[11px]">
                    <div className="min-w-0">
                      <p className="truncate capitalize text-charcoal">{session.scenario.replace('_', ' ')}</p>
                      <p className="text-[9.5px] text-muted">
                        {duration(session.duration_seconds)} · {relative(session.started_at)}
                      </p>
                    </div>
                    <Badge tone={session.status === 'completed' ? 'good' : session.status === 'active' ? 'sage' : 'neutral'}>
                      {session.status}
                    </Badge>
                  </div>
                ))}
              </div>
            </Card>
          )}
        </div>
      </div>

      <Notice tone="warning" className="mt-4" title="How to read this page">
        Estimates describe similarity to patterns learned from WESAD laboratory conditions. They are not a diagnosis and
        individual physiology varies with sleep, caffeine, movement and illness. Seeded demo records are synthetic and
        labelled.
      </Notice>
    </div>
  )
}
