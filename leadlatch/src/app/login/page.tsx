"use client";

import { useState } from "react";
import { createClient } from "@/lib/supabase/client";

export default function LoginPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [mode, setMode] = useState<"magic_link" | "password">("magic_link");
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);
  const supabase = createClient();

  async function handleMagicLink(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setMessage("");

    const { error } = await supabase.auth.signInWithOtp({
      email,
      options: {
        emailRedirectTo: `${window.location.origin}/auth/callback`,
      },
    });

    setLoading(false);
    if (error) {
      setMessage(error.message);
    } else {
      setMessage("Check your email for the login link.");
    }
  }

  async function handlePassword(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setMessage("");

    const { error } = await supabase.auth.signInWithPassword({
      email,
      password,
    });

    setLoading(false);
    if (error) {
      if (error.message.includes("Invalid login")) {
        const { error: signUpError } = await supabase.auth.signUp({
          email,
          password,
          options: {
            emailRedirectTo: `${window.location.origin}/auth/callback`,
          },
        });
        if (signUpError) {
          setMessage(signUpError.message);
        } else {
          setMessage("Account created. Check email to confirm, then sign in.");
        }
      } else {
        setMessage(error.message);
      }
    } else {
      window.location.href = "/dashboard";
    }
  }

  return (
    <div
      style={{
        minHeight: "100vh",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        background: "var(--bg-secondary)",
      }}
    >
      <div className="card" style={{ width: "100%", maxWidth: 400 }}>
        <h1 style={{ fontSize: "1.5rem", marginBottom: "0.25rem" }}>
          LeadLatch
        </h1>
        <p
          style={{
            color: "var(--text-muted)",
            marginBottom: "1.5rem",
            fontSize: "0.875rem",
          }}
        >
          Speed-to-Lead Autopilot
        </p>

        <div style={{ display: "flex", gap: "0.5rem", marginBottom: "1rem" }}>
          <button
            className={`btn btn-sm ${mode === "magic_link" ? "btn-primary" : ""}`}
            onClick={() => setMode("magic_link")}
          >
            Magic Link
          </button>
          <button
            className={`btn btn-sm ${mode === "password" ? "btn-primary" : ""}`}
            onClick={() => setMode("password")}
          >
            Password
          </button>
        </div>

        <form
          onSubmit={mode === "magic_link" ? handleMagicLink : handlePassword}
        >
          <div style={{ marginBottom: "0.75rem" }}>
            <label
              htmlFor="email"
              style={{
                display: "block",
                fontSize: "0.8rem",
                fontWeight: 600,
                marginBottom: "0.25rem",
              }}
            >
              Email
            </label>
            <input
              id="email"
              type="email"
              className="input"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              placeholder="you@company.com"
            />
          </div>

          {mode === "password" && (
            <div style={{ marginBottom: "0.75rem" }}>
              <label
                htmlFor="password"
                style={{
                  display: "block",
                  fontSize: "0.8rem",
                  fontWeight: 600,
                  marginBottom: "0.25rem",
                }}
              >
                Password
              </label>
              <input
                id="password"
                type="password"
                className="input"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                minLength={6}
                placeholder="••••••••"
              />
            </div>
          )}

          <button
            type="submit"
            className="btn btn-primary"
            style={{ width: "100%" }}
            disabled={loading}
          >
            {loading
              ? "Loading..."
              : mode === "magic_link"
                ? "Send Magic Link"
                : "Sign In / Sign Up"}
          </button>
        </form>

        {message && (
          <p
            style={{
              marginTop: "1rem",
              fontSize: "0.85rem",
              color: message.includes("Check")
                ? "var(--success)"
                : "var(--danger)",
            }}
          >
            {message}
          </p>
        )}
      </div>
    </div>
  );
}
