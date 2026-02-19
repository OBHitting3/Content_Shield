"use client";

import { useOrg } from "@/components/dashboard/org-context";
import { useEffect, useState, useCallback } from "react";
import { createClient } from "@/lib/supabase/client";
import type { AutomationRule, Membership, Profile } from "@/types/database";

export default function SettingsPage() {
  const { currentOrg, currentRole } = useOrg();
  const [rules, setRules] = useState<AutomationRule[]>([]);
  const [members, setMembers] = useState<(Membership & { profiles: Profile })[]>([]);
  const [webhookUrl, setWebhookUrl] = useState("");
  const [saving, setSaving] = useState(false);
  const supabase = createClient();

  const load = useCallback(async () => {
    if (!currentOrg) return;

    const [rulesRes, membersRes] = await Promise.all([
      supabase
        .from("automation_rules")
        .select("*")
        .eq("org_id", currentOrg.org_id),
      supabase
        .from("memberships")
        .select("*, profiles(*)")
        .eq("org_id", currentOrg.org_id),
    ]);

    if (rulesRes.data) {
      setRules(rulesRes.data as AutomationRule[]);
      if (rulesRes.data.length > 0) {
        setWebhookUrl(rulesRes.data[0].webhook_url || "");
      }
    }
    if (membersRes.data) {
      setMembers(membersRes.data as (Membership & { profiles: Profile })[]);
    }
  }, [currentOrg, supabase]);

  useEffect(() => {
    load();
  }, [load]);

  async function saveWebhook(e: React.FormEvent) {
    e.preventDefault();
    if (!currentOrg) return;
    setSaving(true);

    if (rules.length > 0) {
      await supabase
        .from("automation_rules")
        .update({ webhook_url: webhookUrl })
        .eq("id", rules[0].id);
    } else {
      await supabase.from("automation_rules").insert({
        org_id: currentOrg.org_id,
        name: "Default n8n Webhook",
        webhook_url: webhookUrl,
        trigger_on: "lead_created",
        followup_cadence: [
          { delay_minutes: 0, action: "email", template: "welcome" },
          { delay_minutes: 1440, action: "email", template: "followup_1" },
          { delay_minutes: 4320, action: "email", template: "followup_2" },
        ],
      });
    }

    setSaving(false);
    load();
  }

  if (!currentOrg) {
    return <p style={{ color: "var(--text-muted)" }}>Select an organization.</p>;
  }

  const isAdmin = currentRole === "owner" || currentRole === "admin";

  return (
    <div>
      <h1 style={{ fontSize: "1.5rem", marginBottom: "1.5rem" }}>Settings</h1>

      <div style={{ display: "grid", gap: "1.5rem", maxWidth: 640 }}>
        {/* Organization Info */}
        <div className="card">
          <h3 style={{ marginBottom: "0.75rem" }}>Organization</h3>
          <p>
            <strong>Name:</strong> {currentOrg.organizations.name}
          </p>
          <p>
            <strong>Slug:</strong> {currentOrg.organizations.slug}
          </p>
          <p>
            <strong>ID:</strong>{" "}
            <code style={{ fontSize: "0.8rem" }}>{currentOrg.org_id}</code>
          </p>
          <p style={{ marginTop: "0.75rem", fontSize: "0.85rem", color: "var(--text-muted)" }}>
            Use the Org ID in your lead intake form to route leads here.
          </p>
        </div>

        {/* Lead Intake Endpoint */}
        <div className="card">
          <h3 style={{ marginBottom: "0.75rem" }}>Lead Intake Endpoint</h3>
          <p style={{ fontSize: "0.85rem", marginBottom: "0.5rem" }}>
            POST form data to this endpoint to create leads:
          </p>
          <code
            style={{
              display: "block",
              background: "var(--bg-secondary)",
              padding: "0.5rem",
              borderRadius: "var(--radius)",
              fontSize: "0.8rem",
              wordBreak: "break-all",
            }}
          >
            {process.env.NEXT_PUBLIC_SUPABASE_URL}/functions/v1/lead-intake
          </code>
          <p
            style={{
              fontSize: "0.8rem",
              color: "var(--text-muted)",
              marginTop: "0.5rem",
            }}
          >
            Include <code>org_id</code> and <code>name</code> in the JSON body.
          </p>
        </div>

        {/* Automation / Webhook */}
        {isAdmin && (
          <div className="card">
            <h3 style={{ marginBottom: "0.75rem" }}>n8n Webhook</h3>
            <form onSubmit={saveWebhook}>
              <label
                style={{
                  display: "block",
                  fontSize: "0.8rem",
                  fontWeight: 600,
                  marginBottom: "0.25rem",
                }}
              >
                Webhook URL (called on new lead)
              </label>
              <input
                className="input"
                placeholder="https://your-n8n.example.com/webhook/..."
                value={webhookUrl}
                onChange={(e) => setWebhookUrl(e.target.value)}
                style={{ marginBottom: "0.5rem" }}
              />
              <button type="submit" className="btn btn-primary btn-sm" disabled={saving}>
                {saving ? "Saving..." : "Save"}
              </button>
            </form>
          </div>
        )}

        {/* Members */}
        <div className="card">
          <h3 style={{ marginBottom: "0.75rem" }}>
            Members ({members.length})
          </h3>
          {members.length === 0 ? (
            <p style={{ color: "var(--text-muted)", fontSize: "0.85rem" }}>
              No members found.
            </p>
          ) : (
            <table>
              <thead>
                <tr>
                  <th>Email</th>
                  <th>Name</th>
                  <th>Role</th>
                </tr>
              </thead>
              <tbody>
                {members.map((m) => (
                  <tr key={m.id}>
                    <td style={{ fontSize: "0.85rem" }}>
                      {m.profiles?.email || "—"}
                    </td>
                    <td style={{ fontSize: "0.85rem" }}>
                      {m.profiles?.full_name || "—"}
                    </td>
                    <td>
                      <span
                        className="badge"
                        style={{
                          background:
                            m.role === "owner"
                              ? "#dbeafe"
                              : m.role === "admin"
                                ? "#fef3c7"
                                : "#e9ecef",
                          color:
                            m.role === "owner"
                              ? "#1d4ed8"
                              : m.role === "admin"
                                ? "#92400e"
                                : "#495057",
                        }}
                      >
                        {m.role}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  );
}
