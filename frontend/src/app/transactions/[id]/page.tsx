import Link from "next/link";
import { notFound } from "next/navigation";
import { AuditTimeline } from "@/components/AuditTimeline";
import { StatusBadge } from "@/components/StatusBadge";
import { SynthesisMetrics } from "@/components/SynthesisMetrics";
import { fetchTransactionAudit } from "@/lib/api";
import { TransactionStatusSchema } from "@/types/schemas";

interface TransactionDetailPageProps {
  readonly params: Promise<{ readonly id: string }>;
}

export default async function TransactionDetailPage({
  params,
}: TransactionDetailPageProps): Promise<React.JSX.Element> {
  const { id } = await params;

  let data: Awaited<ReturnType<typeof fetchTransactionAudit>>;
  try {
    data = await fetchTransactionAudit(id);
  } catch {
    notFound();
  }

  const { transaction, audit_trail } = data;

  const statusParsed = TransactionStatusSchema.safeParse(transaction.status);
  const validStatus = statusParsed.success ? statusParsed.data : "pending";

  const amountDisplay =
    transaction.amount !== null
      ? new Intl.NumberFormat("en-AU", {
          style: "currency",
          currency: "AUD",
        }).format(transaction.amount)
      : "—";

  return (
    <div className="space-y-8">
      {/* Breadcrumb */}
      <nav className="flex items-center gap-2 text-sm text-gray-500">
        <Link href="/dashboard" className="hover:text-white transition-colors">
          Dashboard
        </Link>
        <span>/</span>
        <span className="truncate font-mono text-gray-300">{id}</span>
      </nav>

      {/* Transaction Ground Truth */}
      <section className="rounded-lg border border-white/10 bg-gray-900 p-6">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <h1 className="text-lg font-bold text-white">
              {transaction.merchant ?? id}
            </h1>
            {transaction.employee_name && (
              <p className="mt-0.5 text-sm text-gray-400">
                {transaction.employee_name}
              </p>
            )}
          </div>
          <div className="flex flex-col items-end gap-2">
            <span className="font-mono text-2xl font-bold text-white">
              {amountDisplay}
            </span>
            <StatusBadge status={validStatus} />
          </div>
        </div>

        <dl className="mt-6 grid grid-cols-2 gap-4 sm:grid-cols-4">
          <div>
            <dt className="text-xs font-semibold uppercase tracking-wide text-gray-500">
              Transaction ID
            </dt>
            <dd className="mt-1 truncate font-mono text-xs text-gray-300">
              {transaction.transaction_id}
            </dd>
          </div>
          <div>
            <dt className="text-xs font-semibold uppercase tracking-wide text-gray-500">
              Status
            </dt>
            <dd className="mt-1 text-xs text-gray-300">{transaction.status}</dd>
          </div>
          <div>
            <dt className="text-xs font-semibold uppercase tracking-wide text-gray-500">
              Last Updated
            </dt>
            <dd className="mt-1 text-xs text-gray-300">
              {new Date(transaction.last_updated).toLocaleString("en-AU")}
            </dd>
          </div>
          <div>
            <dt className="text-xs font-semibold uppercase tracking-wide text-gray-500">
              Audit Events
            </dt>
            <dd className="mt-1 text-xs text-gray-300">{audit_trail.length}</dd>
          </div>
        </dl>
      </section>

      {/* Synthesis Evaluation */}
      <section>
        <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-gray-400">
          Synthesis & Evaluation
        </h2>
        <SynthesisMetrics
          confidenceScore={transaction.confidence_score}
          synthesisReasoning={transaction.synthesis_reasoning}
        />
      </section>

      {/* Agentic Audit Trail */}
      <section>
        <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-gray-400">
          Agentic Audit Trail
        </h2>
        <AuditTimeline events={audit_trail} />
      </section>
    </div>
  );
}
