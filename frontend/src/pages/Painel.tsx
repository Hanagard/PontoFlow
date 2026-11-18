import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import {
  Activity, ArrowDownRight, ArrowRight, ArrowUpRight, BellRing, CalendarDays,
  CheckCircle2, Clock3, Search, ShieldAlert, Users, Wallet,
} from "lucide-react";
import { apiGet } from "@/lib/api";
import type { Adjustment, Alerts, Dashboard, LiveBoardRow } from "@/lib/types";
import AppShell from "@/components/layout/AppShell";
import KpiCard from "@/components/KpiCard";
import StatusBadge from "@/components/StatusBadge";
import ApprovalQueueCard from "@/components/admin/ApprovalQueueCard";
import AlertCard from "@/components/admin/AlertCard";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { buttonVariants } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { EmptyBlock, ErrorBlock, LoadingBlock } from "@/components/States";
import { cn } from "@/lib/utils";

const number = (value: number | undefined) => (value ?? 0).toLocaleString("pt-BR");

export default function Painel() {
  const [search, setSearch] = useState("");
  const { data, isLoading, isError } = useQuery<Dashboard>({
    queryKey: ["dashboard"], queryFn: () => apiGet<Dashboard>("/dashboard"),
    retry: false, refetchInterval: 60_000,
  });
  const { data: board } = useQuery<LiveBoardRow[]>({
    queryKey: ["live-board"], queryFn: () => apiGet<LiveBoardRow[]>("/time-records/live"),
    retry: false, refetchInterval: 60_000,
  });
  const { data: pending } = useQuery<Adjustment[]>({
    queryKey: ["adjustments", "pendente"],
    queryFn: () => apiGet<Adjustment[]>("/adjustment-requests?status=pendente"), retry: false,
  });
  const { data: alerts } = useQuery<Alerts>({
    queryKey: ["alerts"], queryFn: () => apiGet<Alerts>("/alerts"),
    retry: false, refetchInterval: 60_000,
  });

  const filteredBoard = useMemo(() => {
    const term = search.trim().toLocaleLowerCase("pt-BR");
    if (!term) return board ?? [];
    return (board ?? []).filter((row) =>
      [row.employee_name, row.department ?? "", row.state].some((value) =>
        value.toLocaleLowerCase("pt-BR").includes(term)),
    );
  }, [board, search]);

  const distribution = useMemo(() => {
    const rows = board ?? [];
    return [
      { label: "Trabalhando", count: rows.filter((row) => row.state === "trabalhando").length, color: "bg-emerald-500" },
      { label: "Intervalo", count: rows.filter((row) => row.state === "intervalo").length, color: "bg-sky-500" },
      { label: "Encerrado", count: rows.filter((row) => row.state === "encerrado").length, color: "bg-slate-400" },
      { label: "Ausente", count: rows.filter((row) => row.state === "ausente").length, color: "bg-rose-500" },
    ];
  }, [board]);
  const totalOnBoard = distribution.reduce((sum, item) => sum + item.count, 0);
  const dateLabel = data?.local_date
    ? new Date(`${data.local_date}T12:00:00`).toLocaleDateString("pt-BR", { weekday: "long", day: "2-digit", month: "long", year: "numeric" })
    : "Acompanhamento em tempo real";

  return (
    <AppShell title="Painel Operacional" subtitle={dateLabel}>
      {isError ? <ErrorBlock label="Não foi possível carregar os indicadores agora." /> : null}

      <section className="relative overflow-hidden rounded-2xl bg-slate-950 px-5 py-6 text-white shadow-sm sm:px-7">
        <div className="pointer-events-none absolute -right-12 -top-24 size-64 rounded-full bg-emerald-400/10 blur-3xl" />
        <div className="relative flex flex-col justify-between gap-5 sm:flex-row sm:items-center">
          <div className="max-w-xl">
            <div className="mb-3 inline-flex items-center gap-2 rounded-full border border-emerald-400/20 bg-emerald-400/10 px-3 py-1 text-xs font-semibold text-emerald-300">
              <span className="size-1.5 animate-pulse rounded-full bg-emerald-400" />
              MONITORAMENTO OPERACIONAL
            </div>
            <h2 className="text-xl font-bold tracking-tight sm:text-2xl">Visão geral da operação</h2>
            <p className="mt-1.5 text-sm text-slate-300">Acompanhe a jornada da equipe, identifique desvios e trate pendências em um só lugar.</p>
          </div>
          <div className="grid grid-cols-2 gap-3 sm:min-w-64">
            <div className="rounded-xl border border-white/10 bg-white/5 p-3">
              <p className="text-xs text-slate-400">Registros hoje</p>
              <p className="mt-1 font-mono text-2xl font-bold">{number(data?.today_records)}</p>
            </div>
            <div className="rounded-xl border border-white/10 bg-white/5 p-3">
              <p className="text-xs text-slate-400">Horas extras</p>
              <p className="mt-1 font-mono text-2xl font-bold">{data?.overtime_hhmm ?? "—"}</p>
            </div>
          </div>
        </div>
        <div className="relative mt-5 flex flex-wrap gap-x-5 gap-y-2 border-t border-white/10 pt-4 text-xs text-slate-300">
          <span className="inline-flex items-center gap-1.5"><Clock3 className="size-3.5 text-emerald-300" /> Atualização automática a cada minuto</span>
          <span className="inline-flex items-center gap-1.5"><CalendarDays className="size-3.5 text-emerald-300" /> Fuso {data?.local_date ? "local da empresa" : "—"}</span>
          {data?.holiday_name ? <span className="text-amber-300">Feriado: {data.holiday_name}</span> : null}
        </div>
      </section>

      <section className="space-y-3">
        <div className="flex items-center justify-between gap-3">
          <div>
            <h2 className="text-base font-bold tracking-tight">Indicadores do dia</h2>
            <p className="text-xs text-muted-foreground">Resumo consolidado da jornada</p>
          </div>
          <span className="text-xs text-muted-foreground">Dados atualizados pela API</span>
        </div>
        <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
          <KpiCard label="Funcionários ativos" value={data?.employees_active ?? "—"} hint="Quadro cadastrado" tone="neutral" testId="admin-kpi-ativos" />
          <KpiCard label="Presentes agora" value={data?.present_now ?? "—"} hint="Em atividade" tone="good" testId="admin-kpi-presentes" />
          <KpiCard label="Em intervalo" value={data?.on_interval ?? "—"} hint="Pausa registrada" tone="info" testId="admin-kpi-intervalo" />
          <KpiCard label="Ausentes" value={data?.absent ?? "—"} hint="Sem entrada hoje" tone="bad" testId="admin-kpi-ausentes" />
          <KpiCard label="Atrasados" value={data?.delayed ?? "—"} hint="Fora da tolerância" tone="warn" testId="admin-kpi-atrasados" />
          <KpiCard label="Jornadas incompletas" value={data?.incomplete_days ?? "—"} hint="Exigem conferência" tone="warn" testId="admin-kpi-incompletas" />
          <KpiCard label="Solicitações" value={data?.pending_requests ?? "—"} hint="Aguardando decisão" tone="warn" testId="admin-kpi-pendentes" />
          <KpiCard label="Saldo do dia" value={data?.balance_hhmm ?? "—"} hint="Saldo acumulado" tone="info" testId="admin-kpi-extras" />
        </div>
      </section>

      <div className="grid grid-cols-1 items-start gap-5 xl:grid-cols-12">
        <section className="space-y-3 xl:col-span-8">
          <div className="flex flex-wrap items-end justify-between gap-3">
            <div>
              <h2 className="text-base font-bold tracking-tight">Equipe em tempo real</h2>
              <p className="text-xs text-muted-foreground">Situação atual das jornadas registradas</p>
            </div>
            <Link to="/funcionarios" className={buttonVariants({ variant: "outline", size: "sm" })}>
              Gerenciar equipe <ArrowRight className="ml-1 size-3.5" />
            </Link>
          </div>
          <Card className="overflow-hidden">
            <div className="flex flex-col gap-3 border-b border-border px-4 py-3 sm:flex-row sm:items-center sm:justify-between">
              <div className="flex items-center gap-2 text-sm font-semibold">
                <Users className="size-4 text-muted-foreground" />
                {board?.length ?? 0} colaborador(es) no quadro
              </div>
              <div className="relative w-full sm:max-w-xs">
                <Search className="absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
                <Input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Buscar nome ou setor..." className="h-9 pl-9" aria-label="Buscar funcionário ou departamento" />
              </div>
            </div>
            {isLoading && !board ? <LoadingBlock label="Carregando quadro do dia…" /> : !board || board.length === 0 ? (
              <EmptyBlock label="Nenhum funcionário ativo" hint="Cadastre funcionários para acompanhar a jornada." testId="live-board-empty" />
            ) : filteredBoard.length === 0 ? (
              <EmptyBlock label="Nenhum resultado encontrado" hint="Tente buscar por outro nome ou departamento." />
            ) : (
              <div className="overflow-x-auto">
                <Table data-testid="live-board-table">
                  <TableHeader>
                    <TableRow className="bg-muted/40">
                      <TableHead>Funcionário</TableHead>
                      <TableHead>Departamento</TableHead>
                      <TableHead>Entrada</TableHead>
                      <TableHead>Saída</TableHead>
                      <TableHead className="text-right">Trabalhado</TableHead>
                      <TableHead>Situação</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {filteredBoard.map((row) => (
                      <TableRow key={row.employee_id} data-testid="live-board-row">
                        <TableCell className="min-w-40 font-semibold">{row.employee_name}</TableCell>
                        <TableCell className="text-muted-foreground">{row.department ?? "—"}</TableCell>
                        <TableCell className="font-mono tabular-nums">{row.entrada ?? "—"}</TableCell>
                        <TableCell className="font-mono tabular-nums">{row.saida ?? "—"}</TableCell>
                        <TableCell className="text-right font-mono font-semibold tabular-nums">{row.worked_hhmm ?? "—"}</TableCell>
                        <TableCell><StatusBadge status={row.state} testId="live-board-state" /></TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            )}
            <div className="flex items-center justify-between border-t border-border bg-muted/20 px-4 py-2.5 text-xs text-muted-foreground">
              <span>Exibindo {filteredBoard.length} de {board?.length ?? 0}</span>
              <span className="inline-flex items-center gap-1"><Activity className="size-3.5" /> Atualização em 60s</span>
            </div>
          </Card>
        </section>

        <aside className="space-y-5 xl:col-span-4">
          <Card>
            <CardHeader className="pb-2">
              <div className="flex items-center justify-between">
                <CardTitle className="text-sm font-bold">Distribuição da equipe</CardTitle>
                <Activity className="size-4 text-muted-foreground" />
              </div>
              <p className="text-xs text-muted-foreground">Composição do quadro atual</p>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex h-3 overflow-hidden rounded-full bg-muted" aria-label="Distribuição por situação">
                {distribution.map((item) => (
                  <div key={item.label} className={cn(item.color, "transition-all")} style={{ width: totalOnBoard ? `${(item.count / totalOnBoard) * 100}%` : "0%" }} title={`${item.label}: ${item.count}`} />
                ))}
              </div>
              <div className="grid grid-cols-2 gap-x-3 gap-y-3">
                {distribution.map((item) => (
                  <div key={item.label} className="flex items-center gap-2">
                    <span className={cn("size-2.5 shrink-0 rounded-full", item.color)} />
                    <span className="min-w-0 flex-1 text-xs text-muted-foreground">{item.label}</span>
                    <span className="font-mono text-sm font-bold tabular-nums">{item.count}</span>
                  </div>
                ))}
              </div>
              <p className="border-t border-border pt-3 text-xs text-muted-foreground">Total de pessoas no quadro: <strong className="text-foreground">{totalOnBoard}</strong></p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex-row items-center justify-between gap-2 pb-2">
              <div className="flex items-center gap-2"><ShieldAlert className="size-4 text-amber-500" /><CardTitle className="text-sm font-bold">Atenção necessária</CardTitle></div>
              <Link to="/alertas" className="text-xs font-semibold text-primary hover:underline">Ver todos</Link>
            </CardHeader>
            <CardContent className="space-y-3">
              {!alerts || alerts.total === 0 ? <EmptyBlock label="Nenhuma pendência hoje" testId="painel-alerts-empty" /> : (
                <>
                  <div className="flex items-center justify-between rounded-lg bg-amber-50 px-3 py-2 dark:bg-amber-950/30">
                    <span className="text-xs font-medium text-amber-900 dark:text-amber-200">{alerts.total} pendência(s) identificada(s)</span>
                    <span className="font-mono text-sm font-bold text-red-600 dark:text-red-400">{alerts.high} urgentes</span>
                  </div>
                  {alerts.alerts.slice(0, 3).map((alert) => <AlertCard key={`${alert.employee_id}-${alert.kind}-${alert.date}`} alert={alert} />)}
                </>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex-row items-center justify-between gap-2 pb-2">
              <div className="flex items-center gap-2"><BellRing className="size-4 text-sky-500" /><CardTitle className="text-sm font-bold">Fila de aprovações</CardTitle></div>
              <Link to="/aprovacoes" className="text-xs font-semibold text-primary hover:underline">Abrir fila</Link>
            </CardHeader>
            <CardContent className="space-y-3">
              {!pending || pending.length === 0 ? <EmptyBlock label="Nenhuma solicitação pendente" testId="pending-queue-empty" /> : pending.slice(0, 2).map((request) => <ApprovalQueueCard key={request.id} request={request} />)}
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-2"><CardTitle className="text-sm font-bold">Resumo operacional</CardTitle></CardHeader>
            <CardContent className="space-y-3">
              <div className="flex items-center justify-between text-sm"><span className="flex items-center gap-2 text-muted-foreground"><CheckCircle2 className="size-4" /> Registros hoje</span><strong className="font-mono">{data?.today_records ?? "—"}</strong></div>
              <div className="flex items-center justify-between text-sm"><span className="flex items-center gap-2 text-muted-foreground"><Wallet className="size-4" /> Banco de horas</span><strong className="font-mono">{data?.hours_bank_hhmm ?? "—"}</strong></div>
              <div className="flex items-center justify-between text-sm"><span className="flex items-center gap-2 text-muted-foreground"><ArrowUpRight className="size-4" /> Horas extras</span><strong className="font-mono">{data?.overtime_hhmm ?? "—"}</strong></div>
              <div className="flex items-center justify-between text-sm"><span className="flex items-center gap-2 text-muted-foreground"><ArrowDownRight className="size-4" /> Saldo do dia</span><strong className="font-mono">{data?.balance_hhmm ?? "—"}</strong></div>
            </CardContent>
          </Card>
        </aside>
      </div>
    </AppShell>
  );
}
