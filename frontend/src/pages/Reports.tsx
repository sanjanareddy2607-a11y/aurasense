import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { ArrowUpRight, FileDown, FileText, Plus, Trash2 } from 'lucide-react'
import { api, ApiError, download } from '../lib/api'
import type { Analysis, ReportRecord } from '../types'
import { Badge, Card, EmptyState, LoadingBlock, Modal, Notice, PageHeader, SectionLabel } from '../components/ui'
import { dateTime, relative } from '../lib/format'

const KIND_LABEL: Record<string, string> = {
  analysis: 'Analysis report',
  research: 'Research report',
  institution: 'Institution aggregate',
}

export default function Reports() {
  const [reports, setReports] = useState<ReportRecord[]>([])
  const [analyses, setAnalyses] = useState<Analysis[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState<string | null>(null)
  const [selected, setSelected] = useState('')
  const [confirmDelete, setConfirmDelete] = useState<ReportRecord | null>(null)

  const load = async () => {
    const [reportResponse, analysisResponse] = await Promise.all([
      api<{ reports: ReportRecord[] }>('/reports'),
      api<{ analyses: Analysis[] }>('/analysis?limit=20'),
    ])
    setReports(reportResponse.reports)
    setAnalyses(analysisResponse.analyses)
    if (!selected && analysisResponse.analyses[0]) setSelected(analysisResponse.analyses[0].id)
  }

  useEffect(() => {
    load()
      .catch((err) => setError(err instanceof ApiError ? err.message : 'Unable to load reports.'))
      .finally(() => setLoading(false))
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const generate = async () => {
    if (!selected) return
    setBusy('generate')
    setError(null)
    try {
      await api(`/reports/analysis/${selected}`, { method: 'POST', body: {} })
      await load()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Unable to generate the report.')
    } finally {
      setBusy(null)
    }
  }

  const downloadReport = async (report: ReportRecord) => {
    setBusy(report.id)
    setError(null)
    try {
      await download(`/reports/${report.id}/download`, `aurasense-${report.kind}-${report.id.slice(0, 8)}.pdf`)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Unable to download the report.')
    } finally {
      setBusy(null)
    }
  }

  const remove = async () => {
    if (!confirmDelete) return
    setBusy(confirmDelete.id)
    try {
      await api(`/reports/${confirmDelete.id}`, { method: 'DELETE' })
      setConfirmDelete(null)
      await load()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Unable to delete the report.')
    } finally {
      setBusy(null)
    }
  }

  if (loading) return <LoadingBlock label="Loading report history" />

  return (
    <div>
      <PageHeader
        eyebrow="Reports & History"
        title="A record you can take with you."
        description="Generate PDF reports from stored analyses, keep a versioned history, and download or remove reports at any time."
      />

      {error && (
        <Notice tone="danger" className="mb-4">
          {error}
        </Notice>
      )}

      <div className="grid gap-4 xl:grid-cols-[1.5fr_1fr]">
        <Card className="overflow-hidden">
          <div className="flex items-center justify-between px-5 pb-3 pt-5">
            <div>
              <SectionLabel>Library</SectionLabel>
              <h2 className="mt-1 font-display text-lg text-forest">Generated reports</h2>
            </div>
            <Badge>{reports.length} files</Badge>
          </div>

          {reports.length ? (
            <div className="divide-y divide-line">
              {reports.map((report) => (
                <div key={report.id} className="flex flex-wrap items-center gap-3 px-5 py-3.5">
                  <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-[#F1EFE4] text-[#7C855F]">
                    <FileText size={15} />
                  </span>
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-[12px] font-medium text-charcoal">{report.title}</p>
                    <p className="mt-0.5 text-[10px] text-muted">
                      {KIND_LABEL[report.kind] || report.kind} · {dateTime(report.created_at)}
                      {report.analysis_id && (
                        <>
                          {' · '}
                          <Link to={`/app/analysis/${report.analysis_id}`} className="inline-flex items-center gap-0.5 text-forest hover:underline">
                            source <ArrowUpRight size={10} />
                          </Link>
                        </>
                      )}
                    </p>
                  </div>
                  <div className="flex items-center gap-1">
                    <button
                      onClick={() => downloadReport(report)}
                      disabled={busy === report.id}
                      className="btn btn-secondary px-2.5 py-1 text-[10px]"
                    >
                      <FileDown size={12} /> {busy === report.id ? '…' : 'PDF'}
                    </button>
                    <button
                      onClick={() => setConfirmDelete(report)}
                      className="rounded-full p-1.5 text-muted transition hover:bg-[#FAEDE9] hover:text-[#A45545]"
                      aria-label="Delete report"
                    >
                      <Trash2 size={13} />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="px-5 pb-6">
              <EmptyState
                icon={<FileText size={18} />}
                title="No reports yet"
                description="Choose an analysed record on the right to generate your first PDF. Reports include the source, model version, quality and limitations."
              />
            </div>
          )}
        </Card>

        <div className="space-y-4">
          <Card className="p-5">
            <div className="flex items-center justify-between">
              <div>
                <SectionLabel>New report</SectionLabel>
                <h2 className="mt-1 font-display text-lg text-forest">From an analysis</h2>
              </div>
              <Plus size={16} className="text-sage" />
            </div>
            {analyses.length ? (
              <>
                <select className="field mt-3" value={selected} onChange={(event) => setSelected(event.target.value)}>
                  {analyses.map((analysis) => (
                    <option key={analysis.id} value={analysis.id}>
                      {analysis.title} · {relative(analysis.created_at)}
                    </option>
                  ))}
                </select>
                <button onClick={generate} disabled={busy === 'generate' || !selected} className="btn btn-primary mt-3 w-full py-2.5">
                  <FileDown size={14} /> {busy === 'generate' ? 'Generating…' : 'Generate PDF report'}
                </button>
                <p className="mt-2 text-[10px] leading-relaxed text-muted">
                  PDFs are generated by the backend from stored values, including a visible quality assessment and the
                  non-diagnostic disclaimer.
                </p>
              </>
            ) : (
              <div className="mt-3">
                <EmptyState title="No analyses available" description="Complete a session or upload a signal first." />
              </div>
            )}
          </Card>

          <Card className="p-5">
            <SectionLabel>Report contents</SectionLabel>
            <ul className="mt-2 space-y-2 text-[10.5px] leading-relaxed text-muted">
              <li>· Estimate, class probabilities and uncertainty</li>
              <li>· Signal source, window count, duration and quality</li>
              <li>· Top local feature contributions and model version</li>
              <li>· Explicit limitations and non-diagnostic notice</li>
            </ul>
            <p className="mt-3 border-t border-line pt-2 text-[9.5px] leading-relaxed text-muted">
              Reports are for personal review or research documentation. They are not clinical documents.
            </p>
          </Card>
        </div>
      </div>

      <Modal
        open={Boolean(confirmDelete)}
        onClose={() => setConfirmDelete(null)}
        title="Delete this report?"
        description="The PDF file and its history entry will be removed. The underlying analysis remains available."
        footer={
          <>
            <button className="btn btn-secondary" onClick={() => setConfirmDelete(null)}>
              Keep report
            </button>
            <button className="btn btn-danger" onClick={remove} disabled={busy === confirmDelete?.id}>
              Delete
            </button>
          </>
        }
      >
        <p className="truncate text-[11px] text-muted">{confirmDelete?.title}</p>
      </Modal>
    </div>
  )
}
