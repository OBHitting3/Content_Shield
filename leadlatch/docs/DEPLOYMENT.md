# G) Deployment Steps

## 1. Supabase Project Setup

1. Create a new project at [supabase.com](https://supabase.com)
2. Go to **Settings → API** and copy:
   - Project URL (`NEXT_PUBLIC_SUPABASE_URL`)
   - Anon Key (`NEXT_PUBLIC_SUPABASE_ANON_KEY`)
   - Service Role Key (`SUPABASE_SERVICE_ROLE_KEY`)
3. Go to **SQL Editor** and run the migrations in order:
   ```
   supabase/migrations/20260219000001_initial_schema.sql
   supabase/migrations/20260219000002_rls_policies.sql
   supabase/migrations/20260219000003_seed_helpers.sql
   ```
4. Go to **Authentication → Settings**:
   - Enable "Email" provider
   - Set "Site URL" to your app URL (e.g., `http://localhost:3000` for dev)
   - Add `http://localhost:3000/auth/callback` to "Redirect URLs"

## 2. Deploy Supabase Edge Functions

```bash
# Install Supabase CLI
npm install -g supabase

# Link to your project
supabase link --project-ref your-project-ref

# Set secrets for Edge Functions
supabase secrets set N8N_WEBHOOK_URL=https://your-n8n.example.com/webhook/lead-created
supabase secrets set N8N_EVENT_INGEST_SECRET=your-shared-secret-here

# Deploy functions
supabase functions deploy lead-intake --no-verify-jwt
supabase functions deploy n8n-event-ingest --no-verify-jwt
```

## 3. n8n Setup

1. Set up n8n (self-hosted or cloud) — see [n8n docs](https://docs.n8n.io/)
2. Create the workflow following `n8n/workflow-outline.json`
3. Set n8n environment variables:
   - `SUPABASE_URL` = your project URL
   - `N8N_EVENT_INGEST_SECRET` = same secret as Edge Function
4. Configure SMTP or email service credentials
5. Activate the workflow and copy the webhook URL

## 4. Environment Variables

### Next.js App (`.env.local`)

| Variable | Required | Description |
|----------|----------|-------------|
| `NEXT_PUBLIC_SUPABASE_URL` | Yes | Supabase project URL |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | Yes | Supabase anon (public) key |
| `SUPABASE_SERVICE_ROLE_KEY` | Yes | Supabase service role key (server-only) |
| `N8N_WEBHOOK_URL` | No | n8n webhook URL for lead-created trigger |
| `N8N_EVENT_INGEST_SECRET` | Yes | Shared secret for n8n → Supabase callbacks |
| `NEXT_PUBLIC_APP_URL` | Yes | App base URL (for auth redirects) |

### Supabase Edge Function Secrets

| Secret | Description |
|--------|-------------|
| `N8N_WEBHOOK_URL` | n8n webhook trigger URL |
| `N8N_EVENT_INGEST_SECRET` | Shared secret for authenticating n8n callbacks |

### n8n Environment Variables

| Variable | Description |
|----------|-------------|
| `SUPABASE_URL` | Supabase project URL |
| `N8N_EVENT_INGEST_SECRET` | Shared secret matching Edge Function |

## 5. Local Development

```bash
# Clone and install
cd leadlatch
npm install

# Copy env file and fill in values
cp .env.example .env.local
# Edit .env.local with your Supabase credentials

# Run development server
npm run dev

# Build for production
npm run build

# Type check
npm run type-check
```

## 6. Production Deployment (Vercel)

1. Push code to GitHub
2. Import project in [Vercel](https://vercel.com)
3. Set environment variables in Vercel dashboard
4. Set root directory to `leadlatch` (if in a monorepo)
5. Deploy

## 7. Testing the Lead Intake

```bash
# Replace with your actual Supabase URL and org_id
curl -X POST https://your-project.supabase.co/functions/v1/lead-intake \
  -H "Content-Type: application/json" \
  -d '{
    "org_id": "your-org-uuid",
    "name": "Test Lead",
    "email": "test@example.com",
    "phone": "+1-555-000-0000",
    "message": "Testing the intake",
    "source_url": "https://example.com",
    "utm_source": "manual_test"
  }'
```

Expected response:
```json
{
  "success": true,
  "lead_id": "generated-uuid",
  "status": "new"
}
```
