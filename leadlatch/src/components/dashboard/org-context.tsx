"use client";

import {
  createContext,
  useContext,
  useState,
  useCallback,
  type ReactNode,
} from "react";
import type { MembershipWithOrg, MembershipRole } from "@/types/database";

interface OrgContextValue {
  currentOrg: MembershipWithOrg | null;
  memberships: MembershipWithOrg[];
  switchOrg: (orgId: string) => void;
  currentRole: MembershipRole | null;
  userId: string;
}

const OrgContext = createContext<OrgContextValue | null>(null);

export function OrgProvider({
  memberships,
  userId,
  children,
}: {
  memberships: MembershipWithOrg[];
  userId: string;
  children: ReactNode;
}) {
  const [currentOrgId, setCurrentOrgId] = useState<string | null>(
    memberships[0]?.org_id ?? null
  );

  const currentOrg =
    memberships.find((m) => m.org_id === currentOrgId) ?? null;

  const switchOrg = useCallback((orgId: string) => {
    setCurrentOrgId(orgId);
  }, []);

  return (
    <OrgContext.Provider
      value={{
        currentOrg,
        memberships,
        switchOrg,
        currentRole: currentOrg?.role ?? null,
        userId,
      }}
    >
      {children}
    </OrgContext.Provider>
  );
}

export function useOrg() {
  const ctx = useContext(OrgContext);
  if (!ctx) throw new Error("useOrg must be used inside OrgProvider");
  return ctx;
}
