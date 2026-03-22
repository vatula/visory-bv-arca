import Link from "next/link";
import { StatusBadge } from "@/components/StatusBadge";
import { type TransactionSummary } from "@/types/schemas";

interface TransactionCardProps {
  readonly transaction: TransactionSummary;
}

export function TransactionCard({
  transaction,
}: TransactionCardProps): React.JSX.Element {
  const amountDisplay =
    transaction.amount !== null
      ? new Intl.NumberFormat("en-AU", {
          style: "currency",
          currency: "AUD",
        }).format(transaction.amount)
      : "—";

  return (
    <Link
      href={`/transactions/${encodeURIComponent(transaction.transaction_id)}`}
      className="block rounded-lg border border-white/10 bg-gray-900 p-4 transition hover:border-white/25 hover:bg-gray-800"
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <p className="truncate text-sm font-semibold text-white">
            {transaction.merchant ?? transaction.transaction_id}
          </p>
          {transaction.employee_name && (
            <p className="mt-0.5 truncate text-xs text-gray-400">
              {transaction.employee_name}
            </p>
          )}
        </div>
        <div className="flex flex-col items-end gap-1.5 shrink-0">
          <span className="text-sm font-mono font-semibold text-white">
            {amountDisplay}
          </span>
          <StatusBadge status={transaction.status} />
        </div>
      </div>
      <p className="mt-2 text-xs text-gray-500">
        {new Date(transaction.last_updated).toLocaleString("en-AU")}
      </p>
    </Link>
  );
}
