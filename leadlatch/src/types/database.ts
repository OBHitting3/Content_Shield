export type MembershipRole = "owner" | "admin" | "member";
export type LeadStatus = "new" | "working" | "won" | "lost";
export type LeadEventType =
  | "created"
  | "status_changed"
  | "email_sent"
  | "email_opened"
  | "email_replied"
  | "sms_sent"
  | "slack_posted"
  | "note_added"
  | "assigned"
  | "followup_scheduled"
  | "followup_sent"
  | "webhook_fired"
  | "custom";
export type EventSource = "app" | "n8n" | "system" | "edge_function";

export interface Organization {
  id: string;
  name: string;
  slug: string;
  created_at: string;
  updated_at: string;
}

export interface Membership {
  id: string;
  user_id: string;
  org_id: string;
  role: MembershipRole;
  created_at: string;
}

export interface Profile {
  id: string;
  email: string;
  full_name: string | null;
  avatar_url: string | null;
  created_at: string;
  updated_at: string;
}

export interface Lead {
  id: string;
  org_id: string;
  status: LeadStatus;
  name: string;
  email: string | null;
  phone: string | null;
  message: string | null;
  source_url: string | null;
  utm_source: string | null;
  utm_medium: string | null;
  utm_campaign: string | null;
  utm_term: string | null;
  utm_content: string | null;
  assigned_to: string | null;
  created_at: string;
  updated_at: string;
}

export interface LeadEvent {
  id: string;
  lead_id: string;
  org_id: string;
  event_type: LeadEventType;
  source: EventSource;
  payload: Record<string, unknown>;
  created_by: string | null;
  created_at: string;
}

export interface AutomationRule {
  id: string;
  org_id: string;
  name: string;
  enabled: boolean;
  webhook_url: string | null;
  trigger_on: string;
  followup_cadence: FollowupStep[];
  config: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface FollowupStep {
  delay_minutes: number;
  action: "email" | "sms" | "slack";
  template: string;
}

export interface MembershipWithOrg extends Membership {
  organizations: Organization;
}
