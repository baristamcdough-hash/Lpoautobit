interface StatusBadgeProps {
  status: 'pending' | 'processing' | 'completed' | 'error';
}

const statusStyles: Record<string, string> = {
  pending: 'bg-amber-50 text-amber-700 border border-amber-200',
  processing: 'bg-sky-50 text-sky-700 border border-sky-200',
  completed: 'bg-teal-50 text-teal-700 border border-teal-200',
  error: 'bg-red-50 text-red-700 border border-red-200',
};

export default function StatusBadge({ status }: StatusBadgeProps) {
  return (
    <span
      className={`inline-flex items-center px-2 py-0.5 rounded-md text-xs font-medium ${statusStyles[status] || statusStyles.pending}`}
    >
      {status}
    </span>
  );
}
