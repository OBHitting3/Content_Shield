import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "LeadLatch — Speed-to-Lead Autopilot",
  description: "Capture, respond, and follow up with leads automatically.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
