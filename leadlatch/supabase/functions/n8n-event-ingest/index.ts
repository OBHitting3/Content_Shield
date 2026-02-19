/**
 * Supabase Edge Function: n8n-event-ingest
 *
 * Secured endpoint for n8n to write back event updates to Supabase.
 * n8n calls this after sending emails, scheduling follow-ups, posting to Slack, etc.
 *
 * Auth: Shared secret via X-Leadlatch-Secret header.
 * Method: POST
 */

import { createClient } from "https://esm.sh/@supabase/supabase-js@2.49.1";
import { corsHeaders } from "../_shared/cors.ts";

interface EventPayload {
  lead_id: string;
  org_id: string;
  event_type:
    | "email_sent"
    | "email_opened"
    | "email_replied"
    | "sms_sent"
    | "slack_posted"
    | "followup_scheduled"
    | "followup_sent"
    | "status_changed"
    | "custom";
  payload?: Record<string, unknown>;
  new_status?: "new" | "working" | "won" | "lost";
  idempotency_key?: string;
}

Deno.serve(async (req: Request) => {
  if (req.method === "OPTIONS") {
    return new Response("ok", { headers: corsHeaders });
  }

  if (req.method !== "POST") {
    return new Response(JSON.stringify({ error: "Method not allowed" }), {
      status: 405,
      headers: { ...corsHeaders, "Content-Type": "application/json" },
    });
  }

  // Authenticate via shared secret
  const secret = req.headers.get("x-leadlatch-secret");
  const expectedSecret = Deno.env.get("N8N_EVENT_INGEST_SECRET");

  if (!expectedSecret || secret !== expectedSecret) {
    return new Response(JSON.stringify({ error: "Unauthorized" }), {
      status: 401,
      headers: { ...corsHeaders, "Content-Type": "application/json" },
    });
  }

  try {
    const body: EventPayload = await req.json();

    if (!body.lead_id || !body.org_id || !body.event_type) {
      return new Response(
        JSON.stringify({
          error: "lead_id, org_id, and event_type are required",
        }),
        {
          status: 400,
          headers: { ...corsHeaders, "Content-Type": "application/json" },
        }
      );
    }

    const supabaseUrl = Deno.env.get("SUPABASE_URL")!;
    const serviceRoleKey = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!;
    const supabase = createClient(supabaseUrl, serviceRoleKey);

    // Idempotency check: if key provided, skip duplicate events
    if (body.idempotency_key) {
      const { data: existing } = await supabase
        .from("lead_events")
        .select("id")
        .eq("lead_id", body.lead_id)
        .eq("org_id", body.org_id)
        .contains("payload", { idempotency_key: body.idempotency_key })
        .limit(1);

      if (existing && existing.length > 0) {
        return new Response(
          JSON.stringify({
            success: true,
            deduplicated: true,
            event_id: existing[0].id,
          }),
          {
            status: 200,
            headers: { ...corsHeaders, "Content-Type": "application/json" },
          }
        );
      }
    }

    // Insert lead event
    const eventPayload = {
      ...(body.payload || {}),
      ...(body.idempotency_key
        ? { idempotency_key: body.idempotency_key }
        : {}),
    };

    const { data: event, error: eventError } = await supabase
      .from("lead_events")
      .insert({
        lead_id: body.lead_id,
        org_id: body.org_id,
        event_type: body.event_type,
        source: "n8n",
        payload: eventPayload,
      })
      .select("id")
      .single();

    if (eventError) {
      console.error("Event insert error:", eventError);
      return new Response(
        JSON.stringify({ error: "Failed to insert event" }),
        {
          status: 500,
          headers: { ...corsHeaders, "Content-Type": "application/json" },
        }
      );
    }

    // Optionally update lead status
    if (body.new_status) {
      const { error: statusError } = await supabase
        .from("leads")
        .update({ status: body.new_status })
        .eq("id", body.lead_id)
        .eq("org_id", body.org_id);

      if (statusError) {
        console.error("Status update error:", statusError);
      } else {
        // Record status change event
        await supabase.from("lead_events").insert({
          lead_id: body.lead_id,
          org_id: body.org_id,
          event_type: "status_changed",
          source: "n8n",
          payload: { new_status: body.new_status },
        });
      }
    }

    return new Response(
      JSON.stringify({
        success: true,
        event_id: event?.id,
      }),
      {
        status: 200,
        headers: { ...corsHeaders, "Content-Type": "application/json" },
      }
    );
  } catch (err) {
    console.error("Unhandled error:", err);
    return new Response(
      JSON.stringify({ error: "Internal server error" }),
      {
        status: 500,
        headers: { ...corsHeaders, "Content-Type": "application/json" },
      }
    );
  }
});
