interface SynthesisMetricsProps {
  readonly confidenceScore: number | null;
  readonly synthesisReasoning: string | null;
}

export function SynthesisMetrics({
  confidenceScore,
  synthesisReasoning,
}: SynthesisMetricsProps): React.JSX.Element {
  const pct =
    confidenceScore !== null ? Math.round(confidenceScore * 100) : null;

  const barColour =
    pct === null
      ? "bg-gray-600"
      : pct >= 75
        ? "bg-green-500"
        : pct >= 50
          ? "bg-amber-500"
          : "bg-red-500";

  const scoreLabel =
    pct === null
      ? "N/A"
      : pct >= 75
        ? "High confidence"
        : pct >= 50
          ? "Moderate confidence"
          : "Low confidence — escalated";

  return (
    <div className="rounded-lg border border-white/10 bg-gray-900 p-4 space-y-4">
      <h3 className="text-sm font-semibold text-white">Synthesis Evaluation</h3>

      {/* Confidence score bar */}
      <div>
        <div className="mb-1 flex items-center justify-between text-xs text-gray-400">
          <span>{scoreLabel}</span>
          <span className="font-mono font-semibold text-white">
            {pct !== null ? `${pct}%` : "—"}
          </span>
        </div>
        <div className="h-2 w-full overflow-hidden rounded-full bg-gray-700">
          <div
            className={`h-full rounded-full transition-all ${barColour}`}
            style={{ width: pct !== null ? `${pct}%` : "0%" }}
            role="progressbar"
            aria-valuenow={pct ?? 0}
            aria-valuemin={0}
            aria-valuemax={100}
          />
        </div>
      </div>

      {/* Agent reasoning */}
      {synthesisReasoning ? (
        <div>
          <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-gray-500">
            Agent reasoning
          </p>
          <p className="text-sm text-gray-300 leading-relaxed">
            {synthesisReasoning}
          </p>
        </div>
      ) : (
        <p className="text-sm text-gray-600 italic">No reasoning recorded.</p>
      )}
    </div>
  );
}
