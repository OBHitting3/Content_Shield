"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { OrgSwitcher } from "./org-switcher";
import { createClient } from "@/lib/supabase/client";

const navItems = [
  { href: "/dashboard", label: "Overview" },
  { href: "/dashboard/leads", label: "Leads" },
  { href: "/dashboard/settings", label: "Settings" },
];

export function Sidebar({ userEmail }: { userEmail: string }) {
  const pathname = usePathname();
  const supabase = createClient();

  async function handleSignOut() {
    await supabase.auth.signOut();
    window.location.href = "/login";
  }

  return (
    <aside
      style={{
        width: 240,
        background: "var(--bg)",
        borderRight: "1px solid var(--border)",
        display: "flex",
        flexDirection: "column",
        padding: "1rem",
      }}
    >
      <div style={{ marginBottom: "1.5rem" }}>
        <h2 style={{ fontSize: "1.1rem", fontWeight: 700 }}>LeadLatch</h2>
      </div>

      <OrgSwitcher />

      <nav style={{ flex: 1, marginTop: "1rem" }}>
        {navItems.map((item) => {
          const isActive =
            item.href === "/dashboard"
              ? pathname === "/dashboard"
              : pathname.startsWith(item.href);
          return (
            <Link
              key={item.href}
              href={item.href}
              style={{
                display: "block",
                padding: "0.5rem 0.75rem",
                borderRadius: "var(--radius)",
                marginBottom: "0.25rem",
                fontSize: "0.875rem",
                fontWeight: isActive ? 600 : 400,
                background: isActive ? "var(--bg-secondary)" : "transparent",
                color: isActive ? "var(--text)" : "var(--text-muted)",
                textDecoration: "none",
              }}
            >
              {item.label}
            </Link>
          );
        })}
      </nav>

      <div
        style={{
          borderTop: "1px solid var(--border)",
          paddingTop: "0.75rem",
          marginTop: "auto",
        }}
      >
        <p
          style={{
            fontSize: "0.75rem",
            color: "var(--text-muted)",
            marginBottom: "0.5rem",
            overflow: "hidden",
            textOverflow: "ellipsis",
            whiteSpace: "nowrap",
          }}
        >
          {userEmail}
        </p>
        <button
          onClick={handleSignOut}
          className="btn btn-sm"
          style={{ width: "100%" }}
        >
          Sign Out
        </button>
      </div>
    </aside>
  );
}
