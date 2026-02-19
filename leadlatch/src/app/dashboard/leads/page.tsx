"use client";

import { useOrg } from "@/components/dashboard/org-context";
import { useEffect, useState, useCallback } from "react";
import { createClient } from "@/lib/supabase/client";
import { StatusBadge } from "@/components/ui/status-badge";
import Link from "next/link";
import type { Lead, LeadStatus } from "@/types/database";

const STATUS_OPTIONS: (LeadStatus | "all")[] = [
  "all",
  "new",
  "working",
  "won",
  "lost",
];

export default function LeadsPage() {
  const { currentOrg } = useOrg();
  const [leads, setLeads] = useState<Lead[]>([]);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState<LeadStatus | "all">("all");
  const [search, setSearch] = useState("");
  const supabase = createClient();

  const loadLeads = useCallback(async () => {
    if (!currentOrg) return;
    setLoading(true);

    let query = supabase
      .from("leads")
      .select("*")
      .eq("org_id", currentOrg.org_id)
      .order("created_at", { ascending: false });

    if (statusFilter !== "all") {
      query = query.eq("status", statusFilter);
    }
    if (search.trim()) {
      query = query.or(
        `name.ilike.%${search}%,email.ilike.%${search}%,phone.ilike.%${search}%`
      );
    }

    const { data } = await query;
    setLeads((data as Lead[]) || []);
    setLoading(false);
  }, [currentOrg, statusFilter, search, supabase]);

  useEffect(() => {
    loadLeads();
  }, [loadLeads]);

  if (!currentOrg) {
    return <p style={{ color: "var(--text-muted)" }}>Select an organization.</p>;
  }

  return (
    <div>
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginBottom: "1rem",
        }}
      >
        <h1 style={{ fontSize: "1.5rem" }}>Leads</h1>
      </div>

      <div
        style={{
          display: "flex",
          gap: "0.75rem",
          marginBottom: "1rem",
          flexWrap: "wrap",
          alignItems: "center",
        }}
      >
        <input
          className="input"
          style={{ maxWidth: 260 }}
          placeholder="Search name, email, phone..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
        <select
          className="input"
          style={{ maxWidth: 140 }}
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value as LeadStatus | "all")}
        >
          {STATUS_OPTIONS.map((s) => (
            <option key={s} value={s}>
              {s === "all" ? "All Statuses" : s.charAt(0).toUpperCase() + s.slice(1)}
            </option>
          ))}
        </select>
      </div>

      <div className="card" style={{ padding: 0, overflow: "auto" }}>
        {loading ? (
          <p style={{ padding: "2rem", textAlign: "center", color: "var(--text-muted)" }}>
            Loading...
          </p>
        ) : leads.length === 0 ? (
          <p style={{ padding: "2rem", textAlign: "center", color: "var(--text-muted)" }}>
            No leads found.
          </p>
        ) : (
          <table>
            <thead>
              <tr>
                <th>Name</th>
                <th>Email</th>
                <th>Phone</th>
                <th>Status</th>
                <th>Source</th>
                <th>Created</th>
              </tr>
            </thead>
            <tbody>
              {leads.map((lead) => (
                <tr key={lead.id}>
                  <td>
                    <Link
                      href={`/dashboard/leads/${lead.id}`}
                      style={{ fontWeight: 500 }}
                    >
                      {lead.name}
                    </Link>
                  </td>
                  <td style={{ fontSize: "0.85rem" }}>{lead.email || "—"}</td>
                  <td style={{ fontSize: "0.85rem" }}>{lead.phone || "—"}</td>
                  <td>
                    <StatusBadge status={lead.status} />
                  </td>
                  <td style={{ fontSize: "0.85rem" }}>
                    {lead.utm_source || lead.source_url || "—"}
                  </td>
                  <td style={{ fontSize: "0.85rem", color: "var(--text-muted)" }}>
                    {new Date(lead.created_at).toLocaleDateString()}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
