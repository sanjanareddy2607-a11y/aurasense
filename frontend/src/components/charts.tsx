import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import type { ReactNode } from 'react'
import { cn } from './ui'

export const CHART_COLORS = {
  forest: '#183D32',
  sage: '#91A58E',
  olive: '#A4A477',
  amber: '#D49A45',
  coral: '#C97969',
  grey: '#C9C7B9',
}

const axisStyle = { fontSize: 10, fill: '#858B83' }

function TooltipCard({ active, payload, label }: { active?: boolean; payload?: any[]; label?: ReactNode }) {
  if (!active || !payload?.length) return null
  return (
    <div className="rounded-lg border border-line bg-paper/95 px-2.5 py-2 text-[11px] shadow-md backdrop-blur">
      {label !== undefined && <p className="mb-1 font-medium text-forest">{String(label)}</p>}
      {payload.map((entry) => (
        <div key={entry.dataKey} className="flex items-center gap-1.5 text-muted">
          <span className="h-1.5 w-1.5 rounded-full" style={{ background: entry.color }} />
          <span>{entry.name}:</span>
          <span className="tabular text-charcoal">
            {typeof entry.value === 'number' ? entry.value.toFixed(entry.value < 10 ? 2 : 1) : '—'}
          </span>
        </div>
      ))}
    </div>
  )
}

export interface SeriesDef {
  key: string
  label: string
  color: string
  axis?: 'left' | 'right'
}

export function TrendChart({
  data,
  series,
  xKey = 'label',
  height = 220,
  yDomain,
  rightAxis = false,
}: {
  data: Record<string, any>[]
  series: SeriesDef[]
  xKey?: string
  height?: number
  yDomain?: [number | 'auto', number | 'auto']
  rightAxis?: boolean
}) {
  return (
    <div style={{ height }} className="w-full">
      <ResponsiveContainer>
        <LineChart data={data} margin={{ top: 8, right: rightAxis ? 4 : 12, left: -18, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 4" stroke="#EAE8DD" vertical={false} />
          <XAxis dataKey={xKey} tick={axisStyle} tickLine={false} axisLine={{ stroke: '#E4E1D5' }} minTickGap={18} />
          <YAxis yAxisId="left" tick={axisStyle} tickLine={false} axisLine={false} domain={yDomain} width={46} />
          {rightAxis && (
            <YAxis yAxisId="right" orientation="right" tick={axisStyle} tickLine={false} axisLine={false} domain={[0, 100]} width={38} />
          )}
          <Tooltip content={<TooltipCard />} cursor={{ stroke: '#D8D5C8', strokeDasharray: '3 3' }} />
          {series.map((item) => (
            <Line
              key={item.key}
              yAxisId={rightAxis && item.axis === 'right' ? 'right' : 'left'}
              type="monotone"
              dataKey={item.key}
              name={item.label}
              stroke={item.color}
              strokeWidth={1.8}
              dot={false}
              activeDot={{ r: 3, strokeWidth: 0 }}
              connectNulls
            />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}

export function AreaTrend({
  data,
  dataKey,
  color = CHART_COLORS.forest,
  height = 160,
}: {
  data: Record<string, any>[]
  dataKey: string
  color?: string
  height?: number
}) {
  const gradientId = `grad-${dataKey}-${color.replace('#', '')}`
  return (
    <div style={{ height }} className="w-full">
      <ResponsiveContainer>
        <AreaChart data={data} margin={{ top: 6, right: 4, left: -24, bottom: 0 }}>
          <defs>
            <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={color} stopOpacity={0.22} />
              <stop offset="100%" stopColor={color} stopOpacity={0.01} />
            </linearGradient>
          </defs>
          <XAxis dataKey="label" tick={axisStyle} tickLine={false} axisLine={false} minTickGap={24} />
          <YAxis tick={axisStyle} tickLine={false} axisLine={false} width={42} />
          <Tooltip content={<TooltipCard />} />
          <Area type="monotone" dataKey={dataKey} stroke={color} strokeWidth={1.7} fill={`url(#${gradientId})`} connectNulls />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  )
}

export function Waveform({
  values,
  color = CHART_COLORS.forest,
  height = 120,
  className,
  label,
}: {
  values: (number | null)[]
  color?: string
  height?: number
  className?: string
  label?: string
}) {
  const width = 700
  const cleaned = values.filter((v): v is number => v !== null && Number.isFinite(v))
  if (!cleaned.length) {
    return (
      <div
        className={cn('flex items-center justify-center rounded-lg border border-dashed border-line text-[11px] text-muted', className)}
        style={{ height }}
      >
        Awaiting signal
      </div>
    )
  }
  const min = Math.min(...cleaned)
  const max = Math.max(...cleaned)
  const span = max - min || 1
  const step = width / Math.max(1, values.length - 1)
  const points: string[] = []
  values.forEach((value, index) => {
    if (value === null || !Number.isFinite(value)) return
    const x = index * step
    const y = height - 10 - ((value - min) / span) * (height - 20)
    points.push(`${x.toFixed(1)},${y.toFixed(1)}`)
  })
  return (
    <div className={cn('relative', className)}>
      {label && <span className="absolute left-1 top-0 text-[9px] uppercase tracking-[0.15em] text-muted">{label}</span>}
      <svg
        viewBox={`0 0 ${width} ${height}`}
        preserveAspectRatio="none"
        className="w-full"
        style={{ height }}
        role="img"
        aria-label={label || 'Signal waveform'}
      >
        <line x1="0" y1={height / 2} x2={width} y2={height / 2} stroke="#EDEBE0" strokeWidth="1" />
        <polyline
          points={points.join(' ')}
          fill="none"
          stroke={color}
          strokeWidth="1.4"
          strokeLinejoin="round"
          strokeLinecap="round"
          vectorEffect="non-scaling-stroke"
        />
      </svg>
    </div>
  )
}

export function ProbabilityBars({ probabilities, compact = false }: { probabilities: Record<string, number>; compact?: boolean }) {
  const entries = Object.entries(probabilities).sort((a, b) => b[1] - a[1])
  const colors: Record<string, string> = {
    neutral: CHART_COLORS.sage,
    stress: CHART_COLORS.coral,
    amusement: CHART_COLORS.olive,
  }
  return (
    <div className={cn('space-y-2.5', compact && 'space-y-2')}>
      {entries.map(([name, value]) => (
        <div key={name}>
          <div className="mb-1 flex items-center justify-between text-[11px]">
            <span className="capitalize text-charcoal">{name}</span>
            <span className="tabular text-muted">{(value * 100).toFixed(1)}%</span>
          </div>
          <div className="h-1.5 overflow-hidden rounded-full bg-[#EDEBE1]">
            <div
              className="h-full rounded-full transition-all duration-700"
              style={{ width: `${Math.max(1, value * 100)}%`, background: colors[name] || CHART_COLORS.sage }}
            />
          </div>
        </div>
      ))}
    </div>
  )
}

export function ImportanceBars({ items, limit = 10 }: { items: { feature: string; share?: number; importance?: number }[]; limit?: number }) {
  const top = items.slice(0, limit)
  const max = Math.max(...top.map((i) => i.share ?? i.importance ?? 0), 0.0001)
  return (
    <div className="space-y-2.5">
      {top.map((item) => (
        <div key={item.feature} className="grid grid-cols-[minmax(0,1fr)_42px] items-center gap-3">
          <div>
            <div className="mb-1 flex items-center justify-between gap-2">
              <span className="truncate text-[11px] text-charcoal">{item.feature}</span>
            </div>
            <div className="h-1.5 overflow-hidden rounded-full bg-[#EDEBE1]">
              <div className="h-full rounded-full bg-sage" style={{ width: `${((item.share ?? item.importance ?? 0) / max) * 100}%` }} />
            </div>
          </div>
          <span className="tabular text-right text-[11px] text-muted">
            {((item.share ?? item.importance ?? 0) * 100).toFixed(1)}%
          </span>
        </div>
      ))}
    </div>
  )
}

export function ConfusionMatrix({ matrix, classes }: { matrix: number[][]; classes: string[] }) {
  const max = Math.max(...matrix.flat(), 1)
  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[320px] border-separate border-spacing-1 text-[11px]">
        <thead>
          <tr>
            <th className="px-1 pb-1 text-left font-medium text-muted">actual ↓ / predicted →</th>
            {classes.map((name) => (
              <th key={name} className="px-2 pb-1 text-center font-medium capitalize text-muted">
                {name}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {matrix.map((row, i) => (
            <tr key={classes[i] || i}>
              <td className="px-1 py-1 capitalize text-charcoal">{classes[i] || i}</td>
              {row.map((value, j) => {
                const intensity = value / max
                return (
                  <td
                    key={j}
                    className="rounded-md px-2 py-2 text-center tabular"
                    style={{
                      background: `rgba(24, 61, 50, ${0.06 + intensity * 0.55})`,
                      color: intensity > 0.45 ? '#FCFCF9' : '#303832',
                    }}
                  >
                    {value}
                  </td>
                )
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

export function ModelBars({
  models,
  metric = 'balanced_accuracy',
}: {
  models: { model: string; metrics: { balanced_accuracy: number; accuracy: number; f1_macro: number } }[]
  metric?: 'balanced_accuracy' | 'accuracy' | 'f1_macro'
}) {
  const data = models.map((m) => ({ name: m.model.replace('Support Vector Machine', 'SVM'), value: m.metrics[metric] }))
  const colors = [CHART_COLORS.forest, CHART_COLORS.sage, CHART_COLORS.olive, CHART_COLORS.amber]
  return (
    <div style={{ height: 200 }}>
      <ResponsiveContainer>
        <BarChart data={data} margin={{ top: 6, right: 8, left: -22, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 4" stroke="#EAE8DD" vertical={false} />
          <XAxis dataKey="name" tick={axisStyle} tickLine={false} axisLine={{ stroke: '#E4E1D5' }} />
          <YAxis domain={[0, 1]} tick={axisStyle} tickLine={false} axisLine={false} width={42} />
          <Tooltip content={<TooltipCard />} />
          <Bar dataKey="value" name={metric} radius={[5, 5, 0, 0]} maxBarSize={54}>
            {data.map((_, index) => (
              <Cell key={index} fill={colors[index % colors.length]} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}

export function WeeklyBars({
  data,
  height = 210,
}: {
  data: { week_start: string; stress_share: number; neutral_share: number; amusement_share: number }[]
  height?: number
}) {
  return (
    <div style={{ height }}>
      <ResponsiveContainer>
        <BarChart data={data} margin={{ top: 8, right: 8, left: -20, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 4" stroke="#EAE8DD" vertical={false} />
          <XAxis dataKey="week_start" tick={axisStyle} tickLine={false} axisLine={{ stroke: '#E4E1D5' }} />
          <YAxis domain={[0, 100]} tick={axisStyle} tickLine={false} axisLine={false} width={40} unit="%" />
          <Tooltip content={<TooltipCard />} />
          <Bar dataKey="neutral_share" name="Neutral share" stackId="a" fill={CHART_COLORS.sage} maxBarSize={38} />
          <Bar dataKey="amusement_share" name="Amusement share" stackId="a" fill={CHART_COLORS.olive} maxBarSize={38} />
          <Bar dataKey="stress_share" name="Stress-associated share" stackId="a" fill={CHART_COLORS.amber} radius={[4, 4, 0, 0]} maxBarSize={38} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}
