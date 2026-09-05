import { createFileRoute } from "@tanstack/react-router";
import { AuditApp } from "@/components/audit-app";

export const Route = createFileRoute("/")({ component: Home });

function Home() {
  return <AuditApp />;
}
