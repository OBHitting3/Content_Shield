"use client";

import type { LeadEvent } from "@/types/database";

const EVENT_LABELS: Record<string, string> = {
  created: "Lead Created",
  status_changed: "Status Changed",
  email_sent: "Email Sent",
  email_opened: "Email Opened",
  email_replied: "Email Replied",
  sms_sent: "SMS Sent",
  slack_posted: "Slack Posted",
  note_added: "Note Added",
  assigned: "Lead Assigned",
  followup_scheduled: "Follow-up Scheduled",
  followup_sent: "Follow-up Sent",
  webhook_fired: "Webhook Fired",
  custom: "Custom Event",
};

const SOURCE_COLORS: Record<string, string> = {
  app: "#2563eb",
  n8n: "#d97706",
  system: "#6c757d",
  edge_function: "#16a34a",
};

export function LeadTimeline({ events }: { events: LeadEvent[] }) {
  if (events.length === 0) {
    return (
      <p style={{ color: "var(--text-muted)", fontSize: "0.9rem" }}>
        No events yet.
      </p>
    );
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
      {events.map((event) => (
        <div
          key={event.id}
          style={{
            borderLeft: `3px solid ${SOURCE_COLORS[event.source] || "#ccc"}`,
            paddingLeft: "0.75rem",
          }}
        >
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "baseline",
            }}
          >
            <span style={{ fontWeight: 600, fontSize: "0.85rem" }}>
              {EVENT_LABELS[event.event_type] || event.event_type}
            </span>
            <span style={{ fontSize: "0.7rem", color: "var(--text-muted)" }}>
              {event.source}
            </span>
          </div>
          <p style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>
            {new Date(event.created_at).toLocaleString()}
          </p>
          {event.payload && Object.keys(event.payload).length > 0 && (
            <EventPayloadDisplay payload={event.payload} />
          )}
        </div>
      ))}
    </div>
  );
}

function EventPayloadDisplay({
  payload,
}: {
  payload: Record<string, unknown>;
}) {
  if (payload.note) {
    return (
      <p
        style={{
          fontSize: "0.85rem",
          marginTop: "0.25rem",
          background: "var(--bg-secondary)",
          padding: "0.5rem",
          borderRadius: "var(--radius)",
          whiteSpace: "pre-wrap",
        }}
      >
        {String(payload.note)}
      </p>
    );
  }

  if (payload.from && payload.to) {
    return (
      <p style={{ fontSize: "0.8rem", marginTop: "0.25rem", color: "var(--text-muted)" }}>
        {String(payload.from)} &rarr; {String(payload.to)}
      </p>
    );
  }

  const display = Object.entries(payload)
    .filter(([k]) => k !== "idempotency_key")
    .map(([k, v]) => `${k}: ${JSON.stringify(v)}`)
    .join(", ");

  if (!display) return null;

  return (
    <p
      style={{
        fontSize: "0.75rem",
        marginTop: "0.25rem",
        color: "var(--text-muted)",
        fontFamily: "monospace",
      }}
    >
      {display}
    </p>
  );
}
