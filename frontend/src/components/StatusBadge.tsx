import { getStatusMeta, type TransactionStatus } from "@/types/schemas";

interface StatusBadgeProps {
  readonly status: TransactionStatus;
}

export function StatusBadge({ status }: StatusBadgeProps): React.JSX.Element {
  const meta = getStatusMeta(status);
  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold ${meta.bgColour} ${meta.colour} ring-1 ring-inset ring-white/10`}
    >
      {meta.label}
    </span>
  );
}
