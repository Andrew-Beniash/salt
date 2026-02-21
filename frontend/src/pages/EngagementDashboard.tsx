import { useParams, Link } from 'react-router-dom';
import { AlertCircle, ArrowLeft, Loader2 } from 'lucide-react';
import { StatusBadge } from '@/components/ui/StatusBadge';
import { SchemaBuilder } from '@/components/schema/SchemaBuilder';
import { useEngagement } from '@/hooks/useEngagements';

export default function EngagementDashboard() {
  const { id } = useParams<{ id: string }>();
  const { data: engagement, isLoading, isError } = useEngagement(id ?? '');

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

  const locked =
    engagement.status === 'processing' || engagement.status === 'complete';

  return (
    <div className="space-y-8">
      {/* ── Engagement header ─────────────────────────────────────────── */}
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

      {/* ── Schema builder ────────────────────────────────────────────── */}
      <div className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
        <SchemaBuilder engagementId={engagement.id} locked={locked} />
      </div>
    </div>
  );
}
