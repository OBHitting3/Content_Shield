import { redirect } from "next/navigation";
import { createClient } from "@/lib/supabase/server";
import { OrgProvider } from "@/components/dashboard/org-context";
import { Sidebar } from "@/components/dashboard/sidebar";
import type { MembershipWithOrg } from "@/types/database";

export default async function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (!user) {
    redirect("/login");
  }

  const { data: memberships } = await supabase
    .from("memberships")
    .select("*, organizations(*)")
    .eq("user_id", user.id)
    .returns<MembershipWithOrg[]>();

  return (
    <OrgProvider memberships={memberships || []} userId={user.id}>
      <div style={{ display: "flex", minHeight: "100vh" }}>
        <Sidebar userEmail={user.email || ""} />
        <main
          style={{ flex: 1, padding: "1.5rem", background: "var(--bg-secondary)" }}
        >
          {children}
        </main>
      </div>
    </OrgProvider>
  );
}
