interface SlackInteractionViewerProps {
  readonly channel: string | null;
  readonly messageSent: string | null;
  readonly replyReceived: string | null;
}

export function SlackInteractionViewer({
  channel,
  messageSent,
  replyReceived,
}: SlackInteractionViewerProps): React.JSX.Element {
  return (
    <div className="rounded-lg border border-orange-500/30 bg-orange-950/20 p-3">
      {/* Channel header */}
      <div className="mb-2 flex items-center gap-2">
        <span className="text-lg leading-none">💬</span>
        <span className="text-xs font-semibold text-orange-300">
          Slack Interaction
        </span>
        {channel && (
          <span className="rounded bg-orange-900/50 px-1.5 py-0.5 font-mono text-xs text-orange-200">
            #{channel}
          </span>
        )}
      </div>

      {/* Outbound message */}
      {messageSent && (
        <div className="mb-2">
          <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-gray-500">
            Agent sent
          </p>
          <div className="rounded bg-gray-800 px-3 py-2 text-sm text-gray-200">
            {messageSent}
          </div>
        </div>
      )}

      {/* Reply received */}
      {replyReceived ? (
        <div>
          <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-gray-500">
            Reply received
          </p>
          <div className="rounded bg-gray-700 px-3 py-2 text-sm text-white">
            {replyReceived}
          </div>
        </div>
      ) : (
        <div className="flex items-center gap-2 text-xs text-orange-400">
          <span className="inline-block h-2 w-2 animate-pulse rounded-full bg-orange-400" />
          Awaiting reply…
        </div>
      )}
    </div>
  );
}
