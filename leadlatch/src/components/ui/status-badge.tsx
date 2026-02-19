import type { LeadStatus } from "@/types/database";

export function StatusBadge({ status }: { status: LeadStatus }) {
  return <span className={`badge badge-${status}`}>{status}</span>;
}
