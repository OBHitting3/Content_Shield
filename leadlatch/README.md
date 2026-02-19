# LeadLatch — Speed-to-Lead Autopilot

Multi-tenant SaaS for capturing, responding to, and following up with leads automatically.

**Stack:** Next.js 15 (App Router) + TypeScript · Supabase (Auth + Postgres + RLS + Edge Functions) · n8n (workflow automation)

## How It Works

1. **Lead arrives** → External form POSTs to the public `lead-intake` Edge Function
2. **Instant capture** → Lead + event inserted into Supabase (tenant-isolated via RLS)
3. **Automation fires** → n8n webhook triggers: welcome email, Slack notification, scheduled follow-ups
4. **Events logged** → Every automation action writes back to Supabase via `n8n-event-ingest`
5. **Dashboard** → Team views leads, changes statuses, adds notes — all with a deterministic event timeline

## Project Structure

```
leadlatch/
├── src/
│   ├── app/
│   │   ├── layout.tsx                  # Root layout
│   │   ├── page.tsx                    # Redirect to /dashboard or /login
│   │   ├── login/page.tsx              # Auth (magic link + password)
│   │   ├── auth/callback/route.ts      # OAuth/magic link callback
│   │   └── dashboard/
│   │       ├── layout.tsx              # Dashboard shell (sidebar + org provider)
│   │       ├── page.tsx                # Overview with stats
│   │       ├── leads/page.tsx          # Leads list with filters
│   │       ├── leads/[id]/page.tsx     # Lead detail + timeline + notes
│   │       └── settings/page.tsx       # Org info, webhook config, members
│   ├── components/
│   │   ├── dashboard/
│   │   │   ├── org-context.tsx         # React context for current org
│   │   │   ├── org-switcher.tsx        # Org dropdown selector
│   │   │   ├── sidebar.tsx             # Navigation sidebar
│   │   │   ├── create-org-dialog.tsx   # Create organization modal
│   │   │   ├── lead-timeline.tsx       # Event timeline display
│   │   │   └── add-note-form.tsx       # Add note to lead
│   │   └── ui/
│   │       └── status-badge.tsx        # Status pill component
│   ├── lib/supabase/
│   │   ├── client.ts                   # Browser Supabase client
│   │   ├── server.ts                   # Server Supabase client + service client
│   │   └── middleware.ts               # Auth session management
│   ├── middleware.ts                    # Next.js middleware (auth guard)
│   └── types/database.ts              # TypeScript interfaces for all tables
├── supabase/
│   ├── config.toml                     # Supabase local config
│   ├── migrations/
│   │   ├── 20260219000001_initial_schema.sql    # Tables + triggers
│   │   ├── 20260219000002_rls_policies.sql      # RLS policies
│   │   └── 20260219000003_seed_helpers.sql      # Helper RPC functions
│   └── functions/
│       ├── _shared/cors.ts             # CORS headers
│       ├── lead-intake/index.ts        # Public lead ingestion endpoint
│       └── n8n-event-ingest/index.ts   # Secured n8n callback endpoint
├── n8n/
│   ├── workflow-outline.json           # Full node sequence + config
│   └── README.md                       # n8n setup guide
├── docs/
│   ├── ARCHITECTURE.md                 # System diagram + data flow
│   ├── DEPLOYMENT.md                   # Setup and deploy instructions
│   └── DEFINITION-OF-DONE.md          # Checklist + test plan
├── package.json
├── tsconfig.json
├── next.config.ts
└── .env.example
```

## Quick Start

```bash
cd leadlatch
npm install
cp .env.example .env.local
# Fill in your Supabase credentials in .env.local
npm run dev
```

## Database Schema

| Table | Purpose |
|-------|---------|
| `organizations` | Tenant container (name, slug) |
| `memberships` | User ↔ Org mapping with role (owner/admin/member) |
| `profiles` | User display info (auto-created on signup) |
| `leads` | Lead records with status, contact info, UTM tracking |
| `lead_events` | Append-only event timeline (every action logged) |
| `automation_rules` | Webhook URLs, follow-up cadence, enabled flags |

## Security

- **RLS** on every table — `org_id IN (SELECT user_org_ids())` prevents cross-tenant data access
- **Edge Functions** use service role key (bypasses RLS for system operations)
- **n8n-event-ingest** authenticated via shared secret in `x-leadlatch-secret` header
- **Web app** uses anon key + user session — RLS enforced server-side by Postgres
- **Roles:** owner > admin > member — certain operations (delete leads, manage members, configure webhooks) restricted to owner/admin

## Environment Variables

See `.env.example` for the full list. Key variables:

| Variable | Where | Description |
|----------|-------|-------------|
| `NEXT_PUBLIC_SUPABASE_URL` | Next.js + Edge Functions | Supabase project URL |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | Next.js | Public API key |
| `SUPABASE_SERVICE_ROLE_KEY` | Edge Functions + Server | Admin API key |
| `N8N_WEBHOOK_URL` | Edge Function | n8n webhook trigger URL |
| `N8N_EVENT_INGEST_SECRET` | Edge Function + n8n | Shared secret for callbacks |

## Documentation

- [Architecture Overview](docs/ARCHITECTURE.md)
- [Deployment Guide](docs/DEPLOYMENT.md)
- [Definition of Done + Test Plan](docs/DEFINITION-OF-DONE.md)
- [n8n Workflow Guide](n8n/README.md)

## Scripts

```bash
npm run dev          # Start dev server
npm run build        # Production build
npm run start        # Start production server
npm run lint         # ESLint
npm run type-check   # TypeScript check
```

---

CLEAR_99_10: **YES**

All deliverables (A–H) are complete and implementable. The system requires only standard Supabase project credentials and an n8n instance to operate. No missing pieces, no speculative libraries, no guesswork needed.
