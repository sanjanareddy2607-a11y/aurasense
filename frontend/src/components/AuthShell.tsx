import type { ReactNode } from 'react'
import { Link } from 'react-router-dom'
import { ShieldCheck } from 'lucide-react'

export default function AuthShell({
  title,
  subtitle,
  children,
  footer,
}: {
  title: string
  subtitle: string
  children: ReactNode
  footer: ReactNode
}) {
  return (
    <div className="grid min-h-screen bg-ivory lg:grid-cols-[0.92fr_1.08fr]">
      <aside className="relative hidden overflow-hidden bg-forest-deep p-10 text-[#EDEFE5] lg:flex lg:flex-col lg:justify-between">
        <div className="pointer-events-none absolute -right-24 top-10 h-[380px] w-[380px] rounded-full bg-[#24503F]/40 blur-3xl" />
        <Link to="/" className="relative flex items-center gap-2.5">
          <span className="flex h-9 w-9 items-center justify-center rounded-[11px] bg-[#DFE8D7]">
            <svg viewBox="0 0 32 32" className="h-6 w-6" fill="none" aria-hidden>
              <path
                d="M4 18c2.2 0 2.2-7 4.4-7s2.2 12 4.4 12 2.2-9 4.4-9 2.2 5 4.4 5 2.2-2 4.4-2"
                stroke="#183D32"
                strokeWidth="1.7"
                strokeLinecap="round"
              />
              <circle cx="25" cy="10" r="2" fill="#D49A45" />
            </svg>
          </span>
          <span className="font-display text-xl">AuraSense</span>
        </Link>

        <div className="relative">
          <svg viewBox="0 0 480 160" className="mb-10 w-full opacity-80" aria-hidden>
            <line x1="0" y1="110" x2="480" y2="110" stroke="#315544" strokeWidth="1" />
            <polyline
              points={Array.from({ length: 240 }, (_, i) => {
                const t = i / 240
                const beat = Math.exp(-Math.pow(((t * 7) % 1 - 0.3) * 12, 2))
                const wave = 0.2 * Math.exp(-Math.pow(((t * 7) % 1 - 0.62) * 18, 2))
                return `${t * 480},${100 - (beat - wave + 0.05 * Math.sin(t * 18)) * 210}`
              }).join(' ')}
              fill="none"
              stroke="#C7D6C6"
              strokeWidth="1.4"
              vectorEffect="non-scaling-stroke"
            />
          </svg>
          <p className="max-w-sm font-display text-[30px] leading-tight">
            Beyond the pulse.
            <br />
            <span className="italic text-[#A9BBA9]">Understand the pattern.</span>
          </p>
          <p className="mt-4 max-w-sm text-[12px] leading-relaxed text-[#A9BBA9]">
            A research workspace for physiological signals — with the quality, uncertainty and limitations shown
            alongside every estimate.
          </p>
        </div>

        <div className="relative flex items-start gap-2.5 rounded-xl border border-[#315544] bg-[#143328]/60 p-4 text-[11px] leading-relaxed text-[#A9BBA9]">
          <ShieldCheck size={15} className="mt-0.5 shrink-0 text-[#91A58E]" />
          AuraSense does not diagnose any condition. It estimates similarity to patterns in a research dataset.
        </div>
      </aside>

      <main className="flex items-center justify-center px-5 py-12">
        <div className="w-full max-w-[400px]">
          <Link to="/" className="mb-8 flex items-center gap-2 lg:hidden">
            <span className="flex h-8 w-8 items-center justify-center rounded-[10px] bg-forest">
              <svg viewBox="0 0 32 32" className="h-5 w-5" fill="none" aria-hidden>
                <path
                  d="M4 18c2.2 0 2.2-7 4.4-7s2.2 12 4.4 12 2.2-9 4.4-9 2.2 5 4.4 5 2.2-2 4.4-2"
                  stroke="#DCE5D6"
                  strokeWidth="1.8"
                  strokeLinecap="round"
                />
              </svg>
            </span>
            <span className="font-display text-lg text-forest">AuraSense</span>
          </Link>
          <p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-muted">Your workspace</p>
          <h1 className="mt-2 font-display text-[30px] leading-tight text-forest">{title}</h1>
          <p className="mt-2 text-[12.5px] leading-relaxed text-muted">{subtitle}</p>
          <div className="mt-7">{children}</div>
          <div className="mt-6 text-[12px] text-muted">{footer}</div>
        </div>
      </main>
    </div>
  )
}
