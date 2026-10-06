import { useQuery } from "@tanstack/react-query";
import { ShieldCheck } from "lucide-react";
import { apiGet } from "@/lib/api";
import type { AuditLog } from "@/lib/types";
import AppShell from "@/components/layout/AppShell";
import { Badge } from "@/components/ui/badge";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { EmptyBlock, ErrorBlock, LoadingBlock } from "@/components/States";

function describe(log: AuditLog): string {
  const parts: string[] = [];
  if (log.before) parts.push(`antes: ${JSON.stringify(log.before)}`);
  if (log.after) parts.push(`depois: ${JSON.stringify(log.after)}`);
  return parts.join(" · ") || "—";
}

export default function Auditoria() {
  const { data, isLoading, isError } = useQuery<AuditLog[]>({
    queryKey: ["audit"],
    queryFn: () => apiGet<AuditLog[]>("/audit-logs?limit=200"),
    retry: false,
  });

  return (
    <AppShell title="Auditoria" subtitle="Trilha imutável de ações realizadas na empresa">
      <div className="flex items-center gap-2 rounded-xl border border-border bg-card p-4 text-sm text-muted-foreground">
        <ShieldCheck className="size-4 shrink-0 text-emerald-600" aria-hidden="true" />
        Os eventos são gravados pelo backend e não podem ser editados ou excluídos pela aplicação.
      </div>

      {isError ? (
        <ErrorBlock label="Não foi possível carregar a auditoria." />
      ) : isLoading ? (
        <LoadingBlock label="Carregando eventos…" />
      ) : !data || data.length === 0 ? (
        <EmptyBlock label="Nenhum evento registrado" testId="audit-empty" />
      ) : (
        <div className="rounded-xl border border-border bg-card">
          <Table data-testid="audit-table">
            <TableHeader>
              <TableRow>
                <TableHead>Data/Hora</TableHead>
                <TableHead>Ação</TableHead>
                <TableHead>Responsável</TableHead>
                <TableHead>Recurso</TableHead>
                <TableHead>Alteração</TableHead>
                <TableHead>IP</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {data.map((log) => (
                <TableRow key={log.id} data-testid="audit-row">
                  <TableCell className="whitespace-nowrap font-mono text-xs">
                    {new Date(log.created_at).toLocaleString("pt-BR", { timeZone: "America/Belem" })}
                  </TableCell>
                  <TableCell>
                    <Badge variant="outline" className="font-mono text-[11px] font-bold" data-testid="audit-row-action">
                      {log.action}
                    </Badge>
                  </TableCell>
                  <TableCell>
                    <span className="font-semibold">{log.actor_name}</span>
                    <span className="ml-1 text-xs text-muted-foreground">({log.actor_role})</span>
                  </TableCell>
                  <TableCell className="text-sm">{log.resource}</TableCell>
                  <TableCell className="max-w-[320px] truncate text-xs text-muted-foreground" title={describe(log)}>
                    {describe(log)}
                  </TableCell>
                  <TableCell className="font-mono text-xs text-muted-foreground">{log.ip ?? "—"}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}
    </AppShell>
  );
}
