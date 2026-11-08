import { useCallback, useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { Activity, ArrowRight, CircleStop, Pause, Play, RefreshCw, Waves } from 'lucide-react'
import { api, ApiError } from '../lib/api'
import type { Analysis, Scenario, TickResponse } from '../types'
import { Badge, Card, EmptyState, Notice, PageHeader, ProgressBar, QualityPill, SectionLabel, Spinner } from '../components/ui'
import { ProbabilityBars, TrendChart, Waveform, CHART_COLORS } from '../components/charts'
import { duration, stressPercent } from '../lib/format'

export default function Monitor() {
  const [scenarios, setScenarios] = useState<Scenario[]>([])
  const [scenario, setScenario] = useState('resting')
  const [sessionId, setSessionId] = useState<string | null>(null)
  const [status, setStatus] = useState<'idle' | 'active' | 'paused'>('idle')
  const [payload, setPayload] = useState<TickResponse | null>(null)
  const [result, setResult] = useState<Analysis | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const busyRef = useRef(false)

  useEffect(() => {
    api<{ scenarios: Scenario[] }>('/sessions/scenarios')
      .then((response) => {
        setScenarios(response.scenarios)
        setScenario((current) => (response.scenarios.some((s) => s.key === current) ? current : response.scenarios[0]?.key || 'resting'))
      })
      .catch(() => setError('Unable to load simulation scenarios.'))
  }, [])

  const tick = useCallback(
    async (id: string) => {
      if (busyRef.current) return
      busyRef.current = true
      try {
        const response = await api<TickResponse>(`/sessions/${id}/tick`, { method: 'POST', body: { tick_seconds: 5 } })
        setPayload(response)
      } catch (err) {
        setError(err instanceof ApiError ? err.message : 'The simulated stream stopped responding.')
        setStatus('paused')
      } finally {
        busyRef.current = false
      }
    },
    [],
  )

  useEffect(() => {
    if (status !== 'active' || !sessionId) return
    const interval = window.setInterval(() => void tick(sessionId), 3400)
    return () => window.clearInterval(interval)
  }, [status, sessionId, tick])

  const start = async () => {
    setBusy(true)
    setError(null)
    setResult(null)
    setPayload(null)
    try {
      const response = await api<{ session: { id: string } }>('/sessions', { method: 'POST', body: { scenario } })
      setSessionId(response.session.id)
      setStatus('active')
      await tick(response.session.id)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Unable to start the simulated session.')
    } finally {
      setBusy(false)
    }
  }

  const pause = async () => {
    if (!sessionId) return
    try {
      await api(`/sessions/${sessionId}/pause`, { method: 'POST' })
      setStatus('paused')
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Unable to pause the session.')
    }
  }

  const resume = async () => {
    if (!sessionId) return
    try {
      await api(`/sessions/${sessionId}/resume`, { method: 'POST' })
      setStatus('active')
      await tick(sessionId)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Unable to resume the session.')
    }
  }

  const stop = async () => {
    if (!sessionId) return
    setBusy(true)
    try {
      const response = await api<{ analysis: Analysis }>(`/sessions/${sessionId}/stop`, { method: 'POST' })
      setResult(response.analysis)
      setStatus('idle')
      setSessionId(null)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Unable to finish the session.')
    } finally {
      setBusy(false)
    }
  }

  const activeScenario = scenarios.find((item) => item.key === scenario)
  const prediction = payload?.prediction
  const available = prediction?.available
  const elapsed = payload?.elapsed_seconds ?? 0
  const target = 60
  const signal = payload?.signal
  const history = payload?.prediction_history ?? []

  return (
    <div>
      <PageHeader
        eyebrow="Live Monitor"
        title="Watch a signal become an estimate."
        description="A clear, labelled simulation of chest and wrist physiology. Signals are generated on the server, pass through the same preprocessing and feature pipeline as uploaded data, and are never presented as real measurements."
        actions={
          <span className="chip">
            <span className="breathe h-1.5 w-1.5 rounded-full bg-amber" /> Simulated stream
          </span>
        }
      />

      {error && (
        <Notice tone="danger" className="mb-4">
          {error}
        </Notice>
      )}

      {result && (
        <Notice tone="success" className="mb-4" title="Session completed and analysed">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <span>
              {result.predicted_label} · {result.confidence ? `${Math.round(result.confidence * 100)}% confidence` : 'no probability'} ·{' '}
              signal quality {result.quality?.score != null ? `${Math.round(result.quality.score)}/100` : 'not scored'}.
            </span>
            <Link to={`/app/analysis/${result.id}`} className="inline-flex items-center gap-1 font-medium underline underline-offset-2">
              Open full analysis <ArrowRight size={13} />
            </Link>
          </div>
        </Notice>
      )}

      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-5">
        {scenarios.map((item) => (
          <button
            key={item.key}
            disabled={status !== 'idle'}
            onClick={() => setScenario(item.key)}
            className={`rounded-xl border px-3.5 py-3 text-left transition ${
              scenario === item.key ? 'border-forest bg-[#F1F3E9]' : 'border-line bg-paper hover:border-sage'
            } disabled:cursor-not-allowed disabled:opacity-60`}
          >
            <div className="flex items-center justify-between">
              <p className="text-[11.5px] font-medium text-charcoal">{item.label}</p>
              {scenario === item.key && <span className="h-1.5 w-1.5 rounded-full bg-forest" />}
            </div>
            <p className="mt-1 line-clamp-2 text-[10px] leading-relaxed text-muted">{item.description}</p>
          </button>
        ))}
      </div>

      <div className="mt-4 grid gap-4 xl:grid-cols-[1.6fr_1fr]">
        <div className="space-y-4">
          <Card className="p-5">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <SectionLabel>ECG · chest</SectionLabel>
                <h2 className="mt-1 font-display text-lg text-forest">
                  {status === 'idle' && !payload ? 'Awaiting session' : status === 'paused' ? 'Stream paused' : 'Live simulated waveform'}
                </h2>
              </div>
              <div className="flex items-center gap-2">
                {payload && <Badge tone={status === 'active' ? 'good' : 'neutral'}>{status === 'active' ? 'Streaming' : 'Paused'}</Badge>}
                <span className="mono text-[10px] text-muted">{duration(elapsed)} / 60s min.</span>
              </div>
            </div>

            <div className="mt-4 rounded-xl bg-[#F6F6EE] px-3 py-2">
              <Waveform values={signal?.ecg ?? []} color={CHART_COLORS.forest} height={150} label="ECG (simulated)" />
            </div>
            <div className="mt-3 grid gap-2 sm:grid-cols-3">
              {[
                { key: 'eda', label: 'Skin conductance', color: CHART_COLORS.amber, values: signal?.eda ?? [] },
                { key: 'resp', label: 'Respiration', color: CHART_COLORS.sage, values: signal?.resp ?? [] },
                { key: 'motion', label: 'Movement', color: CHART_COLORS.olive, values: signal?.motion ?? [] },
              ].map((channel) => (
                <div key={channel.key} className="rounded-xl border border-line bg-[#FBFAF4] px-2 py-1.5">
                  <Waveform values={channel.values} color={channel.color} height={68} label={channel.label} />
                </div>
              ))}
            </div>
            {payload?.hr_series && payload.hr_series.length > 1 && (
              <div className="mt-3">
                <div className="mb-1 flex items-center justify-between text-[10px] text-muted">
                  <span className="inline-flex items-center gap-1.5">
                    <Waves size={11} /> Instantaneous heart rate
                  </span>
                  <span className="tabular">latest {payload.hr_series[payload.hr_series.length - 1]?.bpm?.toFixed(0) ?? '—'} bpm</span>
                </div>
                <TrendChart
                  data={payload.hr_series.map((point) => ({ label: `${Math.round(point.t)}s`, hr: point.bpm }))}
                  series={[{ key: 'hr', label: 'Heart rate', color: CHART_COLORS.forest }]}
                  height={110}
                />
              </div>
            )}
          </Card>

          <Card className="p-5">
            <div className="flex items-center justify-between">
              <div>
                <SectionLabel>Prediction history</SectionLabel>
                <h2 className="mt-1 font-display text-lg text-forest">How the estimate settles</h2>
              </div>
              <span className="text-[10px] text-muted">{history.length} readings</span>
            </div>
            {history.length ? (
              <div className="mt-3 overflow-x-auto">
                <table className="w-full min-w-[480px] text-left text-[11px]">
                  <thead>
                    <tr className="border-y border-line text-[9px] uppercase tracking-[0.1em] text-muted">
                      <th className="py-2 pr-3 font-medium">Elapsed</th>
                      <th className="py-2 pr-3 font-medium">Estimate</th>
                      <th className="py-2 pr-3 font-medium">Confidence</th>
                      <th className="py-2 pr-3 font-medium">Stress prob.</th>
                      <th className="py-2 font-medium">Quality</th>
                    </tr>
                  </thead>
                  <tbody>
                    {[...history].reverse().map((entry, index) => (
                      <tr key={`${entry.at_seconds}-${index}`} className="border-b border-line/60">
                        <td className="tabular py-1.5 pr-3 text-muted">{duration(entry.at_seconds)}</td>
                        <td className="py-1.5 pr-3 text-charcoal">{entry.label}</td>
                        <td className="tabular py-1.5 pr-3 text-muted">{entry.confidence != null ? `${Math.round(entry.confidence * 100)}%` : '—'}</td>
                        <td className="tabular py-1.5 pr-3 text-muted">{stressPercent(entry.stress_probability)?.toFixed(0) ?? '—'}%</td>
                        <td className="tabular py-1.5 text-muted">{entry.quality_score?.toFixed(0) ?? '—'}/100</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <p className="mt-3 text-[11px] leading-relaxed text-muted">
                Readings appear after enough signal has accumulated. The model needs a full 60-second window before its
                first estimate.
              </p>
            )}
          </Card>
        </div>

        <div className="space-y-4">
          <Card className="p-5">
            <div className="flex items-start justify-between">
              <div>
                <SectionLabel>Session</SectionLabel>
                <h2 className="mt-1 font-display text-xl text-forest">{activeScenario?.label || 'Simulation'}</h2>
              </div>
              <span className="flex h-8 w-8 items-center justify-center rounded-full bg-[#EEF1E5] text-[#4C6449]">
                <Activity size={15} />
              </span>
            </div>
            <p className="mt-1.5 text-[11px] leading-relaxed text-muted">{activeScenario?.expected_pattern}</p>

            <div className="mt-4">
              <div className="mb-1.5 flex items-center justify-between text-[10px] text-muted">
                <span>Window accumulation</span>
                <span className="tabular">{Math.min(100, Math.round((elapsed / target) * 100))}%</span>
              </div>
              <ProgressBar value={Math.min(elapsed, target)} max={target} tone={available ? 'sage' : 'forest'} />
              <p className="mt-1.5 text-[9.5px] text-muted">
                {available ? 'Estimates update every few seconds once a window is available.' : 'Collecting the first full window…'}
              </p>
            </div>

            <div className="mt-4 flex flex-col gap-2">
              {status === 'idle' ? (
                <button onClick={start} disabled={busy} className="btn btn-primary w-full py-2.5">
                  {busy ? <Spinner label="Starting" /> : <><Play size={14} /> Start simulated session</>}
                </button>
              ) : (
                <>
                  <div className="grid grid-cols-2 gap-2">
                    {status === 'active' ? (
                      <button onClick={pause} className="btn btn-secondary py-2.5">
                        <Pause size={13} /> Pause
                      </button>
                    ) : (
                      <button onClick={resume} className="btn btn-secondary py-2.5">
                        <Play size={13} /> Resume
                      </button>
                    )}
                    <button onClick={stop} disabled={busy} className="btn btn-danger py-2.5">
                      <CircleStop size={13} /> Finish
                    </button>
                  </div>
                  <button
                    onClick={() => void tick(sessionId!)}
                    disabled={status !== 'active'}
                    className="btn btn-ghost py-1.5 text-[11px]"
                  >
                    <RefreshCw size={12} /> Pull next reading now
                  </button>
                </>
              )}
            </div>

            <p className="mt-3 border-t border-line pt-3 text-[9.5px] leading-relaxed text-muted">
              Synthetic signals only. No camera, wearable or personal sensor is accessed.
            </p>
          </Card>

          <Card className="p-5">
            <SectionLabel>Current reading</SectionLabel>
            {prediction ? (
              <>
                <div className="mt-2 flex items-start justify-between gap-3">
                  <div>
                    <p className="font-display text-xl leading-tight text-forest">{prediction.predicted_label}</p>
                    <p className="mt-1 text-[10.5px] text-muted">
                      {prediction.confidence != null ? `${Math.round(prediction.confidence * 100)}% confidence` : 'No probability yet'}
                      {prediction.uncertainty != null ? ` · uncertainty ${prediction.uncertainty.toFixed(2)}` : ''}
                    </p>
                  </div>
                  {payload?.quality && <QualityPill score={payload.quality.score} grade={payload.quality.grade} />}
                </div>
                {available ? (
                  <div className="mt-4">
                    <ProbabilityBars probabilities={prediction.class_probabilities} compact />
                  </div>
                ) : (
                  <p className="mt-2 rounded-lg bg-[#F7F3E6] px-3 py-2 text-[10.5px] leading-relaxed text-[#7C6A44]">
                    {prediction.message || 'The model is collecting enough signal to produce a reading.'}
                  </p>
                )}
                <div className="mt-4 flex items-center justify-between border-t border-line pt-3 text-[10px] text-muted">
                  <span>Stress probability</span>
                  <span className="tabular text-charcoal">{stressPercent(prediction.stress_probability)?.toFixed(0) ?? '—'}%</span>
                </div>
                {payload?.quality?.issues?.length ? (
                  <div className="mt-3 space-y-1">
                    {payload.quality.issues.slice(0, 2).map((issue) => (
                      <p key={issue.code} className="text-[10px] leading-relaxed text-[#8A6526]">
                        · {issue.message}
                      </p>
                    ))}
                  </div>
                ) : null}
              </>
            ) : (
              <div className="mt-3">
                <EmptyState title="No reading yet" description="Start a session to see the estimate, uncertainty and signal quality." />
              </div>
            )}
          </Card>
        </div>
      </div>

      <Notice tone="warning" className="mt-4" title="Simulation notice">
        This page illustrates the analysis pipeline with synthetic signals generated deterministically from scenario
        templates. It is not a recording of you and must not be used to infer your health or mental state.
      </Notice>
    </div>
  )
}
