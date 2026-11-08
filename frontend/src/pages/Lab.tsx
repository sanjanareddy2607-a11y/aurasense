import { useEffect, useRef, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { ArrowRight, FileUp, FlaskConical, Info, ScanLine, Upload } from 'lucide-react'
import { api, ApiError } from '../lib/api'
import type { Analysis, Dataset, Inspection } from '../types'
import { Badge, Card, EmptyState, Notice, PageHeader, ProgressBar, QualityPill, SectionLabel } from '../components/ui'
import { Waveform, CHART_COLORS } from '../components/charts'
import { duration } from '../lib/format'

interface UploadResponse {
  analysis: Analysis
  dataset: Dataset
  inspection: Inspection
}

interface DatasetPreview {
  dataset: Dataset
  preview: Record<string, (number | null)[]>
  channels: { key: string; label: string; column: string }[]
  sampling_rate: number
  duration_seconds: number
  windows: number
  quality: { score: number | null; grade: string | null; issues: { code: string; severity: string; message: string }[] }
  rows: number
  columns: string[]
}

const CHANNEL_COLORS: Record<string, string> = {
  ecg: CHART_COLORS.forest,
  eda: CHART_COLORS.amber,
  resp: CHART_COLORS.sage,
  bvp: CHART_COLORS.olive,
  temp: CHART_COLORS.coral,
  acc: CHART_COLORS.olive,
  emg: CHART_COLORS.olive,
}

export default function Lab() {
  const navigate = useNavigate()
  const inputRef = useRef<HTMLInputElement>(null)
  const [file, setFile] = useState<File | null>(null)
  const [title, setTitle] = useState('')
  const [samplingRate, setSamplingRate] = useState('')
  const [dragging, setDragging] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [result, setResult] = useState<UploadResponse | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [datasets, setDatasets] = useState<Dataset[]>([])
  const [preview, setPreview] = useState<DatasetPreview | null>(null)
  const [previewBusy, setPreviewBusy] = useState<string | null>(null)
  const [channel, setChannel] = useState<string>('')
  const [analyseBusy, setAnalyseBusy] = useState<string | null>(null)

  useEffect(() => {
    api<{ datasets: Dataset[] }>('/datasets')
      .then((response) => setDatasets(response.datasets.filter((dataset) => !dataset.is_reference)))
      .catch(() => undefined)
  }, [])

  const chooseFile = (selected: File | null) => {
    setFile(selected)
    setResult(null)
    setError(null)
    if (selected && !title) setTitle(selected.name.replace(/\.[^.]+$/, ''))
  }

  const upload = async () => {
    if (!file) return
    setUploading(true)
    setError(null)
    setResult(null)
    try {
      const form = new FormData()
      form.append('file', file)
      if (title.trim()) form.append('title', title.trim())
      if (samplingRate.trim()) form.append('sampling_rate', samplingRate.trim())
      const response = await api<UploadResponse>('/analysis/upload', { method: 'POST', form })
      setResult(response)
      setChannel(Object.keys(response.inspection.preview)[0] || '')
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'The file could not be analysed.')
    } finally {
      setUploading(false)
    }
  }

  const loadPreview = async (dataset: Dataset) => {
    setPreviewBusy(dataset.id)
    setError(null)
    try {
      const response = await api<DatasetPreview>(`/datasets/${dataset.id}/preview`)
      setPreview(response)
      setChannel(Object.keys(response.preview)[0] || '')
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Unable to preview this dataset.')
    } finally {
      setPreviewBusy(null)
    }
  }

  const analyseDataset = async (dataset: Dataset) => {
    setAnalyseBusy(dataset.id)
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
      setAnalyseBusy(null)
    }
  }

  const inspection = result?.inspection
  const previewSource = inspection
    ? { preview: inspection.preview, channels: inspection.channels }
    : preview
      ? { preview: preview.preview, channels: preview.channels }
      : null
  const previewKeys = previewSource ? Object.keys(previewSource.preview) : []
  const activeKey = previewKeys.includes(channel) ? channel : previewKeys[0]
  const activeChannel = previewSource?.channels.find((item) => item.key === activeKey)

  return (
    <div>
      <PageHeader
        eyebrow="BioSignal Lab"
        title="Bring your own signal."
        description="Upload a CSV with time-series channels. AuraSense detects channels and sampling rate, scores signal quality, extracts interpretable features and runs the same model used for WESAD."
        actions={
          <span className="chip">
            <FlaskConical size={11} /> CSV · TSV · TXT
          </span>
        }
      />

      {error && (
        <Notice tone="danger" className="mb-4">
          {error}
        </Notice>
      )}

      <div className="grid gap-4 xl:grid-cols-[1.35fr_1fr]">
        <div className="space-y-4">
          <Card className="p-5 md:p-6">
            <div className="flex items-start justify-between">
              <div>
                <SectionLabel>New upload</SectionLabel>
                <h2 className="mt-1 font-display text-xl text-forest">Add a recording</h2>
              </div>
              <FileUp size={17} className="text-sage" />
            </div>

            <div
              onDragOver={(event) => {
                event.preventDefault()
                setDragging(true)
              }}
              onDragLeave={() => setDragging(false)}
              onDrop={(event) => {
                event.preventDefault()
                setDragging(false)
                const dropped = event.dataTransfer.files?.[0]
                if (dropped) chooseFile(dropped)
              }}
              onClick={() => inputRef.current?.click()}
              className={`mt-4 flex cursor-pointer flex-col items-center justify-center gap-2 rounded-2xl border border-dashed px-6 py-10 text-center transition ${
                dragging ? 'border-forest bg-[#F1F3E9]' : 'border-[#D5D2C3] bg-[#FAFAF3] hover:border-sage'
              }`}
            >
              <span className="flex h-11 w-11 items-center justify-center rounded-full bg-[#EEF1E5] text-[#4C6449]">
                <Upload size={18} />
              </span>
              <p className="text-[12.5px] font-medium text-charcoal">
                {file ? file.name : 'Drop a CSV here, or choose a file'}
              </p>
              <p className="text-[10.5px] text-muted">
                {file
                  ? `${(file.size / 1024).toFixed(0)} KB · ready to analyse`
                  : 'Up to 12 MB · header row required · at least 20 rows'}
              </p>
              <input
                ref={inputRef}
                type="file"
                accept=".csv,.tsv,.txt"
                className="hidden"
                onChange={(event) => chooseFile(event.target.files?.[0] ?? null)}
              />
            </div>

            <div className="mt-4 grid gap-3 sm:grid-cols-[1.4fr_0.8fr]">
              <div>
                <label className="label" htmlFor="title">
                  Analysis title
                </label>
                <input
                  id="title"
                  className="field"
                  value={title}
                  onChange={(event) => setTitle(event.target.value)}
                  placeholder="e.g. Evening resting recording"
                />
              </div>
              <div>
                <label className="label" htmlFor="fs">
                  Sampling rate (optional)
                </label>
                <input
                  id="fs"
                  className="field"
                  inputMode="decimal"
                  value={samplingRate}
                  onChange={(event) => setSamplingRate(event.target.value)}
                  placeholder="auto"
                />
              </div>
            </div>

            <div className="mt-4 flex flex-wrap items-center gap-2">
              <button onClick={upload} disabled={!file || uploading} className="btn btn-primary">
                <ScanLine size={14} /> {uploading ? 'Analysing…' : 'Analyse signal'}
              </button>
              {file && (
                <button
                  onClick={() => {
                    chooseFile(null)
                    setTitle('')
                    if (inputRef.current) inputRef.current.value = ''
                  }}
                  className="btn btn-ghost"
                >
                  Clear
                </button>
              )}
              <span className="text-[10px] text-muted">Signals are stored locally on this server.</span>
            </div>
          </Card>

          {inspection && (
            <Card className="p-5 md:p-6">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <SectionLabel>Inspection</SectionLabel>
                  <h2 className="mt-1 font-display text-lg text-forest">{inspection.filename}</h2>
                </div>
                <QualityPill score={inspection.quality.score} grade={inspection.quality.grade} />
              </div>

              <div className="mt-4 grid grid-cols-2 gap-2 sm:grid-cols-4">
                {[
                  { label: 'Rows', value: inspection.rows.toLocaleString() },
                  { label: 'Duration', value: duration(inspection.duration_seconds) },
                  { label: 'Sampling', value: `${inspection.sampling_rate} Hz` },
                  { label: 'Windows', value: inspection.windows },
                ].map((item) => (
                  <div key={item.label} className="rounded-lg bg-[#F6F5ED] px-3 py-2">
                    <p className="text-[9px] uppercase tracking-[0.1em] text-muted">{item.label}</p>
                    <p className="mt-0.5 text-[12px] font-medium text-charcoal">{item.value}</p>
                  </div>
                ))}
              </div>

              <div className="mt-4">
                <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
                  <div className="flex flex-wrap gap-1.5">
                    {previewKeys.map((key) => (
                      <button
                        key={key}
                        onClick={() => setChannel(key)}
                        className={`rounded-full px-2.5 py-1 text-[10px] font-medium capitalize transition ${
                          activeKey === key ? 'bg-forest text-[#F4F3E9]' : 'border border-line bg-paper text-muted hover:text-forest'
                        }`}
                      >
                        {previewSource?.channels.find((item) => item.key === key)?.label || key}
                      </button>
                    ))}
                  </div>
                  <span className="text-[9.5px] text-muted">
                    {activeChannel?.column ? `mapped from “${activeChannel.column}”` : 'detected channel'}
                  </span>
                </div>
                {activeKey && (
                  <div className="rounded-xl border border-line bg-[#FBFAF4] px-3 py-2">
                    <Waveform
                      values={previewSource?.preview[activeKey] || []}
                      color={CHANNEL_COLORS[activeKey] || CHART_COLORS.forest}
                      height={120}
                      label={`${activeChannel?.label || activeKey} · first ${inspection.preview_seconds}s`}
                    />
                  </div>
                )}
              </div>

              <div className="mt-4 grid gap-3 sm:grid-cols-2">
                <div>
                  <p className="text-[10px] font-medium uppercase tracking-[0.1em] text-muted">Detected channels</p>
                  <div className="mt-2 flex flex-wrap gap-1.5">
                    {inspection.channels.map((item) => (
                      <Badge key={item.key} tone="sage">
                        {item.label}
                      </Badge>
                    ))}
                  </div>
                </div>
                <div>
                  <p className="text-[10px] font-medium uppercase tracking-[0.1em] text-muted">Data notes</p>
                  <ul className="mt-2 space-y-1 text-[10.5px] leading-relaxed text-muted">
                    <li>· Sampling rate {inspection.sampling_rate_source === 'header' ? 'read from a time column' : 'assumed or supplied'}.</li>
                    {inspection.unrecognised_columns.length > 0 && (
                      <li>· Ignored columns: {inspection.unrecognised_columns.join(', ')}</li>
                    )}
                    {Object.entries(inspection.missing_values).slice(0, 2).map(([key, value]) => (
                      <li key={key}>· {value} missing values in {key}</li>
                    ))}
                  </ul>
                </div>
              </div>

              {inspection.quality.issues.length > 0 && (
                <div className="mt-3 rounded-lg bg-[#F8EFDF] px-3 py-2 text-[10.5px] leading-relaxed text-[#8A6526]">
                  {inspection.quality.issues.map((issue) => issue.message).join(' ')}
                </div>
              )}

              {result && (
                <div className="mt-4 flex flex-wrap items-center justify-between gap-3 border-t border-line pt-3">
                  <div>
                    <p className="text-[11.5px] font-medium text-charcoal">{result.analysis.predicted_label}</p>
                    <p className="text-[10px] text-muted">
                      {result.analysis.confidence != null ? `${Math.round(result.analysis.confidence * 100)}% confidence` : 'No probability'} ·{' '}
                      {result.analysis.class_probabilities.stress != null
                        ? `${(result.analysis.class_probabilities.stress * 100).toFixed(0)}% stress-associated`
                        : '—'}
                    </p>
                  </div>
                  <Link to={`/app/analysis/${result.analysis.id}`} className="btn btn-primary px-3.5 py-2 text-[11px]">
                    Open analysis <ArrowRight size={13} />
                  </Link>
                </div>
              )}
            </Card>
          )}

          {preview && (
            <Card className="p-5">
              <div className="flex flex-wrap items-start justify-between gap-2">
                <div>
                  <SectionLabel>Dataset preview</SectionLabel>
                  <h2 className="mt-1 font-display text-lg text-forest">{preview.dataset.name}</h2>
                </div>
                <div className="flex items-center gap-2">
                  <QualityPill score={preview.quality.score} grade={preview.quality.grade} />
                  <button onClick={() => setPreview(null)} className="btn btn-ghost px-2 py-1 text-[10px]">
                    Close
                  </button>
                </div>
              </div>
              <div className="mt-3 flex flex-wrap gap-1.5">
                {Object.keys(preview.preview).map((key) => (
                  <button
                    key={key}
                    onClick={() => setChannel(key)}
                    className={`rounded-full px-2.5 py-1 text-[10px] capitalize transition ${
                      activeKey === key ? 'bg-forest text-[#F4F3E9]' : 'border border-line bg-paper text-muted'
                    }`}
                  >
                    {preview.channels.find((item) => item.key === key)?.label || key}
                  </button>
                ))}
              </div>
              {activeKey && (
                <div className="mt-2 rounded-xl border border-line bg-[#FBFAF4] px-3 py-2">
                  <Waveform values={preview.preview[activeKey] || []} color={CHANNEL_COLORS[activeKey] || CHART_COLORS.forest} height={110} />
                </div>
              )}
              <div className="mt-2 flex justify-between text-[10px] text-muted">
                <span>{preview.rows.toLocaleString()} rows · {duration(preview.duration_seconds)} · {preview.sampling_rate} Hz</span>
                <button
                  onClick={() => analyseDataset(preview.dataset)}
                  disabled={analyseBusy === preview.dataset.id}
                  className="font-medium text-forest"
                >
                  {analyseBusy === preview.dataset.id ? 'Analysing…' : 'Analyse this dataset →'}
                </button>
              </div>
            </Card>
          )}
        </div>

        <div className="space-y-4">
          <Card className="p-5">
            <SectionLabel>Accepted columns</SectionLabel>
            <h2 className="mt-1 font-display text-lg text-forest">Automatic mapping</h2>
            <p className="mt-1.5 text-[10.5px] leading-relaxed text-muted">
              Column names are matched case-insensitively, including common aliases. Missing channels are handled with
              explicit defaults and flagged in quality.
            </p>
            <div className="mt-3 space-y-1.5 text-[11px]">
              {[
                ['ECG / EKG', 'Heart rate, HRV'],
                ['EDA / GSR / SC', 'Skin conductance'],
                ['Resp / Respiration', 'Breathing rate'],
                ['Temp / Temperature', 'Skin temperature'],
                ['EMG', 'Muscle activity'],
                ['ACC_x / ACC_y / ACC_z', 'Movement'],
                ['BVP / PPG', 'Pulse waveform'],
              ].map(([name, use]) => (
                <div key={name} className="flex items-center justify-between gap-3 border-b border-line/60 pb-1.5">
                  <span className="mono text-[10px] text-charcoal">{name}</span>
                  <span className="text-[10px] text-muted">{use}</span>
                </div>
              ))}
            </div>
          </Card>

          <Card className="p-5">
            <SectionLabel>Demonstration datasets</SectionLabel>
            <h2 className="mt-1 font-display text-lg text-forest">Synthetic recordings</h2>
            <div className="mt-3 space-y-2">
              {datasets.map((dataset) => (
                <div key={dataset.id} className="rounded-xl border border-line bg-[#FBFAF4] p-3">
                  <div className="flex items-start justify-between gap-2">
                    <div className="min-w-0">
                      <p className="truncate text-[11.5px] font-medium text-charcoal">{dataset.name}</p>
                      <p className="mt-0.5 text-[9.5px] text-muted">{dataset.source}</p>
                    </div>
                    <Badge tone="amber">Demo</Badge>
                  </div>
                  <div className="mt-2 flex gap-2">
                    <button
                      onClick={() => loadPreview(dataset)}
                      disabled={previewBusy === dataset.id}
                      className="btn btn-secondary px-2.5 py-1 text-[10px]"
                    >
                      {previewBusy === dataset.id ? 'Loading…' : 'Preview'}
                    </button>
                    <button
                      onClick={() => analyseDataset(dataset)}
                      disabled={analyseBusy === dataset.id}
                      className="btn btn-ghost px-2.5 py-1 text-[10px]"
                    >
                      {analyseBusy === dataset.id ? 'Analysing…' : 'Analyse'}
                    </button>
                  </div>
                </div>
              ))}
              {!datasets.length && <EmptyState title="No demonstration datasets" description="They are created when demo data is seeded." />}
            </div>
          </Card>

          <Notice tone="info" title="Privacy & quality">
            <span className="inline-flex items-start gap-1.5">
              <Info size={12} className="mt-0.5 shrink-0" />
              Uploaded files stay on this server. Poor electrode contact, motion and short recordings reduce quality — the
              app shows this before you interpret an estimate.
            </span>
          </Notice>

          <Card className="p-5">
            <SectionLabel>Quality scale</SectionLabel>
            <div className="mt-3 space-y-2.5">
              {[
                { label: 'Good', range: '80–100', tone: 'sage', body: 'Stable channels and plausible ranges.' },
                { label: 'Fair', range: '55–79', tone: 'amber', body: 'Some noise or missing channels; interpret cautiously.' },
                { label: 'Poor', range: '0–54', tone: 'coral', body: 'Likely unreliable; results are suppressed or flagged.' },
              ].map((item) => (
                <div key={item.label}>
                  <div className="flex items-center justify-between text-[11px]">
                    <span className="text-charcoal">{item.label}</span>
                    <span className="tabular text-[10px] text-muted">{item.range}</span>
                  </div>
                  <ProgressBar className="mt-1" value={item.label === 'Good' ? 90 : item.label === 'Fair' ? 68 : 35} tone={item.tone as 'sage' | 'amber' | 'coral'} />
                  <p className="mt-1 text-[9.5px] text-muted">{item.body}</p>
                </div>
              ))}
            </div>
          </Card>
        </div>
      </div>
    </div>
  )
}
