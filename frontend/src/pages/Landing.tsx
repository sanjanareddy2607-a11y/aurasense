import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { ArrowRight, Activity, CheckCircle2, ChevronRight, Lock, Microscope, ShieldCheck, Waves } from 'lucide-react'
import { api } from '../lib/api'
import { Brand } from '../components/Layout'

interface ModelInfo {
  available: boolean
  model_name?: string
  model_version?: string
  cv_strategy?: string
  training_windows?: number
  participants?: string[]
  global_metrics?: { balanced_accuracy: number; accuracy: number; f1_macro: number }
}

function useWaveform(points = 220) {
  return useMemo(() => {
    return Array.from({ length: points }, (_, i) => {
      const t = i / points
      const beat = Math.exp(-Math.pow(((t * 9) % 1 - 0.32) * 11, 2))
      const tWave = 0.32 * Math.exp(-Math.pow(((t * 9) % 1 - 0.62) * 16, 2))
      const baseline = 0.06 * Math.sin(t * Math.PI * 6)
      const noise = 0.015 * Math.sin(t * 720) + 0.008 * Math.cos(t * 431)
      return Number((baseline + beat - tWave + noise).toFixed(4))
    })
  }, [points])
}

export default function Landing() {
  const waveform = useWaveform()
  const [model, setModel] = useState<ModelInfo | null>(null)

  useEffect(() => {
    api<ModelInfo>('/model/info')
      .then(setModel)
      .catch(() => setModel(null))
  }, [])

  const metric = model?.global_metrics?.balanced_accuracy
  const svgPoints = waveform
    .map((value, index) => `${(index / (waveform.length - 1)) * 620},${110 - value * 240}`)
    .join(' ')

  return (
    <div className="min-h-screen bg-ivory text-charcoal">
      <header className="sticky top-0 z-30 border-b border-line/70 bg-ivory/85 backdrop-blur">
        <div className="mx-auto flex h-16 max-w-6xl items-center justify-between px-5">
          <Link to="/" className="flex items-center gap-2.5">
            <span className="flex h-8 w-8 items-center justify-center rounded-[10px] bg-forest">
              <svg viewBox="0 0 32 32" className="h-5 w-5" fill="none" aria-hidden>
                <path
                  d="M4 18c2.2 0 2.2-7 4.4-7s2.2 12 4.4 12 2.2-9 4.4-9 2.2 5 4.4 5 2.2-2 4.4-2"
                  stroke="#DCE5D6"
                  strokeWidth="1.8"
                  strokeLinecap="round"
                />
                <circle cx="25" cy="10" r="2" fill="#D49A45" />
              </svg>
            </span>
            <span className="font-display text-[19px] text-forest">AuraSense</span>
          </Link>
          <nav className="hidden items-center gap-8 text-[12px] text-muted md:flex">
            <a href="#how" className="transition hover:text-forest">
              How it works
            </a>
            <a href="#science" className="transition hover:text-forest">
              Science
            </a>
            <a href="#privacy" className="transition hover:text-forest">
              Privacy
            </a>
          </nav>
          <div className="flex items-center gap-2">
            <Link to="/login" className="btn btn-ghost hidden sm:inline-flex">
              Sign in
            </Link>
            <Link to="/register" className="btn btn-primary">
              Create account <ArrowRight size={14} />
            </Link>
          </div>
        </div>
      </header>

      <main>
        <section className="relative overflow-hidden">
          <div className="pointer-events-none absolute -right-40 -top-40 h-[520px] w-[520px] rounded-full bg-[#E8EDE0] blur-3xl" />
          <div className="pointer-events-none absolute -left-24 top-64 h-[320px] w-[320px] rounded-full bg-[#F0E7D5] blur-3xl" />
          <div className="relative mx-auto grid max-w-6xl gap-12 px-5 pb-16 pt-16 md:grid-cols-[1.05fr_0.95fr] md:items-center md:pb-24 md:pt-24">
            <div className="rise">
              <span className="inline-flex items-center gap-2 rounded-full border border-[#DCE1D2] bg-[#F1F3E9] px-3 py-1 text-[10px] uppercase tracking-[0.16em] text-[#5D6C55]">
                <span className="h-1.5 w-1.5 rounded-full bg-sage" />
                Physiological pattern research
              </span>
              <h1 className="mt-6 font-display text-[42px] leading-[1.06] tracking-[-0.02em] text-forest md:text-[62px]">
                Your body has a story.
                <br />
                <em className="font-light not-italic text-[#7C8B68]">
                  <span className="italic">Learn to understand its signals.</span>
                </em>
              </h1>
              <p className="mt-6 max-w-lg text-[15px] leading-relaxed text-[#5F675F]">
                AuraSense brings heart rhythm, skin conductance, breathing and movement into one calm, legible
                workspace — with a trained research model, visible uncertainty, and no claims it cannot support.
              </p>
              <div className="mt-8 flex flex-wrap items-center gap-3">
                <Link to="/register" className="btn btn-primary px-5 py-3 text-[13px]">
                  Begin with your signals <ArrowRight size={15} />
                </Link>
                <Link to="/login" className="btn btn-secondary px-5 py-3 text-[13px]">
                  Explore the demonstration
                </Link>
              </div>
              <p className="mt-4 text-[11px] text-muted">
                Demo access: <span className="mono text-[#5F6B58]">demo@aurasense.app</span> ·{' '}
                <span className="mono text-[#5F6B58]">Demo1234!</span>
              </p>

              <div className="mt-10 grid max-w-md grid-cols-3 gap-5 border-t border-line pt-6">
                {[
                  { value: '15', label: 'WESAD participants' },
                  { value: '1,032', label: 'analysed windows' },
                  { value: '20', label: 'physiological features' },
                ].map((stat) => (
                  <div key={stat.label}>
                    <p className="font-display text-2xl text-forest">{stat.value}</p>
                    <p className="mt-0.5 text-[10px] uppercase tracking-[0.1em] text-muted">{stat.label}</p>
                  </div>
                ))}
              </div>
            </div>

            <div className="rise" style={{ animationDelay: '120ms' }}>
              <div className="relative rounded-[26px] border border-[#DFDDCF] bg-paper p-5 shadow-[0_30px_80px_-50px_rgba(24,61,50,0.5)]">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-[10px] uppercase tracking-[0.18em] text-muted">Signal window</p>
                    <p className="mt-1 font-display text-lg text-forest">Chest · 60 seconds</p>
                  </div>
                  <span className="rounded-full border border-[#E7D9C0] bg-[#FAF2E4] px-2.5 py-1 text-[9px] uppercase tracking-[0.12em] text-[#8A6526]">
                    Illustration
                  </span>
                </div>

                <div className="mt-5 rounded-2xl bg-[#F4F5EC] px-2 py-4">
                  <svg viewBox="0 0 620 140" className="h-[130px] w-full" preserveAspectRatio="none" aria-hidden>
                    <line x1="0" y1="110" x2="620" y2="110" stroke="#E2E4D6" strokeWidth="1" />
                    <polyline
                      points={svgPoints}
                      fill="none"
                      stroke="#183D32"
                      strokeWidth="1.5"
                      strokeLinejoin="round"
                      className="sweep-line"
                      vectorEffect="non-scaling-stroke"
                    />
                  </svg>
                  <div className="mt-1 flex justify-between px-2 text-[9px] uppercase tracking-[0.14em] text-muted">
                    <span>ECG</span>
                    <span>0:00 — 1:00</span>
                  </div>
                </div>

                <div className="mt-4 grid grid-cols-3 gap-2.5">
                  {[
                    { label: 'Heart rate', value: '68', unit: 'bpm' },
                    { label: 'Skin conduct.', value: '2.4', unit: 'µS' },
                    { label: 'Breathing', value: '14', unit: '/min' },
                  ].map((item) => (
                    <div key={item.label} className="rounded-xl border border-line bg-[#FBFAF4] px-3 py-2.5">
                      <p className="text-[9px] uppercase tracking-[0.1em] text-muted">{item.label}</p>
                      <p className="mt-1 flex items-baseline gap-1">
                        <span className="font-display text-xl text-forest">{item.value}</span>
                        <span className="text-[9px] text-muted">{item.unit}</span>
                      </p>
                    </div>
                  ))}
                </div>

                <div className="mt-4 flex items-start gap-2 rounded-xl bg-[#F5F1E6] px-3 py-2.5 text-[10px] leading-relaxed text-[#7C6A44]">
                  <ShieldCheck size={13} className="mt-0.5 shrink-0" />
                  This illustration is generated, not measured. Every simulated reading is labelled as such inside the app.
                </div>
              </div>
            </div>
          </div>
        </section>

        <section className="border-y border-line bg-[#F2F1E8]">
          <div className="mx-auto flex max-w-6xl flex-col items-start justify-between gap-4 px-5 py-6 md:flex-row md:items-center">
            <p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-muted">Built on</p>
            <div className="flex flex-wrap items-center gap-x-8 gap-y-3 text-[12px] text-[#5C665C]">
              <span className="inline-flex items-center gap-2">
                <Microscope size={14} className="text-sage" /> WESAD wearable stress dataset
              </span>
              <span className="inline-flex items-center gap-2">
                <Activity size={14} className="text-sage" /> {model?.model_name || 'Gradient boosting'} · participant-independent CV
              </span>
              <span className="inline-flex items-center gap-2">
                <Waves size={14} className="text-sage" /> ECG · EDA · respiration · temperature · movement
              </span>
            </div>
          </div>
        </section>

        <section id="how" className="mx-auto max-w-6xl px-5 py-20">
          <div className="max-w-2xl">
            <p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-muted">How it works</p>
            <h2 className="mt-3 font-display text-[34px] leading-tight text-forest md:text-[42px]">
              A calmer way to read the signals.
            </h2>
            <p className="mt-3 text-sm leading-relaxed text-muted">
              Every step is inspectable: the channels used, the windows analysed, the quality of the signal, the
              probabilities behind the estimate and the features that moved it.
            </p>
          </div>

          <div className="mt-10 grid gap-4 md:grid-cols-3">
            {[
              {
                title: 'Observe',
                body: 'Run a clearly labelled simulated session to see how chest ECG, EDA, respiration and movement flow through the pipeline in real time.',
                icon: Activity,
              },
              {
                title: 'Understand',
                body: 'Twenty standardised features are compared with WESAD-derived patterns. You see probability, uncertainty, signal quality and local feature contributions.',
                icon: Microscope,
              },
              {
                title: 'Investigate',
                body: 'Upload your own CSV, compare against your personal baseline, and export a report that states its sources, model version and limitations.',
                icon: CheckCircle2,
              },
            ].map((item, index) => {
              const Icon = item.icon
              return (
                <div key={item.title} className="card p-6">
                  <div className="flex items-center justify-between">
                    <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-[#EDF1E5] text-[#4C6449]">
                      <Icon size={18} />
                    </span>
                    <span className="font-display text-3xl text-[#DDDAC9]">0{index + 1}</span>
                  </div>
                  <h3 className="mt-5 font-display text-xl text-forest">{item.title}</h3>
                  <p className="mt-2 text-[12.5px] leading-relaxed text-muted">{item.body}</p>
                </div>
              )
            })}
          </div>
        </section>

        <section id="science" className="bg-forest text-[#EDEFE5]">
          <div className="mx-auto grid max-w-6xl gap-12 px-5 py-20 md:grid-cols-[0.95fr_1.05fr]">
            <div>
              <p className="text-[10px] font-semibold uppercase tracking-[0.2em] text-[#9FB3A2]">The science, stated plainly</p>
              <h2 className="mt-4 font-display text-[34px] leading-tight md:text-[42px]">
                Evidence you can inspect.
                <br />
                Limits we do not hide.
              </h2>
              <p className="mt-5 max-w-md text-[13px] leading-relaxed text-[#C5D2C6]">
                AuraSense is trained on the public WESAD dataset: 15 participants, chest and wrist sensors, and a
                laboratory protocol with neutral, stress (TSST) and amusement conditions. Evaluation holds entire
                participants out of training in every fold.
              </p>
              <div className="mt-7 flex flex-wrap gap-3">
                <a href={model ? '#science' : '#science'} className="btn border border-[#486A57] bg-transparent px-4 py-2.5 text-[#EDEFE5] hover:bg-[#20483B]">
                  Read the model card <ChevronRight size={14} />
                </a>
                <Link to="/login" className="btn bg-[#EDEFE5] px-4 py-2.5 text-[13px] text-forest hover:bg-white">
                  Open the workspace
                </Link>
              </div>
            </div>

            <div className="space-y-3">
              <div className="rounded-2xl border border-[#315544] bg-[#143328] p-5">
                <div className="flex items-start justify-between gap-4">
                  <div>
                    <p className="text-[10px] uppercase tracking-[0.16em] text-[#8FA396]">Participant-independent result</p>
                    <p className="mt-2 font-display text-4xl text-[#F1F2E8]">
                      {metric ? `${(metric * 100).toFixed(1)}%` : '—'}
                      <span className="ml-2 font-sans text-[11px] font-normal text-[#9FB3A2]">balanced accuracy</span>
                    </p>
                  </div>
                  <span className="rounded-full border border-[#3E604E] px-2.5 py-1 text-[9px] uppercase tracking-[0.12em] text-[#A9BBA9]">
                    3-class
                  </span>
                </div>
                <p className="mt-3 text-[11px] leading-relaxed text-[#A9BBA9]">
                  Grouped cross-validation by participant. Not a measure of clinical accuracy, and not a result on any
                  individual user.
                </p>
              </div>

              {[
                {
                  title: 'Physiology is not a diagnosis',
                  body: 'A pattern similar to a stress condition is not proof of stress, anxiety or illness. AuraSense never outputs a diagnosis.',
                },
                {
                  title: 'Signal quality changes the answer',
                  body: 'Motion, loose sensors and short recordings reduce confidence. Quality is scored and shown before you rely on an estimate.',
                },
                {
                  title: 'Your data stays yours',
                  body: 'Institution views are opt-in only and suppressed below a minimum cohort. You can export or delete your account data at any time.',
                },
              ].map((item) => (
                <div key={item.title} className="rounded-2xl border border-[#315544] bg-[#143328]/60 p-4">
                  <div className="flex items-start gap-3">
                    <Lock size={14} className="mt-0.5 shrink-0 text-[#91A58E]" />
                    <div>
                      <p className="text-[12.5px] font-medium text-[#EDEFE5]">{item.title}</p>
                      <p className="mt-1 text-[11px] leading-relaxed text-[#A9BBA9]">{item.body}</p>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </section>

        <section id="privacy" className="mx-auto max-w-6xl px-5 py-20">
          <div className="grid gap-10 md:grid-cols-[0.9fr_1.1fr] md:items-center">
            <div>
              <p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-muted">Privacy by design</p>
              <h2 className="mt-3 font-display text-[34px] leading-tight text-forest md:text-[40px]">
                Built for research,
                <br />
                not surveillance.
              </h2>
              <p className="mt-4 max-w-md text-[13px] leading-relaxed text-muted">
                Aggregate institution views use only explicitly shared analyses, require a minimum cohort, and never
                expose individual records. Raw signals can be discarded after analysis.
              </p>
            </div>
            <div className="grid gap-3 sm:grid-cols-2">
              {[
                { title: 'Explicit consent', body: 'Sharing is off by default and can be withdrawn in Settings.' },
                { title: 'Cohort suppression', body: 'Groups below the minimum size are withheld, not partially shown.' },
                { title: 'Data export', body: 'Download your account, analyses and baselines as JSON.' },
                { title: 'Deletion', body: 'Remove your account and associated records from the app.' },
              ].map((item) => (
                <div key={item.title} className="card p-4">
                  <p className="text-[12.5px] font-medium text-forest">{item.title}</p>
                  <p className="mt-1 text-[11px] leading-relaxed text-muted">{item.body}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        <section className="mx-auto max-w-6xl px-5 pb-20">
          <div className="rounded-[28px] bg-[#EAEDDF] px-6 py-12 text-center md:px-16">
            <p className="text-[10px] font-semibold uppercase tracking-[0.2em] text-[#6E7C63]">Begin gently</p>
            <h2 className="mx-auto mt-3 max-w-xl font-display text-[32px] leading-tight text-forest md:text-[40px]">
              Understand the pattern before you name it.
            </h2>
            <p className="mx-auto mt-3 max-w-lg text-[13px] leading-relaxed text-[#63705D]">
              Explore with the demonstration account, or create a private workspace for your own recordings and baselines.
            </p>
            <div className="mt-7 flex flex-wrap justify-center gap-3">
              <Link to="/register" className="btn btn-primary px-5 py-3 text-[13px]">
                Create your workspace <ArrowRight size={15} />
              </Link>
              <Link to="/login" className="btn btn-secondary bg-white/60 px-5 py-3 text-[13px]">
                Use the demo account
              </Link>
            </div>
          </div>
        </section>
      </main>

      <footer className="border-t border-line">
        <div className="mx-auto flex max-w-6xl flex-col gap-4 px-5 py-8 text-[11px] text-muted md:flex-row md:items-center md:justify-between">
          <Brand dark={false} />
          <p className="max-w-md leading-relaxed">
            AuraSense is a research prototype. It does not diagnose or treat any condition and is not a substitute for
            professional care.
          </p>
          <p className="mono text-[10px]">v1.0.0</p>
        </div>
      </footer>
    </div>
  )
}
