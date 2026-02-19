# n8n Workflow — LeadLatch Speed-to-Lead Autopilot

## Overview

This workflow is triggered by the `lead-intake` Supabase Edge Function when a new lead is created. It handles:

1. **Immediate welcome email** to the lead
2. **Status update** (new → working) via the event-ingest endpoint
3. **Scheduled follow-ups** (24h and 96h after creation)
4. **Slack notification** (optional, parallel branch)
5. **Event logging** — every action writes back to Supabase via `n8n-event-ingest`

## Node Sequence

```
[Webhook Trigger]
    │
    ▼
[Generate Idempotency Keys]
    │
    ├──────────────────────────┐
    ▼                          ▼
[Has Email?]              [Post to Slack]
    │                          │
    ├── YES                    ▼
    │   ▼                 [Log Slack Event]
    │  [Send Welcome Email]
    │   │
    │   ▼
    │  [Log Email Event]
    │   │
    │   ▼
    │  [Update Status → Working]
    │   │
    │   ▼
    │  [Wait 24h]
    │   │
    │   ▼
    │  [Send Follow-up 1]
    │   │
    │   ▼
    │  [Log Follow-up 1]
    │   │
    │   ▼
    │  [Wait 72h]
    │   │
    │   ▼
    │  [Send Follow-up 2]
    │   │
    │   ▼
    │  [Log Follow-up 2]
    │
    └── NO → [Post to Slack] (still notifies team)
```

## Webhook Payload Shape

The `lead-intake` Edge Function sends this JSON:

```json
{
  "lead_id": "550e8400-e29b-41d4-a716-446655440000",
  "org_id": "660e8400-e29b-41d4-a716-446655440000",
  "name": "Jane Doe",
  "email": "jane@example.com",
  "phone": "+1-555-123-4567",
  "message": "Interested in your service",
  "source_url": "https://yoursite.com/pricing",
  "utm_source": "google",
  "created_at": "2026-02-19T12:00:00.000Z"
}
```

## Event-Ingest Callback Shape

Every n8n action writes back to Supabase using HTTP POST to `/functions/v1/n8n-event-ingest`:

```json
{
  "lead_id": "uuid",
  "org_id": "uuid",
  "event_type": "email_sent | followup_sent | slack_posted | status_changed",
  "idempotency_key": "lead_id_action_name",
  "payload": { "template": "welcome", "to": "jane@example.com" },
  "new_status": "working"
}
```

Headers required:
- `Content-Type: application/json`
- `x-leadlatch-secret: <your-shared-secret>`

## Idempotency Strategy

Each action generates a deterministic key: `{lead_id}_{action_name}`.

| Action | Key Pattern |
|--------|-------------|
| Welcome email | `{lead_id}_welcome_email` |
| Follow-up 1 | `{lead_id}_followup_1` |
| Follow-up 2 | `{lead_id}_followup_2` |
| Slack notification | `{lead_id}_slack_notify` |
| Status → working | `{lead_id}_status_working` |

The `n8n-event-ingest` function checks the `payload.idempotency_key` field before inserting. If a matching event already exists, it returns `{ success: true, deduplicated: true }` without creating a duplicate.

This prevents duplicate follow-ups if n8n retries a failed execution.

## n8n Environment Variables

Set these in n8n Settings → Variables:

| Variable | Value |
|----------|-------|
| `SUPABASE_URL` | Your Supabase project URL |
| `N8N_EVENT_INGEST_SECRET` | Shared secret matching the Edge Function |

## Setup Steps

1. Import or recreate the workflow in n8n using the node sequence above
2. Configure SMTP credentials (or use a SendGrid/Resend node)
3. Set environment variables in n8n
4. Activate the workflow
5. Copy the webhook URL and set it as `N8N_WEBHOOK_URL` in your Supabase Edge Function environment
6. (Optional) Connect Slack OAuth for the Slack notification node
