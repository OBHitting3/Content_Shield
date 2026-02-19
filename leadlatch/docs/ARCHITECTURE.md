# A) Architecture Overview — LeadLatch MVP

## System Diagram

```
                        ┌─────────────────────┐
                        │   External Forms     │
                        │ (Website, Typeform,  │
                        │  Unbounce, etc.)     │
                        └─────────┬───────────┘
                                  │ POST JSON
                                  ▼
                   ┌──────────────────────────────┐
                   │  Supabase Edge Function       │
                   │  /functions/v1/lead-intake     │
                   │  (public, no JWT required)     │
                   │                                │
                   │  1. Validate org_id + name     │
                   │  2. INSERT lead                │
                   │  3. INSERT lead_event(created) │
                   │  4. Fire n8n webhook (async)   │
                   │  5. Return { lead_id }         │
                   └──────┬───────────┬────────────┘
                          │           │
                          │           │ POST webhook
                          ▼           ▼
           ┌──────────────────┐  ┌─────────────────────┐
           │  Supabase DB     │  │  n8n Workflow        │
           │  (Postgres)      │  │  (self-hosted or     │
           │                  │  │   n8n Cloud)         │
           │  • organizations │  │                      │
           │  • memberships   │  │  1. Welcome email    │
           │  • profiles      │  │  2. Slack notify     │
           │  • leads         │  │  3. Follow-up #1     │
           │  • lead_events   │  │  4. Follow-up #2     │
           │  • automation_   │  │  5. Log each action  │
           │    rules         │  │     back to Supabase │
           └────────▲─────────┘  └──────┬──────────────┘
                    │                    │
                    │  POST events       │
                    │                    ▼
                    │   ┌─────────────────────────────┐
                    │   │  Supabase Edge Function      │
                    │   │  /functions/v1/n8n-event-    │
                    │   │  ingest                      │
                    │   │  (secured via shared secret) │
                    │   │                              │
                    │   │  1. Validate secret header   │
                    │   │  2. Idempotency check        │
                    │   │  3. INSERT lead_event        │
                    │   │  4. (Optional) UPDATE lead   │
                    │   │     status                   │
                    └───┴──────────────────────────────┘
                    ▲
                    │ Supabase JS Client (anon key + RLS)
                    │
           ┌────────┴────────────────┐
           │  Next.js Web App        │
           │  (App Router)           │
           │                         │
           │  • /login               │
           │  • /dashboard           │
           │  • /dashboard/leads     │
           │  • /dashboard/leads/:id │
           │  • /dashboard/settings  │
           │                         │
           │  Auth: Supabase Auth    │
           │  (magic link + password)│
           └─────────────────────────┘
```

## Components

| Component | Technology | Purpose |
|-----------|-----------|---------|
| Web App | Next.js 15 (App Router) + TypeScript | Dashboard for viewing/managing leads |
| Database | Supabase (Postgres) | Multi-tenant data store with RLS |
| Auth | Supabase Auth | Email magic link + password |
| Lead Intake | Supabase Edge Function (Deno) | Public API for form submissions |
| Event Ingest | Supabase Edge Function (Deno) | Secured callback for n8n |
| Automation | n8n | Email follow-ups, Slack, event logging |

## Data Flow

### Lead Creation Flow
1. External form POSTs to `/functions/v1/lead-intake` with `org_id`, `name`, and optional fields
2. Edge Function validates, inserts lead + "created" event using service role key
3. Edge Function fires n8n webhook asynchronously (non-blocking)
4. Returns `{ success: true, lead_id: "..." }` to the form

### Automation Flow
1. n8n webhook receives lead payload
2. Generates idempotency keys from `lead_id`
3. Sends welcome email (if lead has email)
4. Posts to Slack (parallel)
5. Writes each action back to Supabase via `n8n-event-ingest`
6. Waits 24h, sends follow-up #1, logs event
7. Waits 72h, sends follow-up #2, logs event

### Dashboard Flow
1. User authenticates via Supabase Auth (magic link or password)
2. Middleware validates session, redirects unauthenticated users
3. Dashboard loads memberships to populate org switcher
4. All queries filter by `org_id` — RLS enforces tenant isolation
5. Users can view leads, change status, add notes (all recorded as events)

## Security Model

| Layer | Mechanism |
|-------|-----------|
| Multi-tenancy | RLS policies on every table — `org_id IN (user_org_ids())` |
| Public API | Edge Function uses service role key (bypasses RLS) |
| Event Ingest | Shared secret in `x-leadlatch-secret` header |
| Web App | Supabase anon key + user session (RLS enforced) |
| Roles | owner > admin > member — enforced in RLS `WITH CHECK` clauses |
