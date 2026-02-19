-- LeadLatch RLS Policies
-- Every table is locked down so orgs can only access their own data.

-- ============================================================
-- Enable RLS on all tables
-- ============================================================
alter table public.organizations    enable row level security;
alter table public.memberships      enable row level security;
alter table public.profiles         enable row level security;
alter table public.leads            enable row level security;
alter table public.lead_events      enable row level security;
alter table public.automation_rules enable row level security;

-- ============================================================
-- Helper: returns org IDs the current user belongs to
-- ============================================================
create or replace function public.user_org_ids()
returns setof uuid as $$
  select org_id from public.memberships where user_id = auth.uid();
$$ language sql security definer stable;

-- ============================================================
-- ORGANIZATIONS
-- Users can see orgs they belong to.
-- Owners can update their org.
-- ============================================================
create policy "Members can view their orgs"
  on public.organizations for select
  using (id in (select public.user_org_ids()));

create policy "Owners can update their org"
  on public.organizations for update
  using (id in (
    select org_id from public.memberships
    where user_id = auth.uid() and role = 'owner'
  ));

-- ============================================================
-- MEMBERSHIPS
-- Users can see memberships in their orgs.
-- Owners/admins can insert/delete memberships.
-- ============================================================
create policy "Members can view memberships in their orgs"
  on public.memberships for select
  using (org_id in (select public.user_org_ids()));

create policy "Owners and admins can add members"
  on public.memberships for insert
  with check (org_id in (
    select org_id from public.memberships
    where user_id = auth.uid() and role in ('owner', 'admin')
  ));

create policy "Owners and admins can remove members"
  on public.memberships for delete
  using (org_id in (
    select org_id from public.memberships
    where user_id = auth.uid() and role in ('owner', 'admin')
  ));

-- ============================================================
-- PROFILES
-- Users can read any profile (for displaying names in UI).
-- Users can only update their own profile.
-- ============================================================
create policy "Anyone authenticated can view profiles"
  on public.profiles for select
  using (auth.role() = 'authenticated');

create policy "Users can update own profile"
  on public.profiles for update
  using (id = auth.uid());

-- ============================================================
-- LEADS
-- Users can CRUD leads in their orgs.
-- ============================================================
create policy "Members can view leads in their orgs"
  on public.leads for select
  using (org_id in (select public.user_org_ids()));

create policy "Members can insert leads in their orgs"
  on public.leads for insert
  with check (org_id in (select public.user_org_ids()));

create policy "Members can update leads in their orgs"
  on public.leads for update
  using (org_id in (select public.user_org_ids()));

create policy "Owners and admins can delete leads"
  on public.leads for delete
  using (org_id in (
    select org_id from public.memberships
    where user_id = auth.uid() and role in ('owner', 'admin')
  ));

-- ============================================================
-- LEAD EVENTS
-- Users can view events in their orgs.
-- Users can insert events (notes) in their orgs.
-- Events are append-only: no update/delete from client.
-- ============================================================
create policy "Members can view events in their orgs"
  on public.lead_events for select
  using (org_id in (select public.user_org_ids()));

create policy "Members can insert events in their orgs"
  on public.lead_events for insert
  with check (org_id in (select public.user_org_ids()));

-- ============================================================
-- AUTOMATION RULES
-- Members can view rules. Owners/admins can manage them.
-- ============================================================
create policy "Members can view automation rules"
  on public.automation_rules for select
  using (org_id in (select public.user_org_ids()));

create policy "Owners and admins can manage automation rules"
  on public.automation_rules for insert
  with check (org_id in (
    select org_id from public.memberships
    where user_id = auth.uid() and role in ('owner', 'admin')
  ));

create policy "Owners and admins can update automation rules"
  on public.automation_rules for update
  using (org_id in (
    select org_id from public.memberships
    where user_id = auth.uid() and role in ('owner', 'admin')
  ));

create policy "Owners and admins can delete automation rules"
  on public.automation_rules for delete
  using (org_id in (
    select org_id from public.memberships
    where user_id = auth.uid() and role in ('owner', 'admin')
  ));
