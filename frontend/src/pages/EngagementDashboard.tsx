import { useParams, Link } from 'react-router-dom';
import { AlertCircle, ArrowLeft, Loader2, Play, CheckCircle2, FileX, BarChart3, Clock, Database, FileText, AlertTriangle } from 'lucide-react';
import { StatusBadge } from '@/components/ui/StatusBadge';
import { SchemaBuilder } from '@/components/schema/SchemaBuilder';
import { useEngagement, useEngagementProgress, useActivateEngagement, useRejectedDocuments } from '@/hooks/useEngagements';

function ProgressCard({ label, count, icon: Icon, colorClass }: { label: string; count: number; icon: React.ElementType; colorClass: string }) {
  return (
    <div className="flex flex-col gap-2 rounded-xl border border-gray-200 bg-white p-4 shadow-sm">
      <div className="flex items-center gap-2 text-sm font-medium text-gray-500">
        <Icon className={`h-4 w-4 ${colorClass}`} />
        {label}
      </div>
      <div className="text-2xl font-semibold text-gray-900">{count.toLocaleString()}</div>
    </div>
  );
}

export default function EngagementDashboard() {
  const { id } = useParams<{ id: string }>();
  const engagementId = id ?? '';
  const { data: engagement, isLoading, isError } = useEngagement(engagementId);
  const activateMutation = useActivateEngagement();

  const isProcessing = engagement?.status === 'processing';
  const isComplete = engagement?.status === 'complete';
  const isDraft = engagement?.status === 'draft';

  // Progress hook automatically polls if isProcessing is true
  const { data: progress } = useEngagementProgress(engagementId, isProcessing || isComplete);

  // Only query rejected documents if we actually have some to avoid unnecessary calls
  const hasRejects = (progress?.rejected ?? 0) > 0 || (progress?.download_failed ?? 0) > 0 || (progress?.extraction_failed ?? 0) > 0;
  const { data: rejectedDocs } = useRejectedDocuments(engagementId, hasRejects);

  if (isLoading) {
    return (
      <div className="flex items-center gap-2 py-20 text-gray-400">
        <Loader2 className="h-5 w-5 animate-spin" />
        <span className="text-sm">Loading engagement…</span>
      </div>
    );
  }

  if (isError || !engagement) {
    return (
      <div className="space-y-4">
        <Link
          to="/"
          className="inline-flex items-center gap-1 text-sm text-gray-500 hover:text-gray-700"
        >
          <ArrowLeft className="h-4 w-4" /> Back to engagements
        </Link>
        <div className="flex items-center gap-2 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          <AlertCircle className="h-4 w-4 shrink-0" />
          Engagement not found or you do not have access.
        </div>
      </div>
    );
  }

  const handleActivate = () => {
    activateMutation.mutate(engagementId);
  };

  const percentComplete = progress?.percent_complete ?? 0;

  return (
    <div className="space-y-8">
      {/* ── Engagement header ─────────────────────────────────────────── */}
      <div className="flex items-start justify-between">
        <div>
          <Link
            to="/"
            className="mb-4 inline-flex items-center gap-1 text-sm text-gray-400 hover:text-gray-600 transition-colors"
          >
            <ArrowLeft className="h-4 w-4" /> All engagements
          </Link>

          <div className="flex flex-wrap items-center gap-3">
            <h1 className="text-2xl font-semibold text-gray-900">
              {engagement.project_name}
            </h1>
            <StatusBadge status={engagement.status} />
          </div>

          <p className="mt-1 text-sm text-gray-500">
            {engagement.client_name}
            <span className="mx-2 text-gray-300">·</span>
            {engagement.client_id}
            <span className="mx-2 text-gray-300">·</span>
            Tax Year {engagement.tax_year}
          </p>
        </div>

        {/* Activation Controls */}
        <div>
          {isDraft && (
            <button
              onClick={handleActivate}
              disabled={activateMutation.isPending}
              className="inline-flex items-center gap-2 rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
            >
              {activateMutation.isPending ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Play className="h-4 w-4" />
              )}
              Activate Processing
            </button>
          )}
          {(isProcessing || isComplete) && (
            <div className="inline-flex items-center gap-2 rounded-md bg-indigo-50 px-4 py-2 text-sm font-medium text-indigo-700 border border-indigo-200">
              {isProcessing ? <Loader2 className="h-4 w-4 animate-spin" /> : <CheckCircle2 className="h-4 w-4" />}
              {isProcessing ? 'Processing Active' : 'Pipeline Complete'}
            </div>
          )}
        </div>
      </div>

      {/* ── Progress Pipeline Tracker (Only visible if active or complete) ── */}
      {(isProcessing || isComplete) && progress && (
        <div className="space-y-6">
          <div className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
            <div className="mb-4 flex items-center justify-between">
              <h3 className="text-lg font-medium text-gray-900 flex items-center gap-2">
                <BarChart3 className="h-5 w-5 text-indigo-500" />
                Pipeline Progress
              </h3>
              <div className="text-sm font-medium text-gray-500">
                {percentComplete.toFixed(1)}% Complete
              </div>
            </div>

            {/* Progress Bar */}
            <div className="h-4 w-full overflow-hidden rounded-full bg-gray-100">
              <div
                className="h-full bg-indigo-600 transition-all duration-500 ease-out"
                style={{ width: `${percentComplete}%` }}
              />
            </div>

            {/* Stage Counters */}
            <div className="mt-6 grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-6">
              <ProgressCard label="Discovered" count={progress.discovered} icon={Database} colorClass="text-blue-500" />
              <ProgressCard label="Validated" count={progress.validated} icon={CheckCircle2} colorClass="text-emerald-500" />
              <ProgressCard label="Downloaded" count={progress.downloaded} icon={FileText} colorClass="text-cyan-500" />
              <ProgressCard label="Extracting" count={progress.extracting + progress.queued} icon={Clock} colorClass="text-amber-500" />
              <ProgressCard label="Reviewed" count={progress.confirmed + progress.corrected + progress.auto_approved} icon={CheckCircle2} colorClass="text-indigo-500" />
              <ProgressCard label="Rejected/Failed" count={progress.rejected + progress.download_failed + progress.extraction_failed} icon={FileX} colorClass="text-red-500" />
            </div>
          </div>

          {/* Rejected Documents Panel */}
          {hasRejects && rejectedDocs && rejectedDocs.length > 0 && (
            <div className="rounded-xl border border-red-200 bg-white shadow-sm overflow-hidden">
              <div className="bg-red-50 px-6 py-4 border-b border-red-100 flex items-center gap-2">
                <AlertTriangle className="h-5 w-5 text-red-600" />
                <h3 className="text-sm font-medium text-red-900">Rejected Documents ({rejectedDocs.length})</h3>
              </div>
              <div className="max-h-96 overflow-y-auto p-0">
                <table className="min-w-full divide-y divide-gray-200">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Filename</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Reason</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Time</th>
                    </tr>
                  </thead>
                  <tbody className="bg-white divide-y divide-gray-200">
                    {rejectedDocs.map((doc) => (
                      <tr key={doc.id}>
                        <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                          {doc.filename}
                        </td>
                        <td className="px-6 py-4 text-sm text-red-600">
                          {doc.rejection_reason || doc.error_detail || "Unknown error"}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                          {new Date(doc.discovered_at).toLocaleString()}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      )}

      {/* ── Schema builder ────────────────────────────────────────────── */}
      <div className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
        <SchemaBuilder engagementId={engagement.id} locked={isProcessing || isComplete} />
      </div>
    </div>
  );
}

