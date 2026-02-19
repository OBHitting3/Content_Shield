-- LeadLatch MVP Schema
-- Multi-tenant speed-to-lead system

-- Enable UUID generation
create extension if not exists "pgcrypto";

-- ============================================================
-- ORGANIZATIONS
-- ============================================================
create table public.organizations (
  id          uuid primary key default gen_random_uuid(),
  name        text not null,
  slug        text not null unique,
  created_at  timestamptz not null default now(),
  updated_at  timestamptz not null default now()
);

create index idx_organizations_slug on public.organizations (slug);

-- ============================================================
-- MEMBERSHIPS  (user <-> org, with role)
-- ============================================================
create type public.membership_role as enum ('owner', 'admin', 'member');

create table public.memberships (
  id          uuid primary key default gen_random_uuid(),
  user_id     uuid not null references auth.users (id) on delete cascade,
  org_id      uuid not null references public.organizations (id) on delete cascade,
  role        public.membership_role not null default 'member',
  created_at  timestamptz not null default now(),
  unique (user_id, org_id)
);

create index idx_memberships_user on public.memberships (user_id);
create index idx_memberships_org  on public.memberships (org_id);

-- ============================================================
-- PROFILES  (public-facing user data, synced from auth.users)
-- ============================================================
create table public.profiles (
  id          uuid primary key references auth.users (id) on delete cascade,
  email       text not null,
  full_name   text,
  avatar_url  text,
  created_at  timestamptz not null default now(),
  updated_at  timestamptz not null default now()
);

-- Auto-create profile on signup
create or replace function public.handle_new_user()
returns trigger as $$
begin
  insert into public.profiles (id, email, full_name)
  values (
    new.id,
    new.email,
    coalesce(new.raw_user_meta_data ->> 'full_name', '')
  );
  return new;
end;
$$ language plpgsql security definer;

create trigger on_auth_user_created
  after insert on auth.users
  for each row execute function public.handle_new_user();

-- ============================================================
-- LEADS
-- ============================================================
create type public.lead_status as enum ('new', 'working', 'won', 'lost');

create table public.leads (
  id          uuid primary key default gen_random_uuid(),
  org_id      uuid not null references public.organizations (id) on delete cascade,
  status      public.lead_status not null default 'new',
  name        text not null,
  email       text,
  phone       text,
  message     text,
  source_url  text,
  utm_source  text,
  utm_medium  text,
  utm_campaign text,
  utm_term    text,
  utm_content text,
  assigned_to uuid references auth.users (id) on delete set null,
  created_at  timestamptz not null default now(),
  updated_at  timestamptz not null default now()
);

create index idx_leads_org    on public.leads (org_id);
create index idx_leads_status on public.leads (org_id, status);
create index idx_leads_email  on public.leads (org_id, email);

-- ============================================================
-- LEAD EVENTS  (deterministic timeline)
-- ============================================================
create type public.lead_event_type as enum (
  'created',
  'status_changed',
  'email_sent',
  'email_opened',
  'email_replied',
  'sms_sent',
  'slack_posted',
  'note_added',
  'assigned',
  'followup_scheduled',
  'followup_sent',
  'webhook_fired',
  'custom'
);

create type public.event_source as enum ('app', 'n8n', 'system', 'edge_function');

create table public.lead_events (
  id          uuid primary key default gen_random_uuid(),
  lead_id     uuid not null references public.leads (id) on delete cascade,
  org_id      uuid not null references public.organizations (id) on delete cascade,
  event_type  public.lead_event_type not null,
  source      public.event_source not null default 'app',
  payload     jsonb not null default '{}',
  created_by  uuid references auth.users (id) on delete set null,
  created_at  timestamptz not null default now()
);

create index idx_lead_events_lead on public.lead_events (lead_id, created_at desc);
create index idx_lead_events_org  on public.lead_events (org_id);

-- ============================================================
-- AUTOMATION RULES
-- ============================================================
create table public.automation_rules (
  id              uuid primary key default gen_random_uuid(),
  org_id          uuid not null references public.organizations (id) on delete cascade,
  name            text not null,
  enabled         boolean not null default true,
  webhook_url     text,
  trigger_on      text not null default 'lead_created',
  followup_cadence jsonb not null default '[]',
  config          jsonb not null default '{}',
  created_at      timestamptz not null default now(),
  updated_at      timestamptz not null default now()
);

create index idx_automation_rules_org on public.automation_rules (org_id);

-- ============================================================
-- UPDATED_AT TRIGGER FUNCTION
-- ============================================================
create or replace function public.set_updated_at()
returns trigger as $$
begin
  new.updated_at = now();
  return new;
end;
$$ language plpgsql;

create trigger trg_organizations_updated_at
  before update on public.organizations
  for each row execute function public.set_updated_at();

create trigger trg_profiles_updated_at
  before update on public.profiles
  for each row execute function public.set_updated_at();

create trigger trg_leads_updated_at
  before update on public.leads
  for each row execute function public.set_updated_at();

create trigger trg_automation_rules_updated_at
  before update on public.automation_rules
  for each row execute function public.set_updated_at();
