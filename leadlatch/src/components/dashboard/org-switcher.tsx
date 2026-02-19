"use client";

import { useOrg } from "./org-context";
import { useState } from "react";
import { CreateOrgDialog } from "./create-org-dialog";

export function OrgSwitcher() {
  const { currentOrg, memberships, switchOrg } = useOrg();
  const [showCreate, setShowCreate] = useState(false);

  if (memberships.length === 0) {
    return (
      <div>
        <p style={{ fontSize: "0.8rem", color: "var(--text-muted)", marginBottom: "0.5rem" }}>
          No organization yet.
        </p>
        <button className="btn btn-primary btn-sm" onClick={() => setShowCreate(true)}>
          Create Organization
        </button>
        {showCreate && <CreateOrgDialog onClose={() => setShowCreate(false)} />}
      </div>
    );
  }

  return (
    <div>
      <label
        htmlFor="org-select"
        style={{ fontSize: "0.7rem", color: "var(--text-muted)", display: "block", marginBottom: "0.25rem" }}
      >
        Organization
      </label>
      <select
        id="org-select"
        className="input"
        value={currentOrg?.org_id || ""}
        onChange={(e) => switchOrg(e.target.value)}
        style={{ fontSize: "0.85rem" }}
      >
        {memberships.map((m) => (
          <option key={m.org_id} value={m.org_id}>
            {m.organizations.name}
          </option>
        ))}
      </select>
      <button
        className="btn btn-sm"
        style={{ marginTop: "0.5rem", width: "100%" }}
        onClick={() => setShowCreate(true)}
      >
        + New Org
      </button>
      {showCreate && <CreateOrgDialog onClose={() => setShowCreate(false)} />}
    </div>
  );
}
