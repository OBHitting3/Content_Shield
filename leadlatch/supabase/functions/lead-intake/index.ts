/**
 * Supabase Edge Function: lead-intake
 *
 * Public endpoint that accepts form submissions, inserts a lead + event,
 * and fires the n8n webhook for automation.
 *
 * Deployed at: /functions/v1/lead-intake
 * Method: POST
 * Auth: None (public endpoint — org_id is required in the body)
 */

import { createClient } from "https://esm.sh/@supabase/supabase-js@2.49.1";
import { corsHeaders } from "../_shared/cors.ts";

interface LeadPayload {
  org_id: string;
  name: string;
  email?: string;
  phone?: string;
  message?: string;
  source_url?: string;
  utm_source?: string;
  utm_medium?: string;
  utm_campaign?: string;
  utm_term?: string;
  utm_content?: string;
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

  try {
    const body: LeadPayload = await req.json();

    if (!body.org_id || !body.name) {
      return new Response(
        JSON.stringify({ error: "org_id and name are required" }),
        {
          status: 400,
          headers: { ...corsHeaders, "Content-Type": "application/json" },
        }
      );
    }

    const supabaseUrl = Deno.env.get("SUPABASE_URL")!;
    const serviceRoleKey = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!;
    const supabase = createClient(supabaseUrl, serviceRoleKey);

    // Verify org exists
    const { data: org, error: orgError } = await supabase
      .from("organizations")
      .select("id")
      .eq("id", body.org_id)
      .single();

    if (orgError || !org) {
      return new Response(
        JSON.stringify({ error: "Organization not found" }),
        {
          status: 404,
          headers: { ...corsHeaders, "Content-Type": "application/json" },
        }
      );
    }

    // Insert lead
    const { data: lead, error: leadError } = await supabase
      .from("leads")
      .insert({
        org_id: body.org_id,
        name: body.name,
        email: body.email || null,
        phone: body.phone || null,
        message: body.message || null,
        source_url: body.source_url || null,
        utm_source: body.utm_source || null,
        utm_medium: body.utm_medium || null,
        utm_campaign: body.utm_campaign || null,
        utm_term: body.utm_term || null,
        utm_content: body.utm_content || null,
        status: "new",
      })
      .select()
      .single();

    if (leadError || !lead) {
      console.error("Lead insert error:", leadError);
      return new Response(
        JSON.stringify({ error: "Failed to create lead" }),
        {
          status: 500,
          headers: { ...corsHeaders, "Content-Type": "application/json" },
        }
      );
    }

    // Record "created" event
    const { error: eventError } = await supabase.from("lead_events").insert({
      lead_id: lead.id,
      org_id: body.org_id,
      event_type: "created",
      source: "edge_function",
      payload: {
        source_url: body.source_url || null,
        utm_source: body.utm_source || null,
      },
    });

    if (eventError) {
      console.error("Event insert error:", eventError);
    }

    // Fire n8n webhook (async, non-blocking)
    const n8nWebhookUrl = Deno.env.get("N8N_WEBHOOK_URL");
    if (n8nWebhookUrl) {
      const webhookPayload = {
        lead_id: lead.id,
        org_id: lead.org_id,
        name: lead.name,
        email: lead.email,
        phone: lead.phone,
        message: lead.message,
        source_url: lead.source_url,
        utm_source: lead.utm_source,
        created_at: lead.created_at,
      };

      // Fire and forget — don't block the response
      fetch(n8nWebhookUrl, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(webhookPayload),
      }).catch((err) => {
        console.error("n8n webhook call failed:", err);
      });

      // Record webhook event
      supabase
        .from("lead_events")
        .insert({
          lead_id: lead.id,
          org_id: body.org_id,
          event_type: "webhook_fired",
          source: "edge_function",
          payload: { webhook_url: n8nWebhookUrl, status: "dispatched" },
        })
        .then(({ error }) => {
          if (error) console.error("Webhook event insert error:", error);
        });
    }

    return new Response(
      JSON.stringify({
        success: true,
        lead_id: lead.id,
        status: "new",
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
