"use client";

import { useOrg } from "@/components/dashboard/org-context";
import { useEffect, useState } from "react";
import { createClient } from "@/lib/supabase/client";
import type { LeadStatus } from "@/types/database";

interface Stats {
  total: number;
  new: number;
  working: number;
  won: number;
  lost: number;
}

export default function DashboardPage() {
  const { currentOrg } = useOrg();
  const [stats, setStats] = useState<Stats>({
    total: 0,
    new: 0,
    working: 0,
    won: 0,
    lost: 0,
  });
  const supabase = createClient();

  useEffect(() => {
    if (!currentOrg) return;

    async function loadStats() {
      const { data: leads } = await supabase
        .from("leads")
        .select("status")
        .eq("org_id", currentOrg!.org_id);

      if (leads) {
        const s: Stats = { total: leads.length, new: 0, working: 0, won: 0, lost: 0 };
        leads.forEach((l: { status: LeadStatus }) => {
          s[l.status]++;
        });
        setStats(s);
      }
    }

    loadStats();
  }, [currentOrg, supabase]);

  if (!currentOrg) {
    return (
      <div>
        <h1 style={{ fontSize: "1.5rem", marginBottom: "1rem" }}>Dashboard</h1>
        <p style={{ color: "var(--text-muted)" }}>
          Create an organization to get started.
        </p>
      </div>
    );
  }

  const statCards: { label: string; value: number; color: string }[] = [
    { label: "Total Leads", value: stats.total, color: "var(--text)" },
    { label: "New", value: stats.new, color: "#2563eb" },
    { label: "Working", value: stats.working, color: "#d97706" },
    { label: "Won", value: stats.won, color: "#16a34a" },
    { label: "Lost", value: stats.lost, color: "#dc2626" },
  ];

  return (
    <div>
      <h1 style={{ fontSize: "1.5rem", marginBottom: "1rem" }}>
        {currentOrg.organizations.name} — Dashboard
      </h1>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))", gap: "1rem" }}>
        {statCards.map((s) => (
          <div key={s.label} className="card" style={{ textAlign: "center" }}>
            <p style={{ fontSize: "0.8rem", color: "var(--text-muted)", marginBottom: "0.25rem" }}>
              {s.label}
            </p>
            <p style={{ fontSize: "2rem", fontWeight: 700, color: s.color }}>
              {s.value}
            </p>
          </div>
        ))}
      </div>
    </div>
  );
}
