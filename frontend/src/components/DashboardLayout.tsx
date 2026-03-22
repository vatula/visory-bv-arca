import { QueuePanel } from "@/components/QueuePanel";
import { TransactionCard } from "@/components/TransactionCard";
import { type QueuedTransaction, type TransactionSummary } from "@/types/schemas";

interface DashboardLayoutProps {
  readonly active: readonly TransactionSummary[];
  readonly processed: readonly TransactionSummary[];
  readonly queue: readonly QueuedTransaction[];
  readonly totalRemaining: number;
}

export function DashboardLayout({
  active,
  processed,
  queue,
  totalRemaining,
}: DashboardLayoutProps): React.JSX.Element {
  return (
    <div>
      {/* Up-next queue */}
      <QueuePanel queue={queue} totalRemaining={totalRemaining} />

      {/* Active / Processed two-column grid */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        {/* Active Operations column */}
        <section>
          <div className="mb-3 flex items-center justify-between">
            <h2 className="text-sm font-semibold uppercase tracking-wide text-gray-400">
              Active Operations
            </h2>
            <span className="rounded-full bg-indigo-900/50 px-2 py-0.5 text-xs font-semibold text-indigo-300">
              {active.length}
            </span>
          </div>
          {active.length === 0 ? (
            <p className="rounded-lg border border-dashed border-white/10 py-8 text-center text-sm text-gray-600">
              No active transactions
            </p>
          ) : (
            <ul className="space-y-3">
              {active.slice(0, 10).map((tx) => (
                <li key={tx.transaction_id}>
                  <TransactionCard transaction={tx} />
                </li>
              ))}
            </ul>
          )}
        </section>

        {/* Processed Ledger column */}
        <section>
          <div className="mb-3 flex items-center justify-between">
            <h2 className="text-sm font-semibold uppercase tracking-wide text-gray-400">
              Processed Ledger
            </h2>
            <span className="rounded-full bg-gray-700 px-2 py-0.5 text-xs font-semibold text-gray-300">
              {processed.length}
            </span>
          </div>
          {processed.length === 0 ? (
            <p className="rounded-lg border border-dashed border-white/10 py-8 text-center text-sm text-gray-600">
              No processed transactions
            </p>
          ) : (
            <ul className="space-y-3">
              {processed.slice(0, 10).map((tx) => (
                <li key={tx.transaction_id}>
                  <TransactionCard transaction={tx} />
                </li>
              ))}
            </ul>
          )}
        </section>
      </div>
    </div>
  );
}
