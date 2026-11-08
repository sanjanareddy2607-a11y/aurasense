import type { ReactNode } from 'react'
import { AlertTriangle, CheckCircle2, Info, Loader2, X } from 'lucide-react'

export function cn(...values: (string | false | null | undefined)[]): string {
  return values.filter(Boolean).join(' ')
}

type Tone = 'neutral' | 'stress' | 'amusement' | 'good' | 'fair' | 'poor' | 'sage' | 'amber' | 'coral'

const tones: Record<Tone, string> = {
  neutral: 'bg-[#F0EFE7] text-[#5E665F] border-[#E2DFD2]',
  stress: 'bg-[#F6E7E2] text-[#A45545] border-[#EBCFC6]',
  amusement: 'bg-[#EEF1E4] text-[#6C7546] border-[#DDE3C8]',
  good: 'bg-[#E9EFE5] text-[#3F5F45] border-[#CFDCC8]',
  fair: 'bg-[#F7EEDF] text-[#8A6526] border-[#EAD9BC]',
  poor: 'bg-[#F7E6E1] text-[#A45545] border-[#EBCFC6]',
  sage: 'bg-[#EDF2EA] text-[#47664F] border-[#D5E0CF]',
  amber: 'bg-[#F8EFDF] text-[#8A6526] border-[#EBD9BB]',
  coral: 'bg-[#F8E8E3] text-[#A45545] border-[#EDD2C9]',
}

export function Badge({ children, tone = 'neutral', className }: { children: ReactNode; tone?: Tone; className?: string }) {
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1 rounded-full border px-2.5 py-0.5 text-[11px] font-medium tracking-wide',
        tones[tone],
        className,
      )}
    >
      {children}
    </span>
  )
}

export function Card({ children, className }: { children: ReactNode; className?: string }) {
  return <div className={cn('card', className)}>{children}</div>
}

export function SectionLabel({ children, className }: { children: ReactNode; className?: string }) {
  return <p className={cn('text-[10px] font-semibold uppercase tracking-[0.16em] text-muted', className)}>{children}</p>
}

export function PageHeader({
  eyebrow,
  title,
  description,
  actions,
}: {
  eyebrow?: string
  title: string
  description?: string
  actions?: ReactNode
}) {
  return (
    <header className="mb-7 flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
      <div className="max-w-2xl">
        {eyebrow && <SectionLabel className="mb-2">{eyebrow}</SectionLabel>}
        <h1 className="text-[26px] leading-tight text-forest md:text-[32px]">{title}</h1>
        {description && <p className="mt-2 text-sm leading-relaxed text-muted">{description}</p>}
      </div>
      {actions && <div className="flex flex-wrap items-center gap-2">{actions}</div>}
    </header>
  )
}

export function Stat({
  label,
  value,
  unit,
  meta,
  icon,
  tone = 'neutral',
}: {
  label: string
  value: ReactNode
  unit?: string
  meta?: ReactNode
  icon?: ReactNode
  tone?: 'neutral' | 'sage' | 'amber' | 'coral'
}) {
  const ring = {
    neutral: 'bg-[#F1F1E9] text-forest',
    sage: 'bg-[#EAF0E6] text-[#47664F]',
    amber: 'bg-[#F7EEDF] text-[#8A6526]',
    coral: 'bg-[#F7E8E3] text-[#A45545]',
  }[tone]
  return (
    <Card className="p-5">
      <div className="flex items-start justify-between gap-3">
        <p className="text-[11px] font-medium uppercase tracking-[0.12em] text-muted">{label}</p>
        {icon && <span className={cn('flex h-8 w-8 items-center justify-center rounded-full', ring)}>{icon}</span>}
      </div>
      <div className="mt-3 flex items-baseline gap-1.5">
        <span className="font-display text-[30px] leading-none text-forest tabular">{value}</span>
        {unit && <span className="text-xs text-muted">{unit}</span>}
      </div>
      {meta && <div className="mt-3 text-[12px] leading-snug text-muted">{meta}</div>}
    </Card>
  )
}

export function Spinner({ label = 'Loading', size = 16 }: { label?: string; size?: number }) {
  return (
    <span className="inline-flex items-center gap-2 text-xs text-muted">
      <Loader2 size={size} className="animate-spin" />
      {label}
    </span>
  )
}

export function LoadingBlock({ label = 'Loading' }: { label?: string }) {
  return (
    <div className="flex min-h-[180px] items-center justify-center">
      <Spinner label={label} size={20} />
    </div>
  )
}

export function EmptyState({
  icon,
  title,
  description,
  action,
}: {
  icon?: ReactNode
  title: string
  description?: string
  action?: ReactNode
}) {
  return (
    <div className="flex flex-col items-center justify-center gap-3 rounded-2xl border border-dashed border-line px-6 py-12 text-center">
      {icon && <div className="flex h-11 w-11 items-center justify-center rounded-full bg-[#F1F1E9] text-sage">{icon}</div>}
      <div>
        <p className="font-display text-lg text-forest">{title}</p>
        {description && <p className="mx-auto mt-1 max-w-md text-xs leading-relaxed text-muted">{description}</p>}
      </div>
      {action}
    </div>
  )
}

export function Notice({
  tone = 'info',
  title,
  children,
  className,
}: {
  tone?: 'info' | 'warning' | 'success' | 'danger'
  title?: string
  children: ReactNode
  className?: string
}) {
  const config = {
    info: { icon: Info, box: 'border-[#DDE4DB] bg-[#F4F6F0] text-[#4A5A4E]' },
    warning: { icon: AlertTriangle, box: 'border-[#EBD9BB] bg-[#FAF3E6] text-[#7E5E24]' },
    success: { icon: CheckCircle2, box: 'border-[#CFDCC8] bg-[#EFF4EB] text-[#3F5F45]' },
    danger: { icon: AlertTriangle, box: 'border-[#EDD2C9] bg-[#FAEDE9] text-[#A45545]' },
  }[tone]
  const Icon = config.icon
  return (
    <div className={cn('flex gap-2.5 rounded-xl border px-3.5 py-3 text-xs leading-relaxed', config.box, className)}>
      <Icon size={15} className="mt-0.5 shrink-0" />
      <div>
        {title && <p className="mb-0.5 font-semibold">{title}</p>}
        <div>{children}</div>
      </div>
    </div>
  )
}

export function ProgressBar({
  value,
  max = 100,
  tone = 'forest',
  className,
}: {
  value: number
  max?: number
  tone?: 'forest' | 'sage' | 'amber' | 'coral'
  className?: string
}) {
  const colors = { forest: 'bg-forest', sage: 'bg-sage', amber: 'bg-amber', coral: 'bg-coral' }
  const width = Math.max(0, Math.min(100, (value / max) * 100))
  return (
    <div className={cn('h-1.5 w-full overflow-hidden rounded-full bg-[#ECEAE0]', className)}>
      <div className={cn('h-full rounded-full transition-all duration-500', colors[tone])} style={{ width: `${width}%` }} />
    </div>
  )
}

export function Modal({
  open,
  onClose,
  title,
  description,
  children,
  footer,
}: {
  open: boolean
  onClose: () => void
  title: string
  description?: string
  children?: ReactNode
  footer?: ReactNode
}) {
  if (!open) return null
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-[#102A23]/40 backdrop-blur-sm" onClick={onClose} />
      <div className="relative w-full max-w-md rounded-2xl border border-line bg-paper p-6 shadow-xl">
        <button
          onClick={onClose}
          className="absolute right-4 top-4 rounded-full p-1 text-muted transition hover:bg-[#F1F1E9] hover:text-forest"
          aria-label="Close"
        >
          <X size={16} />
        </button>
        <h3 className="pr-6 font-display text-xl text-forest">{title}</h3>
        {description && <p className="mt-1.5 text-xs leading-relaxed text-muted">{description}</p>}
        <div className="mt-4">{children}</div>
        {footer && <div className="mt-5 flex justify-end gap-2">{footer}</div>}
      </div>
    </div>
  )
}

export function Field({
  label,
  hint,
  error,
  children,
  htmlFor,
}: {
  label: string
  hint?: string
  error?: string
  children: ReactNode
  htmlFor?: string
}) {
  return (
    <div>
      <label className="label" htmlFor={htmlFor}>
        {label}
      </label>
      {children}
      {hint && !error && <p className="mt-1.5 text-[11px] leading-relaxed text-muted">{hint}</p>}
      {error && <p className="mt-1.5 text-[11px] text-coral">{error}</p>}
    </div>
  )
}

export function Toggle({
  checked,
  onChange,
  label,
  description,
  disabled,
}: {
  checked: boolean
  onChange: (value: boolean) => void
  label: string
  description?: string
  disabled?: boolean
}) {
  return (
    <div className="flex items-start justify-between gap-6 py-4">
      <div>
        <p className="text-sm font-medium text-charcoal">{label}</p>
        {description && <p className="mt-1 max-w-lg text-xs leading-relaxed text-muted">{description}</p>}
      </div>
      <button
        type="button"
        role="switch"
        aria-checked={checked}
        disabled={disabled}
        onClick={() => onChange(!checked)}
        className={cn(
          'relative mt-0.5 h-6 w-11 shrink-0 rounded-full border transition-colors',
          checked ? 'border-forest bg-forest' : 'border-line bg-[#E9E7DC]',
          disabled && 'opacity-50',
        )}
      >
        <span
          className={cn('absolute top-0.5 rounded-full bg-white transition-transform', checked ? 'translate-x-5' : 'translate-x-0.5')}
          style={{ height: 18, width: 18 }}
        />
      </button>
    </div>
  )
}

export function Tabs({
  tabs,
  value,
  onChange,
}: {
  tabs: { key: string; label: string }[]
  value: string
  onChange: (key: string) => void
}) {
  return (
    <div className="inline-flex flex-wrap gap-1 rounded-full border border-line bg-[#F4F3EB] p-1">
      {tabs.map((tab) => (
        <button
          key={tab.key}
          onClick={() => onChange(tab.key)}
          className={cn(
            'rounded-full px-3.5 py-1.5 text-xs font-medium transition',
            value === tab.key ? 'bg-paper text-forest shadow-sm' : 'text-muted hover:text-forest',
          )}
        >
          {tab.label}
        </button>
      ))}
    </div>
  )
}

export function SourceBadge({ sourceType, isDemo }: { sourceType: string; isDemo?: boolean }) {
  if (isDemo) return <Badge tone="amber">Seeded demo record</Badge>
  if (sourceType === 'simulated') return <Badge tone="sage">Simulated signals</Badge>
  if (sourceType === 'wesad_reference') return <Badge tone="neutral">WESAD reference</Badge>
  if (sourceType === 'upload') return <Badge tone="neutral">Uploaded CSV</Badge>
  if (sourceType === 'demo_file') return <Badge tone="amber">Demo dataset</Badge>
  return <Badge>{sourceType}</Badge>
}

export function QualityPill({ score, grade }: { score: number | null; grade: string | null }) {
  if (score === null || score === undefined) return <Badge>Quality not assessed</Badge>
  const tone: Tone = grade === 'good' ? 'good' : grade === 'fair' ? 'fair' : grade === 'poor' ? 'poor' : 'coral'
  return (
    <Badge tone={tone}>
      <span className="h-1.5 w-1.5 rounded-full bg-current" />
      Quality {Math.round(score)}/100 · {grade ?? 'unknown'}
    </Badge>
  )
}

export function ClassPill({ predicted, label }: { predicted: string | null; label: string }) {
  const tone: Tone = predicted === 'stress' ? 'stress' : predicted === 'neutral' ? 'good' : predicted === 'amusement' ? 'amusement' : 'amber'
  return <Badge tone={tone}>{label}</Badge>
}
