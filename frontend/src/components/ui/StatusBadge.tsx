import { cn } from '@/lib/utils';
import type { EngagementStatus } from '@/types/engagement';

const STYLES: Record<EngagementStatus, string> = {
  draft:      'bg-gray-100 text-gray-600 ring-gray-500/20',
  active:     'bg-blue-50 text-blue-700 ring-blue-600/20',
  processing: 'bg-amber-50 text-amber-700 ring-amber-600/20',
  complete:   'bg-green-50 text-green-700 ring-green-600/20',
  error:      'bg-red-50 text-red-700 ring-red-600/20',
};

const LABELS: Record<EngagementStatus, string> = {
  draft:      'Draft',
  active:     'Active',
  processing: 'Processing',
  complete:   'Complete',
  error:      'Error',
};

interface StatusBadgeProps {
  status: string;
  className?: string;
}

export function StatusBadge({ status, className }: StatusBadgeProps) {
  const s = status as EngagementStatus;
  return (
    <span
      className={cn(
        'inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ring-1 ring-inset',
        STYLES[s] ?? 'bg-gray-100 text-gray-600 ring-gray-500/20',
        className,
      )}
    >
      {LABELS[s] ?? status}
    </span>
  );
}
