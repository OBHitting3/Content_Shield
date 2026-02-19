-- Helper function: create org + make calling user the owner.
-- Used by the app when a user creates a new organization.
create or replace function public.create_org_with_owner(
  org_name text,
  org_slug text
)
returns uuid as $$
declare
  new_org_id uuid;
begin
  insert into public.organizations (name, slug)
  values (org_name, org_slug)
  returning id into new_org_id;

  insert into public.memberships (user_id, org_id, role)
  values (auth.uid(), new_org_id, 'owner');

  return new_org_id;
end;
$$ language plpgsql security definer;
