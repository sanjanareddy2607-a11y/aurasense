import { useEffect, useMemo, useState } from 'react'
import { Activity, Database, FileDown, FlaskConical, Microscope, Play, Users } from 'lucide-react'
import { api, ApiError, download } from '../lib/api'
import type { Experiment, ResearchOverview } from '../types'
import {
  Badge,
  Card,
  EmptyState,
  LoadingBlock,
  Notice,
  PageHeader,
  ProgressBar,
  SectionLabel,
  Stat,
  Tabs,
} from '../components/ui'
import { ConfusionMatrix, ImportanceBars, ModelBars } from '../components/charts'
import { dateTime, featureName, num } from '../lib/format'

const CLASSES = ['neutral', 'stress', 'amusement']

export default function Research() {
  const [data, setData] = useState<ResearchOverview | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [tab, setTab] = useState('models')
  const [selectedModel, setSelectedModel] = useState(0)
  const [busy, setBusy] = useState(false)
  const [experimentModel, setExperimentModel] = useState('Random Forest')

  const load = async () => {
    const response = await api<ResearchOverview>('/research/overview')
    const bestIndex = response.metrics?.models.findIndex((item) => item.model === response.metrics?.best_model) ?? -1
    setSelectedModel(bestIndex >= 0 ? bestIndex : 0)
    setData(response)
  }

  useEffect(() => {
    load()
      .catch((err) => setError(err instanceof ApiError ? err.message : 'Unable to load the Research Centre.'))
      .finally(() => setLoading(false))
  }, [])

  const models = data?.metrics?.models ?? []
  const best = useMemo(() => models.find((item) => item.model === data?.metrics?.best_model) || models[0], [models, data])
  const active = models[selectedModel] || best

  const runExperiment = async () => {
    if (!data?.dataset) return
    setBusy(true)
    setError(null)
    try {
      await api('/research/experiments', {
        method: 'POST',
        body: { dataset_id: data.dataset.id, model: experimentModel },
      })
      await load()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'The experiment could not be executed.')
    } finally {
      setBusy(false)
    }
  }

  const researchReport = async (experimentId?: string) => {
    setBusy(true)
    setError(null)
    try {
      const query = experimentId ? `?experiment_id=${experimentId}` : ''
      const response = await api<{ report: { id: string } }>(`/reports/research${query}`, { method: 'POST', body: {} })
      await download(`/reports/${response.report.id}/download`, 'aurasense-research-report.pdf')
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Unable to generate the research report.')
    } finally {
      setBusy(false)
    }
  }

  if (loading) return <LoadingBlock label="Loading research metrics" />
  if (!data) return <Notice tone="danger">{error || 'Research data unavailable.'}</Notice>

  const summary = data.dataset_summary
  const metrics = data.metrics
  const classDistribution = summary?.class_distribution || metrics?.class_distribution || {}
  const totalWindows = summary?.windows || metrics?.windows || 0

  return (
    <div>
      <PageHeader
        eyebrow="Research Centre"
        title="The evidence behind the estimate."
        description="Participant-independent evaluation on WESAD: model comparison, confusion matrices, per-participant results, permutation importance and reproducible experiments."
        actions={
          <>
            <a href={data.dataset_url} target="_blank" rel="noreferrer" className="btn btn-secondary">
              <Database size={14} /> Dataset source
            </a>
            <button onClick={() => researchReport()} disabled={busy} className="btn btn-primary">
              <FileDown size={14} /> {busy ? 'Working…' : 'Research report'}
            </button>
          </>
        }
      />

      {error && (
        <Notice tone="danger" className="mb-4">
          {error}
        </Notice>
      )}

      {!data.model.available && (
        <Notice tone="warning" className="mb-4" title="Model artifact not found">
          Run <span className="mono">python -m ml.wesad_extract</span> and <span className="mono">python -m ml.train</span> in
          the backend to create the feature table and persist the model.
        </Notice>
      )}

      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <Stat
          label="Participants held out"
          value={summary?.participant_count ?? data.model.participants?.length ?? '—'}
          unit="people"
          meta="Entire participants excluded from training in each fold"
          icon={<Users size={15} />}
        />
        <Stat label="Analysed windows" value={totalWindows.toLocaleString()} unit="60s windows" meta="30-second stride · labels 1, 2, 3 only" />
        <Stat
          label="Best model"
          value={best?.model === 'Support Vector Machine' ? 'SVM' : best?.model?.replace('Gradient Boosting', 'Gradient boost') || '—'}
          meta={<Badge tone="sage">{metrics?.evaluation_strategy || 'Grouped CV'}</Badge>}
          icon={<Microscope size={15} />}
          tone="sage"
        />
        <Stat
          label="Balanced accuracy"
          value={best ? `${(best.metrics.balanced_accuracy * 100).toFixed(1)}%` : '—'}
          meta={`Macro F1 ${best ? (best.metrics.f1_macro * 100).toFixed(1) : '—'}% · ${best?.metrics.n_test_windows ?? 0} test windows`}
          icon={<Activity size={15} />}
          tone="amber"
        />
      </div>

      <div className="mt-4 grid gap-4 xl:grid-cols-[1.55fr_1fr]">
        <Card className="p-5 md:p-6">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <SectionLabel>Evaluation</SectionLabel>
              <h2 className="mt-1 font-display text-xl text-forest">Model comparison</h2>
            </div>
            <Tabs
              value={tab}
              onChange={setTab}
              tabs={[
                { key: 'models', label: 'Comparison' },
                { key: 'classes', label: 'Per class' },
                { key: 'subjects', label: 'By participant' },
              ]}
            />
          </div>

          {tab === 'models' && (
            <>
              <div className="mt-4 overflow-x-auto">
                <table className="w-full min-w-[560px] text-left text-[11.5px]">
                  <thead>
                    <tr className="border-y border-line bg-[#FAFAF4] text-[9px] uppercase tracking-[0.12em] text-muted">
                      <th className="px-3 py-2 font-medium">Model</th>
                      <th className="px-3 py-2 font-medium">Accuracy</th>
                      <th className="px-3 py-2 font-medium">Balanced</th>
                      <th className="px-3 py-2 font-medium">Macro F1</th>
                      <th className="px-3 py-2 font-medium">Subject bal.</th>
                      <th className="px-3 py-2 font-medium">SD</th>
                    </tr>
                  </thead>
                  <tbody>
                    {models.map((model, index) => (
                      <tr
                        key={model.model}
                        onClick={() => setSelectedModel(index)}
                        className={`cursor-pointer border-b border-line/70 transition ${
                          selectedModel === index ? 'bg-[#F3F5EA]' : 'hover:bg-[#FBFAF3]'
                        }`}
                      >
                        <td className="px-3 py-2.5">
                          <div className="flex items-center gap-2">
                            <span className="font-medium text-charcoal">{model.model}</span>
                            {model.model === data.metrics?.best_model && <Badge tone="sage">Best</Badge>}
                          </div>
                        </td>
                        <td className="tabular px-3 py-2.5 text-charcoal">{(model.metrics.accuracy * 100).toFixed(1)}%</td>
                        <td className="tabular px-3 py-2.5 text-charcoal">{(model.metrics.balanced_accuracy * 100).toFixed(1)}%</td>
                        <td className="tabular px-3 py-2.5 text-charcoal">{(model.metrics.f1_macro * 100).toFixed(1)}%</td>
                        <td className="tabular px-3 py-2.5 text-muted">{(model.mean_subject_balanced_accuracy * 100).toFixed(1)}%</td>
                        <td className="tabular px-3 py-2.5 text-muted">{num(model.metrics.balanced_accuracy_std, 3)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <div className="mt-4">
                <ModelBars models={models} />
              </div>
              <p className="mt-2 text-[10px] leading-relaxed text-muted">
                Balanced accuracy and macro F1 account for the class imbalance (neutral windows are more frequent). Select a
                row to view its confusion matrix.
              </p>
            </>
          )}

          {tab === 'classes' && active && (
            <div className="mt-4">
              <p className="mb-3 text-[11px] text-muted">Selected model: <span className="font-medium text-charcoal">{active.model}</span></p>
              <div className="overflow-x-auto">
                <table className="w-full min-w-[420px] text-left text-[11.5px]">
                  <thead>
                    <tr className="border-y border-line text-[9px] uppercase tracking-[0.1em] text-muted">
                      <th className="px-2 py-2 font-medium">Class</th>
                      <th className="px-2 py-2 font-medium">Precision</th>
                      <th className="px-2 py-2 font-medium">Recall</th>
                      <th className="px-2 py-2 font-medium">F1</th>
                      <th className="px-2 py-2 font-medium">Support</th>
                    </tr>
                  </thead>
                  <tbody>
                    {Object.entries(active.metrics.per_class).map(([name, value]) => (
                      <tr key={name} className="border-b border-line/60">
                        <td className="px-2 py-2 capitalize text-charcoal">{name}</td>
                        <td className="tabular px-2 py-2 text-muted">{(value.precision * 100).toFixed(1)}%</td>
                        <td className="tabular px-2 py-2 text-muted">{(value.recall * 100).toFixed(1)}%</td>
                        <td className="tabular px-2 py-2 text-muted">{(value.f1 * 100).toFixed(1)}%</td>
                        <td className="tabular px-2 py-2 text-muted">{value.support}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <p className="mt-3 text-[10.5px] leading-relaxed text-muted">
                Amusement is the smallest class and is most often confused with neutral. Stress recall is relatively high,
                but false positives remain possible — an important limitation for any real-world use.
              </p>
            </div>
          )}

          {tab === 'subjects' && active && (
            <div className="mt-4 max-h-[360px] overflow-auto">
              <table className="w-full text-left text-[11px]">
                <thead className="sticky top-0 bg-paper">
                  <tr className="border-y border-line text-[9px] uppercase tracking-[0.1em] text-muted">
                    <th className="px-2 py-2 font-medium">Participant</th>
                    <th className="px-2 py-2 font-medium">Accuracy</th>
                    <th className="px-2 py-2 font-medium">Balanced</th>
                    <th className="px-2 py-2 font-medium">Windows</th>
                  </tr>
                </thead>
                <tbody>
                  {Object.entries(active.per_subject || {}).map(([subject, value]) => (
                    <tr key={subject} className="border-b border-line/60">
                      <td className="px-2 py-1.5 text-charcoal">{subject}</td>
                      <td className="tabular px-2 py-1.5 text-muted">{value.accuracy != null ? `${(value.accuracy * 100).toFixed(1)}%` : '—'}</td>
                      <td className="tabular px-2 py-1.5 text-muted">
                        {'balanced_accuracy' in value ? `${(value.balanced_accuracy * 100).toFixed(1)}%` : '—'}
                      </td>
                      <td className="tabular px-2 py-1.5 text-muted">{value.windows}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Card>

        <div className="space-y-4">
          <Card className="p-5">
            <div className="flex items-start justify-between">
              <div>
                <SectionLabel>Confusion matrix</SectionLabel>
                <h2 className="mt-1 font-display text-lg text-forest">{active?.model || 'Model'}</h2>
              </div>
              {active && <Badge>{active.metrics.n_test_windows} test</Badge>}
            </div>
            {active ? (
              <>
                <div className="mt-3">
                  <ConfusionMatrix matrix={active.metrics.confusion_matrix} classes={CLASSES} />
                </div>
                <p className="mt-2 text-[9.5px] leading-relaxed text-muted">
                  Rows are actual WESAD conditions; columns are model predictions. Aggregated across held-out folds.
                </p>
              </>
            ) : (
              <EmptyState title="No metrics" description="Training output is not available." />
            )}
          </Card>

          <Card className="p-5">
            <SectionLabel>Feature importance</SectionLabel>
            <h2 className="mt-1 font-display text-lg text-forest">What the model relies on</h2>
            <p className="mt-1.5 text-[10.5px] leading-relaxed text-muted">
              Permutation importance after training. Correlated features can share credit.
            </p>
            <div className="mt-3">
              {data.metrics?.feature_importance?.length ? (
                <ImportanceBars
                  items={data.metrics.feature_importance.map((item) => ({ feature: featureName(item.feature), share: item.share }))}
                  limit={9}
                />
              ) : (
                <p className="text-[11px] text-muted">Not available.</p>
              )}
            </div>
          </Card>

          <Card className="p-5">
            <div className="flex items-start justify-between">
              <div>
                <SectionLabel>Dataset</SectionLabel>
                <h2 className="mt-1 font-display text-lg text-forest">WESAD</h2>
              </div>
              <Database size={15} className="text-sage" />
            </div>
            <p className="mt-2 text-[10.5px] leading-relaxed text-muted">{data.dataset?.description}</p>
            <div className="mt-3">
              {Object.entries(classDistribution).map(([name, count]) => {
                const share = totalWindows ? (count / totalWindows) * 100 : 0
                return (
                  <div key={name} className="mb-1.5">
                    <div className="flex items-center justify-between text-[10.5px]">
                      <span className="capitalize text-charcoal">{name}</span>
                      <span className="tabular text-muted">{count} · {share.toFixed(0)}%</span>
                    </div>
                    <ProgressBar
                      className="mt-0.5"
                      value={share}
                      tone={name === 'stress' ? 'coral' : name === 'amusement' ? 'amber' : 'sage'}
                    />
                  </div>
                )
              })}
            </div>
            <div className="mt-3 space-y-1 border-t border-line pt-2 text-[9.5px] leading-relaxed text-muted">
              {summary?.window_seconds && <p>Window {summary.window_seconds}s · stride {summary.step_seconds}s</p>}
              {summary?.excluded_labels && <p>Excluded: {summary.excluded_labels}</p>}
              <p>Source: {data.dataset?.source}</p>
              <a href={data.paper_url} target="_blank" rel="noreferrer" className="inline-block text-forest underline underline-offset-2">
                Original WESAD paper
              </a>
            </div>
          </Card>
        </div>
      </div>

      <div className="mt-4 grid gap-4 xl:grid-cols-[1.4fr_1fr]">
        <Card className="p-5 md:p-6">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <SectionLabel>Experiments</SectionLabel>
              <h2 className="mt-1 font-display text-lg text-forest">Reproducible runs</h2>
            </div>
            {data.can_run_experiments ? (
              <div className="flex items-center gap-2">
                <select className="field !w-auto !py-1.5 text-[11px]" value={experimentModel} onChange={(event) => setExperimentModel(event.target.value)}>
                  <option>Random Forest</option>
                  <option>Support Vector Machine</option>
                  <option>Gradient Boosting</option>
                </select>
                <button onClick={runExperiment} disabled={busy} className="btn btn-primary px-3 py-1.5 text-[11px]">
                  <Play size={12} /> Run
                </button>
              </div>
            ) : (
              <Badge tone="amber">Researcher access required</Badge>
            )}
          </div>

          {data.experiments.length ? (
            <div className="mt-3 space-y-2">
              {data.experiments.map((experiment: Experiment) => {
                const value = experiment.metrics as { balanced_accuracy?: number; f1_macro?: number; accuracy?: number }
                return (
                  <div key={experiment.id} className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-line bg-[#FBFAF4] px-3.5 py-2.5">
                    <div>
                      <p className="text-[11.5px] font-medium text-charcoal">{experiment.model_type}</p>
                      <p className="mt-0.5 text-[9.5px] text-muted">
                        {experiment.evaluation_strategy} · {dateTime(experiment.created_at)}
                      </p>
                    </div>
                    <div className="flex items-center gap-4">
                      <div className="text-right">
                        <p className="text-[9px] uppercase tracking-[0.1em] text-muted">Balanced</p>
                        <p className="tabular text-[11px] text-charcoal">
                          {value.balanced_accuracy != null ? `${(value.balanced_accuracy * 100).toFixed(1)}%` : '—'}
                        </p>
                      </div>
                      <div className="text-right">
                        <p className="text-[9px] uppercase tracking-[0.1em] text-muted">F1</p>
                        <p className="tabular text-[11px] text-charcoal">{value.f1_macro != null ? `${(value.f1_macro * 100).toFixed(1)}%` : '—'}</p>
                      </div>
                      {data.can_run_experiments && (
                        <button onClick={() => researchReport(experiment.id)} className="btn btn-ghost px-2 py-1 text-[10px]">
                          <FileDown size={12} /> PDF
                        </button>
                      )}
                    </div>
                  </div>
                )
              })}
            </div>
          ) : (
            <div className="mt-3">
              <EmptyState icon={<FlaskConical size={18} />} title="No experiments recorded" description="Researchers can execute a grouped evaluation and store its metrics." />
            </div>
          )}
        </Card>

        <Card className="p-5">
          <SectionLabel>Limitations</SectionLabel>
          <h2 className="mt-1 font-display text-lg text-forest">What this evaluation cannot tell you</h2>
          <ul className="mt-3 space-y-2">
            {(metrics?.limitations || []).map((item) => (
              <li key={item} className="flex gap-2 text-[10.5px] leading-relaxed text-muted">
                <span className="mt-1 h-1 w-1 shrink-0 rounded-full bg-amber" />
                {item}
              </li>
            ))}
            <li className="flex gap-2 text-[10.5px] leading-relaxed text-muted">
              <span className="mt-1 h-1 w-1 shrink-0 rounded-full bg-amber" />
              Laboratory conditions differ from daily life; demographic and device diversity is limited.
            </li>
          </ul>
          <p className="mt-3 border-t border-line pt-2 text-[9.5px] leading-relaxed text-muted">
            {data.citation}
          </p>
        </Card>
      </div>

      <Notice tone="warning" className="mt-4" title="Scientific responsibility">
        These metrics describe model behaviour on a small laboratory dataset. They are not evidence of clinical validity,
        and they do not establish that an individual reading is correct.
      </Notice>
    </div>
  )
}
