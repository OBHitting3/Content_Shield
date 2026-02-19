"use client";

import { useState } from "react";
import { createClient } from "@/lib/supabase/client";

export function CreateOrgDialog({ onClose }: { onClose: () => void }) {
  const [name, setName] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const supabase = createClient();

  function toSlug(s: string): string {
    return s
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, "-")
      .replace(/^-|-$/g, "");
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError("");

    const slug = toSlug(name);
    if (!slug) {
      setError("Invalid name.");
      setLoading(false);
      return;
    }

    const { error: rpcError } = await supabase.rpc("create_org_with_owner", {
      org_name: name,
      org_slug: slug,
    });

    setLoading(false);
    if (rpcError) {
      setError(rpcError.message);
    } else {
      window.location.reload();
    }
  }

  return (
    <div
      style={{
        position: "fixed",
        inset: 0,
        background: "rgba(0,0,0,0.4)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        zIndex: 1000,
      }}
      onClick={onClose}
    >
      <div
        className="card"
        style={{ width: 380 }}
        onClick={(e) => e.stopPropagation()}
      >
        <h3 style={{ marginBottom: "1rem" }}>Create Organization</h3>
        <form onSubmit={handleSubmit}>
          <input
            className="input"
            placeholder="Organization name"
            value={name}
            onChange={(e) => setName(e.target.value)}
            required
            autoFocus
          />
          {error && (
            <p style={{ color: "var(--danger)", fontSize: "0.8rem", marginTop: "0.5rem" }}>
              {error}
            </p>
          )}
          <div style={{ display: "flex", gap: "0.5rem", marginTop: "1rem", justifyContent: "flex-end" }}>
            <button type="button" className="btn" onClick={onClose}>
              Cancel
            </button>
            <button type="submit" className="btn btn-primary" disabled={loading}>
              {loading ? "Creating..." : "Create"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
