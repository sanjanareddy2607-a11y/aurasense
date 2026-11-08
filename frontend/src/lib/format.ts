export function pct(value: number | null | undefined, digits = 0): string {
  if (value === null || value === undefined || Number.isNaN(value)) return '—'
  return `${(value * 100).toFixed(digits)}%`
}

export function num(value: number | null | undefined, digits = 1): string {
  if (value === null || value === undefined || Number.isNaN(value)) return '—'
  return value.toFixed(digits)
}

export function compact(value: number | null | undefined): string {
  if (value === null || value === undefined) return '—'
  return new Intl.NumberFormat('en', { notation: 'compact', maximumFractionDigits: 1 }).format(value)
}

export function dateShort(value: string | null | undefined): string {
  if (!value) return '—'
  return new Date(value).toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' })
}

export function dateTime(value: string | null | undefined): string {
  if (!value) return '—'
  return new Date(value).toLocaleString('en-GB', {
    day: '2-digit',
    month: 'short',
    hour: '2-digit',
    minute: '2-digit',
  })
}

export function relative(value: string | null | undefined): string {
  if (!value) return '—'
  const diff = Date.now() - new Date(value).getTime()
  const minutes = Math.round(diff / 60000)
  if (minutes < 1) return 'just now'
  if (minutes < 60) return `${minutes} min ago`
  const hours = Math.round(minutes / 60)
  if (hours < 24) return `${hours} h ago`
  const days = Math.round(hours / 24)
  if (days < 30) return `${days} d ago`
  return dateShort(value)
}

export function duration(seconds: number | null | undefined): string {
  if (seconds === null || seconds === undefined) return '—'
  const mins = Math.floor(seconds / 60)
  const secs = Math.round(seconds % 60)
  if (mins === 0) return `${secs}s`
  return `${mins}m ${secs.toString().padStart(2, '0')}s`
}

export function classTone(predicted: string | null | undefined): 'stress' | 'neutral' | 'amusement' | 'unknown' {
  if (predicted === 'stress') return 'stress'
  if (predicted === 'neutral') return 'neutral'
  if (predicted === 'amusement') return 'amusement'
  return 'unknown'
}

export function gradeTone(grade: string | null | undefined): 'good' | 'fair' | 'poor' | 'unknown' {
  if (grade === 'good') return 'good'
  if (grade === 'fair') return 'fair'
  if (grade === 'poor' || grade === 'insufficient') return 'poor'
  return 'unknown'
}

// The API always returns stress probabilities on a 0–100 scale.
export function stressPercent(value: number | null | undefined): number | null {
  if (value === null || value === undefined || Number.isNaN(value)) return null
  return value
}

export function titleCase(value: string): string {
  return value.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())
}

export function featureLabel(name: string): string {
  return titleCase(name)
}

export const NAV_LABELS: Record<string, string> = {
  hr_mean: 'Mean heart rate',
  hr_std: 'HR variability (SD)',
  rmssd: 'RMSSD',
  sdnn: 'SDNN',
  pnn50: 'pNN50',
  eda_mean: 'Mean skin conductance',
  eda_std: 'EDA variability',
  eda_slope: 'EDA trend',
  eda_phasic_std: 'Phasic EDA variability',
  scr_count: 'SCR frequency',
  scr_amp_sum: 'SCR amplitude',
  resp_rate: 'Respiration rate',
  resp_rate_std: 'Breathing variability',
  resp_amp: 'Respiration amplitude',
  temp_mean: 'Skin temperature',
  temp_std: 'Temperature variability',
  temp_slope: 'Temperature trend',
  emg_rms: 'Muscle activity',
  acc_mag_mean: 'Movement magnitude',
  acc_mag_std: 'Movement variability',
}

export function featureName(name: string): string {
  return NAV_LABELS[name] || titleCase(name)
}
