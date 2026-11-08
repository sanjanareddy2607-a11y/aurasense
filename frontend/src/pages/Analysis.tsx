import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { ArrowRight, BrainCircuit, Database, FlaskConical, Layers, ScanLine, Sparkles } from 'lucide-react'
import { api, ApiError } from '../lib/api'
import type { Analysis, Dataset } from '../types'
import { Badge, Card, ClassPill, EmptyState, LoadingBlock, Notice, PageHeader, SectionLabel, SourceBadge } from '../components/ui'
import { relative } from '../lib/format'
import { cn } from '../components/ui'

const SUBJECTS = ['S2', 'S3', 'S4', 'S5', 'S6', 'S7', 'S8', 'S9', 'S10', 'S11', 'S13', 'S14', 'S15', 'S16', 'S17']
const LABELS = [
  { key: '', label: 'Any condition' },
  { key: 'neutral', label: 'Neutral' },
  { key: 'stress', label: 'Stress' },
  { key: 'amusement', label: 'Amusement' },
]

export default function AnalysisWorkspace() {
  const navigate = useNavigate()
  const [analyses, setAnalyses] = useState<Analysis[]>([])
  const [datasets, setDatasets] = useState<Dataset[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState<string | null>(null)
  const [subject, setSubject] = useState('')
  const [label, setLabel] = useState('')
  const [tab, setTab] = useState<'reference' | 'datasets'>('reference')

  useEffect(() => {
    Promise.all([api<{ analyses: Analysis[] }>('/analysis?limit=10'), api<{ datasets: Dataset[] }>('/datasets')])
      .then(([analysisResponse, datasetResponse]) => {
        setAnalyses(analysisResponse.analyses)
        setDatasets(datasetResponse.datasets)
      })
      .catch((err) => setError(err instanceof ApiError ? err.message : 'Unable to load analysis options.'))
      .finally(() => setLoading(false))
  }, [])

  const runReference = async () => {
    setBusy('reference')
    setError(null)
    try {
      const response = await api<{ analysis: Analysis }>('/analysis/reference', {
        method: 'POST',
        body: { subject: subject || null, label: label || null },
      })
      navigate(`/app/analysis/${response.analysis.id}`)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Unable to analyse the reference window.')
    } finally {
      setBusy(null)
    }
  }

  const runDataset = async (dataset: Dataset) => {
    setBusy(dataset.id)
    setError(null)
    try {
      const response = await api<{ analysis: Analysis }>('/analysis/demo', {
        method: 'POST',
        body: { dataset_id: dataset.id },
      })
      navigate(`/app/analysis/${response.analysis.id}`)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Unable to analyse this dataset.')
    } finally {
      setBusy(null)
    }
  }

  const reference = datasets.find((dataset) => dataset.is_reference)
  const others = datasets.filter((dataset) => !dataset.is_reference)

  if (loading) return <LoadingBlock label="Preparing analysis options" />

  return (
    <div>
      <PageHeader
        eyebrow="AI Analysis"
        title="Inspect one reading, end to end."
        description="Run the trained model on a cached WESAD reference window or a demonstration dataset, then open a reading that shows probabilities, quality, feature contributions and the model version behind it."
        actions={
          <Link to="/app/lab" className="btn btn-secondary">
            <FlaskConical size={14} /> Upload your own CSV
          </Link>
        }
      />

      {error && (
        <Notice tone="danger" className="mb-4">
          {error}
        </Notice>
      )}

      <div className="grid gap-4 xl:grid-cols-[1.45fr_1fr]">
        <div className="space-y-4">
          <Card className="p-5 md:p-6">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <SectionLabel>New analysis</SectionLabel>
                <h2 className="mt-1.5 font-display text-xl text-forest">Choose a signal source</h2>
              </div>
              <div className="inline-flex rounded-full border border-line bg-[#F4F3EB] p-1">
                {[
                  { key: 'reference' as const, label: 'WESAD reference' },
                  { key: 'datasets' as const, label: 'Demo datasets' },
                ].map((item) => (
                  <button
                    key={item.key}
                    onClick={() => setTab(item.key)}
                    className={cn(
                      'rounded-full px-3 py-1.5 text-[11px] font-medium transition',
                      tab === item.key ? 'bg-paper text-forest shadow-sm' : 'text-muted hover:text-forest',
                    )}
                  >
                    {item.label}
                  </button>
                ))}
              </div>
            </div>

            {tab === 'reference' ? (
              <div className="mt-5">
                <div className="rounded-xl border border-line bg-[#F9F9F2] p-4">
                  <div className="flex items-start gap-3">
                    <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-[#EEF1E5] text-[#4C6449]">
                      <ScanLine size={16} />
                    </span>
                    <div>
                      <p className="text-[12px] font-medium text-charcoal">Genuine inference on cached WESAD features</p>
                      <p className="mt-1 text-[11px] leading-relaxed text-muted">
                        The backend extracts the selected participant's window features from the local WESAD installation
                        and runs the persisted model. This demonstrates real inference, but it is reference data — not a
                        prediction about you.
                      </p>
                    </div>
                  </div>
                </div>

                <div className="mt-4 grid gap-3 sm:grid-cols-2">
                  <div>
                    <label className="label" htmlFor="subject">
                      Participant (optional)
                    </label>
                    <select id="subject" className="field" value={subject} onChange={(event) => setSubject(event.target.value)}>
                      <option value="">Random eligible window</option>
                      {SUBJECTS.map((item) => (
                        <option key={item} value={item}>
                          {item}
                        </option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <label className="label" htmlFor="condition">
                      Condition (optional)
                    </label>
                    <select id="condition" className="field" value={label} onChange={(event) => setLabel(event.target.value)}>
                      {LABELS.map((item) => (
                        <option key={item.key} value={item.key}>
                          {item.label}
                        </option>
                      ))}
                    </select>
                  </div>
                </div>

                <button onClick={runReference} disabled={busy === 'reference'} className="btn btn-primary mt-4 w-full py-2.5">
                  <BrainCircuit size={14} /> {busy === 'reference' ? 'Running model…' : 'Analyse reference window'}
                </button>
              </div>
            ) : (
              <div className="mt-5 space-y-2.5">
                {others.map((dataset) => (
                  <div key={dataset.id} className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-line bg-[#FBFBF4] p-3.5">
                    <div className="min-w-0">
                      <div className="flex flex-wrap items-center gap-2">
                        <p className="text-[12px] font-medium text-charcoal">{dataset.name}</p>
                        <Badge tone="amber">{dataset.is_demo ? 'Synthetic demo' : 'Dataset'}</Badge>
                      </div>
                      <p className="mt-1 line-clamp-2 max-w-md text-[10.5px] leading-relaxed text-muted">{dataset.description}</p>
                    </div>
                    <button
                      onClick={() => runDataset(dataset)}
                      disabled={busy === dataset.id}
                      className="btn btn-secondary px-3 py-1.5 text-[11px]"
                    >
                      {busy === dataset.id ? 'Analysing…' : 'Analyse'} <ArrowRight size={12} />
                    </button>
                  </div>
                ))}
                {!others.length && <EmptyState title="No demonstration datasets" description="Seed data has not been created in this environment." />}
              </div>
            )}
          </Card>

          <Card className="overflow-hidden">
            <div className="flex items-center justify-between px-5 pb-3 pt-5">
              <div>
                <SectionLabel>History</SectionLabel>
                <h2 className="mt-1 font-display text-lg text-forest">Recent analyses</h2>
              </div>
              <Link to="/app/reports" className="text-[11px] text-muted hover:text-forest">
                Reports
              </Link>
            </div>
            {analyses.length ? (
              <div className="scroll-thin overflow-x-auto">
                <table className="w-full min-w-[520px] text-left text-[11.5px]">
                  <thead>
                    <tr className="border-y border-line bg-[#FAFAF4] text-[9px] uppercase tracking-[0.12em] text-muted">
                      <th className="px-5 py-2 font-medium">Analysis</th>
                      <th className="px-3 py-2 font-medium">Estimate</th>
                      <th className="px-3 py-2 font-medium">Quality</th>
                      <th className="px-3 py-2 font-medium">When</th>
                    </tr>
                  </thead>
                  <tbody>
                    {analyses.map((item) => (
                      <tr key={item.id} className="border-b border-line/70 hover:bg-[#FBFAF3]">
                        <td className="px-5 py-2.5">
                          <Link to={`/app/analysis/${item.id}`} className="font-medium text-forest hover:underline">
                            {item.title}
                          </Link>
                          <div className="mt-1">
                            <SourceBadge sourceType={item.source_type} isDemo={item.is_demo} />
                          </div>
                        </td>
                        <td className="px-3 py-2.5">
                          <ClassPill predicted={item.predicted_class} label={item.predicted_label.split(' /')[0]} />
                        </td>
                        <td className="tabular px-3 py-2.5 text-muted">{item.quality?.score != null ? `${Math.round(item.quality.score)}/100` : '—'}</td>
                        <td className="px-3 py-2.5 text-muted">{relative(item.created_at)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <div className="px-5 pb-5">
                <EmptyState icon={<Sparkles size={18} />} title="No analyses yet" description="Run a reference window to create your first reading." />
              </div>
            )}
          </Card>
        </div>

        <div className="space-y-4">
          <Card className="p-5">
            <div className="flex items-start justify-between">
              <div>
                <SectionLabel>Reference dataset</SectionLabel>
                <h2 className="mt-1 font-display text-lg text-forest">WESAD</h2>
              </div>
              <Database size={16} className="text-sage" />
            </div>
            {reference ? (
              <>
                <p className="mt-2 text-[11px] leading-relaxed text-muted">{reference.description}</p>
                <div className="mt-3 grid grid-cols-2 gap-2">
                  <div className="rounded-lg bg-[#F6F5ED] px-3 py-2">
                    <p className="text-[9px] uppercase tracking-[0.1em] text-muted">Participants</p>
                    <p className="font-display text-lg text-forest">{reference.participant_count}</p>
                  </div>
                  <div className="rounded-lg bg-[#F6F5ED] px-3 py-2">
                    <p className="text-[9px] uppercase tracking-[0.1em] text-muted">Conditions</p>
                    <p className="font-display text-lg text-forest">{reference.class_names.length || 3}</p>
                  </div>
                </div>
              </>
            ) : (
              <p className="mt-2 text-[11px] text-muted">The reference dataset is not registered in this environment.</p>
            )}
            <p className="mt-3 border-t border-line pt-3 text-[9.5px] leading-relaxed text-muted">
              Schmidt &amp; Reiss (2018). WESAD. DOI: 10.24432/C57K5T. Not redistributed with this app.
            </p>
          </Card>

          <Card className="p-5">
            <SectionLabel>What happens when you run</SectionLabel>
            <div className="mt-3 space-y-3">
              {[
                { icon: Layers, title: 'Windowed features', body: '60-second windows with 30-second stride are reduced to 20 interpretable features.' },
                { icon: BrainCircuit, title: 'Model inference', body: 'The persisted gradient-boosted model returns three-class probabilities.' },
                { icon: ScanLine, title: 'Local explanation', body: 'Each feature is occluded in turn to estimate how much it moved the reading.' },
              ].map((step) => {
                const Icon = step.icon
                return (
                  <div key={step.title} className="flex gap-3">
                    <span className="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-md bg-[#EEF1E5] text-[#4C6449]">
                      <Icon size={13} />
                    </span>
                    <div>
                      <p className="text-[11.5px] font-medium text-charcoal">{step.title}</p>
                      <p className="mt-0.5 text-[10.5px] leading-relaxed text-muted">{step.body}</p>
                    </div>
                  </div>
                )
              })}
            </div>
          </Card>

          <Notice tone="warning" title="Interpretation">
            Probabilities are model outputs on laboratory data, not clinical findings. Poor signal quality lowers
            confidence and should make you more cautious, not more certain.
          </Notice>
        </div>
      </div>
    </div>
  )
}
