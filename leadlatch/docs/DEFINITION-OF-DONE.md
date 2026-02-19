# H) Definition of Done — LeadLatch MVP

## Checklist

### Database & Security
- [x] Schema: `organizations`, `memberships`, `profiles`, `leads`, `lead_events`, `automation_rules` tables created
- [x] RLS enabled on all tables
- [x] RLS policies: users can only access data in orgs they belong to
- [x] `user_org_ids()` helper function for RLS
- [x] `create_org_with_owner()` RPC for org creation
- [x] `updated_at` auto-triggers on all mutable tables
- [x] Profile auto-creation trigger on `auth.users` insert
- [x] Indexes on frequently queried columns (org_id, status, email, lead_id)

### Edge Functions
- [x] `lead-intake`: accepts POST, validates org_id + name, inserts lead + event, fires n8n webhook
- [x] `lead-intake`: returns `{ success, lead_id, status }` with CORS headers
- [x] `n8n-event-ingest`: authenticates via `x-leadlatch-secret` header
- [x] `n8n-event-ingest`: idempotency check on `payload.idempotency_key`
- [x] `n8n-event-ingest`: inserts lead_event, optionally updates lead status
- [x] Both functions handle errors gracefully with appropriate HTTP status codes

### Authentication
- [x] Magic link login (email OTP)
- [x] Password login with auto-signup fallback
- [x] Auth callback route for magic link redirect
- [x] Middleware protects `/dashboard/*` routes
- [x] Middleware redirects authenticated users away from `/login`
- [x] Sign-out button in sidebar

### Dashboard — Core
- [x] Org switcher (select dropdown) in sidebar
- [x] Create Organization dialog (calls `create_org_with_owner` RPC)
- [x] Navigation: Overview, Leads, Settings
- [x] Overview page with status counts (total, new, working, won, lost)

### Dashboard — Leads
- [x] Leads list with search (name, email, phone) and status filter
- [x] Status badges (new=blue, working=yellow, won=green, lost=red)
- [x] Click-through to lead detail
- [x] Lead detail: contact info, message, UTM data
- [x] Status change dropdown (inserts `status_changed` event)
- [x] Timeline of all lead_events (color-coded by source)
- [x] Add Note form (inserts `note_added` event)

### Dashboard — Settings
- [x] Organization info (name, slug, ID)
- [x] Lead intake endpoint display
- [x] n8n webhook URL configuration (owner/admin only)
- [x] Members list with roles

### Automation (n8n)
- [x] Webhook trigger payload shape documented
- [x] Node sequence: welcome email → follow-ups → Slack → event logging
- [x] Idempotency strategy: deterministic keys prevent duplicate actions
- [x] Event-ingest callback shape documented
- [x] Environment variables documented

### Code Quality
- [x] TypeScript strict mode — no `any` types in app code
- [x] Next.js build passes with zero errors
- [x] ESLint configuration (next/core-web-vitals)
- [x] Clean project structure (components, lib, types separated)
- [x] No speculative dependencies — only next, react, @supabase/ssr, @supabase/supabase-js

### Documentation
- [x] Architecture overview (components + data flow diagram)
- [x] Database schema SQL (3 migration files)
- [x] RLS policies documented
- [x] Edge Function code (2 functions)
- [x] n8n workflow outline with node sequence
- [x] Deployment steps (Supabase, n8n, Vercel)
- [x] Environment variables list
- [x] This Definition of Done checklist
- [x] Test plan

## Test Plan

### Integration Tests (Automated)

These tests can be run against a Supabase project (local or remote):

| # | Test | Expected Result |
|---|------|-----------------|
| 1 | POST to `lead-intake` with valid org_id + name | 200, returns `lead_id` |
| 2 | POST to `lead-intake` without org_id | 400, error message |
| 3 | POST to `lead-intake` with invalid org_id | 404, "Organization not found" |
| 4 | POST to `n8n-event-ingest` without secret header | 401, "Unauthorized" |
| 5 | POST to `n8n-event-ingest` with valid secret + event data | 200, returns `event_id` |
| 6 | POST to `n8n-event-ingest` with duplicate idempotency_key | 200, `deduplicated: true` |
| 7 | POST to `n8n-event-ingest` with `new_status` | Lead status updated + status_changed event created |
| 8 | Query leads as user in org A | Returns only org A leads |
| 9 | Query leads as user NOT in org A | Returns empty (RLS blocks) |
| 10 | Insert lead_event for org the user belongs to | Succeeds |
| 11 | Insert lead_event for org the user does NOT belong to | Fails (RLS blocks) |

### Manual Test Steps

| # | Step | Expected |
|---|------|----------|
| 1 | Navigate to `/login` | Login page renders with magic link + password tabs |
| 2 | Sign up with email + password | "Check email" message (or direct sign-in if email confirm is off) |
| 3 | Sign in with password | Redirected to `/dashboard` |
| 4 | No orgs exist → see "Create Organization" | Dialog appears, create org |
| 5 | Org switcher shows the new org | Selected by default |
| 6 | Navigate to "Leads" tab | Empty state: "No leads found." |
| 7 | `curl` the lead-intake endpoint with the org ID | Returns 200 + lead_id |
| 8 | Refresh leads page | New lead appears with status "new" |
| 9 | Click lead name → detail page | Contact info + timeline with "created" event |
| 10 | Change status to "working" | Status badge updates, new event in timeline |
| 11 | Add a note | Note appears in timeline with source "app" |
| 12 | Navigate to Settings | Org info, endpoint URL, members list visible |
| 13 | Set n8n webhook URL and save | Saves to automation_rules |
| 14 | Sign out | Redirected to `/login` |
| 15 | Try to access `/dashboard` directly | Redirected to `/login` |

### RLS Verification (SQL)

```sql
-- As user in org_a, should see only org_a leads:
select * from leads; -- returns only org_a data

-- As user in org_a, should NOT see org_b events:
select * from lead_events where org_id = 'org_b_id'; -- returns 0 rows

-- Service role can see everything (used by Edge Functions):
-- Run with service role key: select * from leads; -- returns all
```
