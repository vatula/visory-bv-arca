import { SlackInteractionViewer } from "@/components/SlackInteractionViewer";
import { type AuditEvent } from "@/types/schemas";

interface AuditTimelineProps {
  readonly events: readonly AuditEvent[];
}

export function AuditTimeline({
  events,
}: AuditTimelineProps): React.JSX.Element {
  if (events.length === 0) {
    return (
      <p className="text-sm text-gray-500 italic">No audit events recorded.</p>
    );
  }

  return (
    <ol className="relative border-l border-white/10">
      {events.map((event) => (
        <li key={event.id} className="mb-6 ml-6">
          {/* Timeline dot */}
          <span className="absolute -left-3 flex h-6 w-6 items-center justify-center rounded-full bg-gray-800 ring-2 ring-white/10">
            <span className="h-2 w-2 rounded-full bg-indigo-400" />
          </span>

          {/* Header */}
          <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
            <time className="font-mono text-xs text-gray-500">
              {new Date(event.timestamp).toLocaleString("en-AU")}
            </time>
            <span className="rounded bg-gray-700 px-1.5 py-0.5 text-xs font-semibold text-indigo-300">
              {event.node_name}
            </span>
          </div>

          {/* Action summary */}
          <p className="mt-1 text-sm text-gray-300">{event.action_summary}</p>

          {/* Slack interaction (if present) */}
          {(event.slack_message_sent !== null ||
            event.slack_reply_received !== null) && (
            <div className="mt-3">
              <SlackInteractionViewer
                channel={event.slack_channel}
                messageSent={event.slack_message_sent}
                replyReceived={event.slack_reply_received}
              />
            </div>
          )}
        </li>
      ))}
    </ol>
  );
}
