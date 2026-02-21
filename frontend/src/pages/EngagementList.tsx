import { Link } from 'react-router-dom';
import { Plus, AlertCircle, Loader2, FolderOpen } from 'lucide-react';
import { StatusBadge } from '@/components/ui/StatusBadge';
import { useEngagements } from '@/hooks/useEngagements';
import type { Engagement } from '@/types/engagement';

function formatDate(iso: string) {
  return new Date(iso).toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  });
}

export default function EngagementList() {
  const { data: engagements, isLoading, isError } = useEngagements();

  return (
    <div className="space-y-6">
      {/* Header ─────────────────────────────────────────────────────────── */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-gray-900">Engagements</h1>
          <p className="mt-1 text-sm text-gray-500">
            All client tax engagements you have access to.
          </p>
        </div>
        <Link
          to="/engagements/new"
          className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-blue-700 transition-colors"
        >
          <Plus className="h-4 w-4" />
          New Engagement
        </Link>
      </div>

      {/* Loading ─────────────────────────────────────────────────────────── */}
      {isLoading && (
        <div className="flex items-center justify-center gap-2 py-20 text-gray-400">
          <Loader2 className="h-5 w-5 animate-spin" />
          <span className="text-sm">Loading engagements…</span>
        </div>
      )}

      {/* Error ───────────────────────────────────────────────────────────── */}
      {isError && (
        <div className="flex items-center gap-2 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          <AlertCircle className="h-4 w-4 shrink-0" />
          Failed to load engagements. Please refresh the page.
        </div>
      )}

      {/* Table ───────────────────────────────────────────────────────────── */}
      {!isLoading && !isError && engagements && (
        <>
          {engagements.length === 0 ? (
            <EmptyState />
          ) : (
            <div className="overflow-hidden rounded-lg border border-gray-200 bg-white shadow-sm">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-gray-200 bg-gray-50/80">
                    <Th>Client Name</Th>
                    <Th>Project Name</Th>
                    <Th>Tax Year</Th>
                    <Th>Status</Th>
                    <Th>Documents</Th>
                    <Th>Created</Th>
                    <th className="w-16" />
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {engagements.map((eng) => (
                    <EngagementRow key={eng.id} engagement={eng} />
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </>
      )}
    </div>
  );
}

// ─── Sub-components ───────────────────────────────────────────────────────────

function Th({ children }: { children: React.ReactNode }) {
  return (
    <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-gray-500">
      {children}
    </th>
  );
}

function EngagementRow({ engagement: eng }: { engagement: Engagement }) {
  return (
    <tr className="group hover:bg-blue-50/40 transition-colors">
      <td className="px-4 py-3 font-medium text-gray-900">{eng.client_name}</td>
      <td className="px-4 py-3 text-gray-700">{eng.project_name}</td>
      <td className="px-4 py-3 text-gray-700">{eng.tax_year}</td>
      <td className="px-4 py-3">
        <StatusBadge status={eng.status} />
      </td>
      {/* Document count requires the documents API — shown once available */}
      <td className="px-4 py-3 text-gray-400">—</td>
      <td className="px-4 py-3 text-gray-500">{formatDate(eng.created_at)}</td>
      <td className="px-4 py-3">
        <Link
          to={`/engagements/${eng.id}`}
          className="text-sm font-medium text-blue-600 opacity-0 group-hover:opacity-100 hover:text-blue-800 transition-all"
        >
          View →
        </Link>
      </td>
    </tr>
  );
}

function EmptyState() {
  return (
    <div className="flex flex-col items-center justify-center gap-3 rounded-lg border-2 border-dashed border-gray-200 py-20">
      <FolderOpen className="h-10 w-10 text-gray-300" />
      <div className="text-center">
        <p className="text-sm font-medium text-gray-500">No engagements yet</p>
        <p className="text-xs text-gray-400 mt-0.5">Create your first engagement to get started.</p>
      </div>
      <Link
        to="/engagements/new"
        className="mt-1 inline-flex items-center gap-1.5 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 transition-colors"
      >
        <Plus className="h-4 w-4" />
        New Engagement
      </Link>
    </div>
  );
}
