"use client";

import { useState } from "react";
import { createClient } from "@/lib/supabase/client";

export function AddNoteForm({
  leadId,
  orgId,
  userId,
  onAdded,
}: {
  leadId: string;
  orgId: string;
  userId: string;
  onAdded: () => void;
}) {
  const [note, setNote] = useState("");
  const [saving, setSaving] = useState(false);
  const supabase = createClient();

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!note.trim()) return;
    setSaving(true);

    const { error } = await supabase.from("lead_events").insert({
      lead_id: leadId,
      org_id: orgId,
      event_type: "note_added",
      source: "app",
      payload: { note: note.trim() },
      created_by: userId,
    });

    setSaving(false);
    if (!error) {
      setNote("");
      onAdded();
    }
  }

  return (
    <form onSubmit={handleSubmit}>
      <textarea
        className="input"
        rows={3}
        placeholder="Write a note..."
        value={note}
        onChange={(e) => setNote(e.target.value)}
        style={{ resize: "vertical", marginBottom: "0.5rem" }}
      />
      <button
        type="submit"
        className="btn btn-primary btn-sm"
        disabled={saving || !note.trim()}
      >
        {saving ? "Saving..." : "Add Note"}
      </button>
    </form>
  );
}
