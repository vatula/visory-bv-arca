import pino from "pino";

// ---------------------------------------------------------------------------
// Trace ID — injected once at module initialisation so every log shares it.
// In production the value should come from a server-side header (e.g. x-trace-id)
// propagated via a cookie or meta tag. For the prototype we generate a UUID.
// ---------------------------------------------------------------------------

function generateTraceId(): string {
  if (typeof crypto !== "undefined" && crypto.randomUUID) {
    return crypto.randomUUID();
  }
  // Fallback for environments without crypto.randomUUID
  return `trace-${Date.now()}-${Math.random().toString(36).slice(2)}`;
}

const TRACE_ID: string =
  (typeof window !== "undefined" &&
    (document.head
      .querySelector<HTMLMetaElement>('meta[name="x-trace-id"]')
      ?.content)) ||
  generateTraceId();

// ---------------------------------------------------------------------------
// Transport configuration
// In the browser we ship logs to the backend telemetry ingest endpoint using
// a batching transport instead of defaulting to console.
// In Node.js (SSR) we write structured JSON to stdout via pino-pretty in dev.
// ---------------------------------------------------------------------------

function buildTransport(): pino.TransportSingleOptions | undefined {
  if (typeof window === "undefined") {
    // Server-side (SSR / Next.js API routes): plain JSON stdout
    return undefined;
  }
  // Client-side: batch logs and POST to backend ingest.
  // Uses navigator.sendBeacon for fatal flush safety (see AGENTS.md).
  return {
    target: "pino/browser",
    options: {
      serialize: true,
      asObject: true,
      transmit: {
        level: "warn",
        send: (
          level: string,
          logEvent: { messages: readonly unknown[] },
        ): void => {
          const body = JSON.stringify({ level, event: logEvent });
          if (level === "fatal" || level === "error") {
            // Synchronous flush for unrecoverable crashes (AGENTS.md fatal rule)
            navigator.sendBeacon("/api/v1/telemetry/ingest", body);
          } else {
            // Best-effort async for warn+ batching
            void fetch("/api/v1/telemetry/ingest", {
              method: "POST",
              headers: { "content-type": "application/json" },
              body,
              keepalive: true,
            });
          }
        },
      },
    },
  };
}

// ---------------------------------------------------------------------------
// Root logger — all child loggers inherit trace_id automatically
// ---------------------------------------------------------------------------

const transport = buildTransport();

export const logger = pino(
  {
    level: process.env.NODE_ENV === "production" ? "info" : "debug",
    browser: typeof window !== "undefined" ? { asObject: true } : undefined,
    base: { trace_id: TRACE_ID, service: "arcra-frontend" },
    timestamp: pino.stdTimeFunctions.isoTime,
  },
  transport as pino.DestinationStream | undefined,
);

// ---------------------------------------------------------------------------
// Factory for component-scoped child loggers (AGENTS.md systemic rule)
// ---------------------------------------------------------------------------

export function getComponentLogger(
  component: string,
  context?: Record<string, unknown>,
): pino.Logger {
  return logger.child({ component, ...context });
}
