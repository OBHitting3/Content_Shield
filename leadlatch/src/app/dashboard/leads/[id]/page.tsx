"use client";

import { useEffect, useState, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import { createClient } from "@/lib/supabase/client";
import { useOrg } from "@/components/dashboard/org-context";
import { StatusBadge } from "@/components/ui/status-badge";
import { LeadTimeline } from "@/components/dashboard/lead-timeline";
import { AddNoteForm } from "@/components/dashboard/add-note-form";
import type { Lead, LeadEvent, LeadStatus } from "@/types/database";

const STATUSES: LeadStatus[] = ["new", "working", "won", "lost"];

export default function LeadDetailPage() {
  const params = useParams();
  const router = useRouter();
  const { currentOrg, userId } = useOrg();
  const [lead, setLead] = useState<Lead | null>(null);
  const [events, setEvents] = useState<LeadEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const supabase = createClient();
  const leadId = params.id as string;

  const loadLead = useCallback(async () => {
    if (!currentOrg) return;

    const [leadRes, eventsRes] = await Promise.all([
      supabase
        .from("leads")
        .select("*")
        .eq("id", leadId)
        .eq("org_id", currentOrg.org_id)
        .single(),
      supabase
        .from("lead_events")
        .select("*")
        .eq("lead_id", leadId)
        .eq("org_id", currentOrg.org_id)
        .order("created_at", { ascending: false }),
    ]);

    if (leadRes.data) setLead(leadRes.data as Lead);
    if (eventsRes.data) setEvents(eventsRes.data as LeadEvent[]);
    setLoading(false);
  }, [currentOrg, leadId, supabase]);

  useEffect(() => {
    loadLead();
  }, [loadLead]);

  async function handleStatusChange(newStatus: LeadStatus) {
    if (!lead || !currentOrg) return;

    await supabase
      .from("leads")
      .update({ status: newStatus })
      .eq("id", lead.id)
      .eq("org_id", currentOrg.org_id);

    await supabase.from("lead_events").insert({
      lead_id: lead.id,
      org_id: currentOrg.org_id,
      event_type: "status_changed",
      source: "app",
      payload: { from: lead.status, to: newStatus },
      created_by: userId,
    });

    loadLead();
  }

  if (loading) {
    return <p style={{ color: "var(--text-muted)" }}>Loading...</p>;
  }

  if (!lead) {
    return <p style={{ color: "var(--danger)" }}>Lead not found.</p>;
  }

  return (
    <div>
      <button
        className="btn btn-sm"
        onClick={() => router.push("/dashboard/leads")}
        style={{ marginBottom: "1rem" }}
      >
        &larr; Back to Leads
      </button>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1.5rem" }}>
        {/* Left column: Contact info */}
        <div>
          <div className="card" style={{ marginBottom: "1rem" }}>
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "flex-start",
                marginBottom: "1rem",
              }}
            >
              <div>
                <h1 style={{ fontSize: "1.5rem" }}>{lead.name}</h1>
                <StatusBadge status={lead.status} />
              </div>
              <select
                className="input"
                style={{ width: "auto" }}
                value={lead.status}
                onChange={(e) => handleStatusChange(e.target.value as LeadStatus)}
              >
                {STATUSES.map((s) => (
                  <option key={s} value={s}>
                    {s.charAt(0).toUpperCase() + s.slice(1)}
                  </option>
                ))}
              </select>
            </div>

            <div style={{ display: "grid", gap: "0.5rem", fontSize: "0.9rem" }}>
              <InfoRow label="Email" value={lead.email} />
              <InfoRow label="Phone" value={lead.phone} />
              <InfoRow label="Source URL" value={lead.source_url} />
              <InfoRow label="UTM Source" value={lead.utm_source} />
              <InfoRow label="UTM Medium" value={lead.utm_medium} />
              <InfoRow label="UTM Campaign" value={lead.utm_campaign} />
              <InfoRow
                label="Created"
                value={new Date(lead.created_at).toLocaleString()}
              />
            </div>

            {lead.message && (
              <div style={{ marginTop: "1rem" }}>
                <p
                  style={{
                    fontSize: "0.8rem",
                    fontWeight: 600,
                    color: "var(--text-muted)",
                    marginBottom: "0.25rem",
                  }}
                >
                  Message
                </p>
                <p
                  style={{
                    background: "var(--bg-secondary)",
                    padding: "0.75rem",
                    borderRadius: "var(--radius)",
                    fontSize: "0.9rem",
                    whiteSpace: "pre-wrap",
                  }}
                >
                  {lead.message}
                </p>
              </div>
            )}
          </div>

          <div className="card">
            <h3 style={{ fontSize: "1rem", marginBottom: "0.75rem" }}>Add Note</h3>
            <AddNoteForm
              leadId={lead.id}
              orgId={currentOrg!.org_id}
              userId={userId}
              onAdded={loadLead}
            />
          </div>
        </div>

        {/* Right column: Timeline */}
        <div>
          <div className="card">
            <h3 style={{ fontSize: "1rem", marginBottom: "0.75rem" }}>
              Timeline ({events.length} events)
            </h3>
            <LeadTimeline events={events} />
          </div>
        </div>
      </div>
    </div>
  );
}

function InfoRow({
  label,
  value,
}: {
  label: string;
  value: string | null | undefined;
}) {
  if (!value) return null;
  return (
    <div style={{ display: "flex", gap: "0.5rem" }}>
      <span style={{ fontWeight: 600, color: "var(--text-muted)", minWidth: 120 }}>
        {label}
      </span>
      <span>{value}</span>
    </div>
  );
}
