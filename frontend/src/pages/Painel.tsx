import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { apiGet } from "@/lib/api";
import type { Adjustment, Alerts, Dashboard, LiveBoardRow } from "@/lib/types";
import AppShell from "@/components/layout/AppShell";
import KpiCard from "@/components/KpiCard";
import StatusBadge from "@/components/StatusBadge";
import ApprovalQueueCard from "@/components/admin/ApprovalQueueCard";
import AlertCard from "@/components/admin/AlertCard";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { buttonVariants } from "@/components/ui/button";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { EmptyBlock, ErrorBlock, LoadingBlock } from "@/components/States";

export default function Painel() {
  const { data, isLoading, isError } = useQuery<Dashboard>({
    queryKey: ["dashboard"],
    queryFn: () => apiGet<Dashboard>("/dashboard"),
    retry: false,
    refetchInterval: 60_000,
  });
  const { data: board } = useQuery<LiveBoardRow[]>({
    queryKey: ["live-board"],
    queryFn: () => apiGet<LiveBoardRow[]>("/time-records/live"),
    retry: false,
    refetchInterval: 60_000,
  });
  const { data: pending } = useQuery<Adjustment[]>({
    queryKey: ["adjustments", "pendente"],
    queryFn: () => apiGet<Adjustment[]>("/adjustment-requests?status=pendente"),
    retry: false,
  });
  const { data: alerts } = useQuery<Alerts>({
    queryKey: ["alerts"],
    queryFn: () => apiGet<Alerts>("/alerts"),
    retry: false,
    refetchInterval: 60_000,
  });

  return (
    <AppShell
      title="Painel Operacional"
      subtitle={data ? `Situação de hoje, ${data.local_date.split("-").reverse().join("/")}${data.holiday_name ? ` · Feriado: ${data.holiday_name}` : ""}` : "Indicadores do dia"}
    >
      {isError ? <ErrorBlock label="Não foi possível carregar os indicadores agora." /> : null}

      <div className="grid grid-cols-2 gap-3 md:grid-cols-4 lg:grid-cols-8">
        <KpiCard label="Ativos" value={data?.employees_active ?? "—"} testId="admin-kpi-ativos" />
        <KpiCard label="Presentes" value={data?.present_now ?? "—"} tone="good" testId="admin-kpi-presentes" />
        <KpiCard label="Em intervalo" value={data?.on_interval ?? "—"} tone="info" testId="admin-kpi-intervalo" />
        <KpiCard label="Ausentes" value={data?.absent ?? "—"} tone="bad" testId="admin-kpi-ausentes" />
        <KpiCard label="Atrasados" value={data?.delayed ?? "—"} tone="warn" testId="admin-kpi-atrasados" />
        <KpiCard label="Incompletas" value={data?.incomplete_days ?? "—"} tone="warn" testId="admin-kpi-incompletas" />
        <KpiCard label="Pendências" value={data?.pending_requests ?? "—"} tone="warn" testId="admin-kpi-pendentes" />
        <KpiCard label="Extras hoje" value={data?.overtime_hhmm ?? "—"} tone="info" testId="admin-kpi-extras" />
      </div>

      <div className="grid grid-cols-1 items-start gap-7 lg:grid-cols-12">
        <section className="space-y-3 lg:col-span-8">
          <div className="flex items-center justify-between gap-3">
            <h2 className="text-lg font-bold tracking-tight">Quadro do dia</h2>
            <Link to="/relatorios" className={buttonVariants({ variant: "outline", size: "sm" })} data-testid="link-relatorios">
              Ver relatórios
            </Link>
          </div>
          {isLoading && !board ? (
            <LoadingBlock label="Carregando quadro do dia…" />
          ) : !board || board.length === 0 ? (
            <EmptyBlock label="Nenhum funcionário ativo" hint="Cadastre funcionários para acompanhar a jornada." testId="live-board-empty" />
          ) : (
            <div className="rounded-xl border border-border bg-card">
              <Table data-testid="live-board-table">
                <TableHeader>
                  <TableRow>
                    <TableHead>Funcionário</TableHead>
                    <TableHead>Departamento</TableHead>
                    <TableHead>Entrada</TableHead>
                    <TableHead>Saída</TableHead>
                    <TableHead className="text-right">Trabalhado</TableHead>
                    <TableHead className="text-right">Atraso</TableHead>
                    <TableHead>Situação</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {board.map((row) => (
                    <TableRow key={row.employee_id} data-testid="live-board-row">
                      <TableCell className="font-semibold">{row.employee_name}</TableCell>
                      <TableCell className="text-muted-foreground">{row.department ?? "—"}</TableCell>
                      <TableCell className="font-mono">{row.entrada ?? "—"}</TableCell>
                      <TableCell className="font-mono">{row.saida ?? "—"}</TableCell>
                      <TableCell className="text-right font-mono font-semibold">{row.worked_hhmm ?? "—"}</TableCell>
                      <TableCell className="text-right font-mono text-amber-600 dark:text-amber-400">
                        {row.delay_minutes ? row.delay_hhmm : "—"}
                      </TableCell>
                      <TableCell>
                        <StatusBadge status={row.state} testId="live-board-state" />
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          )}
        </section>

        <aside className="space-y-4 lg:col-span-4">
          <Card>
            <CardHeader className="flex-row items-center justify-between gap-2">
              <CardTitle className="text-base">Alertas de pendência</CardTitle>
              <Link to="/alertas" className={buttonVariants({ variant: "ghost", size: "sm" })} data-testid="link-alertas">
                Ver todos
              </Link>
            </CardHeader>
            <CardContent className="space-y-3">
              {!alerts || alerts.total === 0 ? (
                <EmptyBlock label="Nenhuma pendência hoje" testId="painel-alerts-empty" />
              ) : (
                <>
                  <p className="text-sm text-muted-foreground" data-testid="painel-alerts-count">
                    <span className="font-mono font-bold text-foreground">{alerts.total}</span> pendência(s), sendo{" "}
                    <span className="font-mono font-bold text-red-600 dark:text-red-400">{alerts.high}</span> urgente(s).
                  </p>
                  {alerts.alerts.slice(0, 3).map((alert) => (
                    <AlertCard key={`${alert.employee_id}-${alert.kind}-${alert.date}`} alert={alert} />
                  ))}
                </>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex-row items-center justify-between gap-2">
              <CardTitle className="text-base">Solicitações pendentes</CardTitle>
              <Link to="/aprovacoes" className={buttonVariants({ variant: "ghost", size: "sm" })} data-testid="link-aprovacoes">
                Ver todas
              </Link>
            </CardHeader>
            <CardContent className="space-y-3">
              {!pending || pending.length === 0 ? (
                <EmptyBlock label="Nenhuma pendência" testId="pending-queue-empty" />
              ) : (
                pending.slice(0, 2).map((request) => <ApprovalQueueCard key={request.id} request={request} />)
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-base">Resumo do dia</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2 text-sm">
              <div className="flex items-center justify-between">
                <span className="text-muted-foreground">Registros hoje</span>
                <span className="font-mono font-bold" data-testid="summary-today-records">{data?.today_records ?? "—"}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-muted-foreground">Saldo acumulado hoje</span>
                <span className="font-mono font-bold" data-testid="summary-balance">{data?.balance_hhmm ?? "—"}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-muted-foreground">Banco de horas fechado</span>
                <span className="font-mono font-bold" data-testid="summary-hours-bank">{data?.hours_bank_hhmm ?? "—"}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-muted-foreground">Fuso da empresa</span>
                <span className="font-mono">America/Belem</span>
              </div>
            </CardContent>
          </Card>
        </aside>
      </div>
    </AppShell>
  );
}
