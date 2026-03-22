import { type QueuedTransaction } from "@/types/schemas";

interface QueuePanelProps {
  readonly queue: readonly QueuedTransaction[];
  readonly totalRemaining: number;
}

export function QueuePanel({
  queue,
  totalRemaining,
}: QueuePanelProps): React.JSX.Element {
  return (
    <section className="mb-6">
      <div className="mb-3 flex items-center justify-between">
        <h2 className="text-sm font-semibold uppercase tracking-wide text-gray-400">
          Up Next
        </h2>
        <span className="rounded-full bg-gray-700 px-2 py-0.5 text-xs font-semibold text-gray-300">
          {totalRemaining} remaining
        </span>
      </div>
      {queue.length === 0 ? (
        <p className="rounded-lg border border-dashed border-white/10 py-6 text-center text-sm text-gray-600">
          Queue empty
        </p>
      ) : (
        <ol className="space-y-2">
          {queue.map((tx, i) => (
            <li
              key={tx.transaction_id}
              className="flex items-center gap-3 rounded-lg border border-white/5 bg-white/[0.03] px-3 py-2 text-sm"
            >
              <span className="w-5 shrink-0 text-center text-xs text-gray-600">
                {i + 1}
              </span>
              <span className="flex-1 truncate text-gray-300">
                {tx.description}
              </span>
              <span className="shrink-0 font-mono text-xs text-gray-400">
                {tx.currency} {Math.abs(tx.amount).toFixed(2)}
              </span>
              <span className="shrink-0 text-xs text-gray-600">{tx.date}</span>
            </li>
          ))}
        </ol>
      )}
    </section>
  );
}
