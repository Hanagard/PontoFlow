import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { Loader2, Lock, LockOpen } from "lucide-react";
import { apiGet, apiPost } from "@/lib/api";
import type { CloseCompetence, Employee, HoursBank, HoursBankBoard } from "@/lib/types";
import { isManager, useMe } from "@/hooks/useMe";
import AppShell from "@/components/layout/AppShell";
import KpiCard from "@/components/KpiCard";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { EmptyBlock, ErrorBlock, LoadingBlock, errorMessage } from "@/components/States";
import { cn } from "@/lib/utils";

const DIRECTION_LABEL = {
  credito: "a receber",
  debito: "a repor",
  zerado: "zerado",
} as const;

function balanceClass(minutes: number): string {
  if (minutes > 0) return "text-emerald-600 dark:text-emerald-400";
  if (minutes < 0) return "text-red-600 dark:text-red-400";
  return "text-foreground";
}

/** Extrato individual: um mês por linha, com o saldo acumulado no topo. */
function Extract({ employeeId, canClose }: { employeeId: string; canClose: boolean }) {
  const queryClient = useQueryClient();
  const [months, setMonths] = useState("6");
  const [confirm, setConfirm] = useState<{ competence: string; label: string; closed: boolean } | null>(null);

  const params = new URLSearchParams({ months });
  if (employeeId) params.set("employee_id", employeeId);

  const { data, isLoading, isError } = useQuery<HoursBank>({
    queryKey: ["hours-bank", employeeId, months],
    queryFn: () => apiGet<HoursBank>(`/hours-bank?${params.toString()}`),
    retry: false,
  });

  const decide = useMutation({
    mutationFn: ({ competence, closed }: { competence: string; closed: boolean }) =>
      apiPost<CloseCompetence>(closed ? "/hours-bank/reopen" : "/hours-bank/close", {
        competence,
        employee_id: employeeId || null,
      }),
    onSuccess: (result) => {
      toast.success(result.reopened ? `${result.label} reaberta.` : `${result.label} fechada — saldo congelado.`);
      setConfirm(null);
      queryClient.invalidateQueries({ queryKey: ["hours-bank"] });
      queryClient.invalidateQueries({ queryKey: ["hours-bank-board"] });
      queryClient.invalidateQueries({ queryKey: ["audit"] });
    },
    onError: (error) => {
      setConfirm(null);
      toast.error(errorMessage(error, "Não foi possível concluir o fechamento."));
    },
  });

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-end gap-3">
        <div className="space-y-1.5">
          <Label htmlFor="bh-months">Período</Label>
          <Select value={months} onValueChange={(value: string) => setMonths(value)}>
            <SelectTrigger id="bh-months" className="w-48" data-testid="hours-bank-months-select">
              <SelectValue>{(v) => `Últimos ${v} meses`}</SelectValue>
            </SelectTrigger>
            <SelectContent>
              {["3", "6", "12", "24"].map((value) => (
                <SelectItem key={value} value={value}>
                  Últimos {value} meses
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </div>

      {data ? (
        <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
          <KpiCard
            label="Saldo acumulado"
            value={data.totals.accumulated_hhmm ?? "00:00"}
            hint={`Direção: ${DIRECTION_LABEL[data.totals.direction]}`}
            tone={data.totals.accumulated_minutes >= 0 ? "good" : "bad"}
            testId="hours-bank-accumulated"
          />
          <KpiCard
            label="A compensar"
            value={data.totals.to_compensate_hhmm ?? "00:00"}
            hint={data.totals.direction === "debito" ? "Horas a repor" : "Horas a receber"}
            tone={data.totals.direction === "debito" ? "bad" : "info"}
            testId="hours-bank-to-compensate"
          />
          <KpiCard label="Créditos" value={data.totals.credit_hhmm ?? "00:00"} tone="good" testId="hours-bank-credit" />
          <KpiCard label="Débitos" value={data.totals.debit_hhmm ?? "00:00"} tone="warn" testId="hours-bank-debit" />
        </div>
      ) : null}

      {isError ? (
        <ErrorBlock label="Não foi possível carregar o banco de horas." />
      ) : isLoading ? (
        <LoadingBlock label="Apurando banco de horas…" />
      ) : !data || data.months.length === 0 ? (
        <EmptyBlock label="Sem competências no período" testId="hours-bank-empty" />
      ) : (
        <div className="rounded-xl border border-border bg-card">
          <Table data-testid="hours-bank-table">
            <TableHeader>
              <TableRow>
                <TableHead>Competência</TableHead>
                <TableHead className="text-right">Trabalhado</TableHead>
                <TableHead className="text-right">Previsto</TableHead>
                <TableHead className="text-right">Saldo do mês</TableHead>
                <TableHead className="text-right">Extras</TableHead>
                <TableHead className="text-right">Faltas</TableHead>
                <TableHead>Situação</TableHead>
                {canClose ? <TableHead className="text-right">Ação</TableHead> : null}
              </TableRow>
            </TableHeader>
            <TableBody>
              {[...data.months].reverse().map((month) => {
                const diverged =
                  month.closed &&
                  month.recalculated_balance_minutes !== null &&
                  month.recalculated_balance_minutes !== month.balance_minutes;
                return (
                  <TableRow key={month.competence} data-testid="hours-bank-row">
                    <TableCell className="font-semibold" data-testid="hours-bank-row-competence">
                      {month.label}
                    </TableCell>
                    <TableCell className="text-right font-mono">{month.worked_hhmm ?? "—"}</TableCell>
                    <TableCell className="text-right font-mono text-muted-foreground">{month.expected_hhmm ?? "—"}</TableCell>
                    <TableCell
                      className={cn("text-right font-mono font-bold", balanceClass(month.balance_minutes))}
                      data-testid="hours-bank-row-balance"
                    >
                      {month.balance_hhmm ?? "—"}
                    </TableCell>
                    <TableCell className="text-right font-mono">{month.overtime_hhmm ?? "—"}</TableCell>
                    <TableCell className="text-right font-mono">{month.faltas}</TableCell>
                    <TableCell>
                      {month.closed ? (
                        <div className="space-y-0.5">
                          <Badge variant="secondary" className="border-0 bg-slate-200 font-semibold text-slate-800 dark:bg-slate-800 dark:text-slate-200" data-testid="hours-bank-row-status">
                            Fechada
                          </Badge>
                          {diverged ? (
                            <p className="text-[11px] font-semibold text-amber-600" data-testid="hours-bank-row-diverged">
                              Recálculo difere do fechado
                            </p>
                          ) : null}
                        </div>
                      ) : (
                        <Badge variant="outline" className="font-semibold" data-testid="hours-bank-row-status">
                          Aberta
                        </Badge>
                      )}
                    </TableCell>
                    {canClose ? (
                      <TableCell className="text-right">
                        <Button
                          size="sm"
                          variant="ghost"
                          onClick={() => setConfirm({ competence: month.competence, label: month.label, closed: month.closed })}
                          data-testid={`hours-bank-toggle-${month.competence}`}
                        >
                          {month.closed ? <LockOpen className="size-4" aria-hidden="true" /> : <Lock className="size-4" aria-hidden="true" />}
                          {month.closed ? "Reabrir" : "Fechar"}
                        </Button>
                      </TableCell>
                    ) : null}
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        </div>
      )}

      {/* Confirmação para ação crítica (§18) */}
      <Dialog open={!!confirm} onOpenChange={(open) => !open && setConfirm(null)}>
        <DialogContent data-testid="hours-bank-confirm-dialog">
          <DialogHeader>
            <DialogTitle>{confirm?.closed ? "Reabrir" : "Fechar"} {confirm?.label}?</DialogTitle>
            <DialogDescription>
              {confirm?.closed
                ? "Ao reabrir, o saldo volta a ser recalculado a partir dos registros atuais. A ação fica registrada na auditoria."
                : employeeId
                  ? "O saldo do mês será congelado para este funcionário. Alterações posteriores em registros antigos não mudam o valor fechado."
                  : "O saldo do mês será congelado para TODOS os funcionários ativos. Alterações posteriores não mudam o valor fechado."}
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <DialogClose render={<Button variant="outline" data-testid="hours-bank-confirm-cancel">Cancelar</Button>} />
            <Button
              onClick={() => confirm && decide.mutate({ competence: confirm.competence, closed: confirm.closed })}
              disabled={decide.isPending}
              data-testid="hours-bank-confirm-submit"
            >
              {decide.isPending ? <Loader2 className="size-4 animate-spin" aria-hidden="true" /> : null}
              {confirm?.closed ? "Reabrir competência" : "Fechar competência"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

/** Quadro da equipe: quanto cada pessoa tem a compensar. */
function Board() {
  const [months, setMonths] = useState("6");
  const { data, isLoading, isError } = useQuery<HoursBankBoard>({
    queryKey: ["hours-bank-board", months],
    queryFn: () => apiGet<HoursBankBoard>(`/hours-bank/board?months=${months}`),
    retry: false,
  });

  return (
    <div className="space-y-5">
      <div className="space-y-1.5">
        <Label htmlFor="board-months">Período considerado</Label>
        <Select value={months} onValueChange={(value: string) => setMonths(value)}>
          <SelectTrigger id="board-months" className="w-48" data-testid="hours-bank-board-months">
            <SelectValue>{(v) => `Últimos ${v} meses`}</SelectValue>
          </SelectTrigger>
          <SelectContent>
            {["3", "6", "12"].map((value) => (
              <SelectItem key={value} value={value}>
                Últimos {value} meses
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {isError ? (
        <ErrorBlock label="Não foi possível carregar o quadro do banco de horas." />
      ) : isLoading ? (
        <LoadingBlock label="Apurando saldos da equipe…" />
      ) : !data || data.rows.length === 0 ? (
        <EmptyBlock label="Nenhum funcionário ativo" testId="hours-bank-board-empty" />
      ) : (
        <div className="rounded-xl border border-border bg-card">
          <Table data-testid="hours-bank-board-table">
            <TableHeader>
              <TableRow>
                <TableHead>Funcionário</TableHead>
                <TableHead>Matrícula</TableHead>
                <TableHead>Departamento</TableHead>
                <TableHead className="text-right">{data.label}</TableHead>
                <TableHead className="text-right">Acumulado</TableHead>
                <TableHead className="text-right">A compensar</TableHead>
                <TableHead>Direção</TableHead>
                <TableHead className="text-right">Meses fechados</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {data.rows.map((row) => (
                <TableRow key={row.employee_id} data-testid="hours-bank-board-row">
                  <TableCell className="font-semibold">{row.employee_name}</TableCell>
                  <TableCell className="font-mono">{row.matricula ?? "—"}</TableCell>
                  <TableCell>{row.department ?? "—"}</TableCell>
                  <TableCell className={cn("text-right font-mono", balanceClass(row.current_balance_minutes))}>
                    {row.current_balance_hhmm ?? "—"}
                  </TableCell>
                  <TableCell
                    className={cn("text-right font-mono font-bold", balanceClass(row.accumulated_minutes))}
                    data-testid="hours-bank-board-row-accumulated"
                  >
                    {row.accumulated_hhmm ?? "—"}
                  </TableCell>
                  <TableCell className="text-right font-mono font-semibold" data-testid="hours-bank-board-row-compensate">
                    {row.to_compensate_hhmm ?? "—"}
                  </TableCell>
                  <TableCell>
                    <Badge
                      variant="secondary"
                      className={cn(
                        "border-0 font-semibold",
                        row.direction === "credito"
                          ? "bg-emerald-100 text-emerald-900 dark:bg-emerald-950 dark:text-emerald-200"
                          : row.direction === "debito"
                            ? "bg-red-100 text-red-900 dark:bg-red-950 dark:text-red-200"
                            : "bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300",
                      )}
                      data-testid="hours-bank-board-row-direction"
                    >
                      {row.direction === "credito" ? "A receber" : row.direction === "debito" ? "A repor" : "Zerado"}
                    </Badge>
                  </TableCell>
                  <TableCell className="text-right font-mono">{row.closed_months}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}
    </div>
  );
}

export default function BancoHoras() {
  const { data: me } = useMe();
  const manager = isManager(me?.role);
  const canClose = me?.role === "admin" || me?.role === "super_admin";
  const [employeeId, setEmployeeId] = useState("");

  const { data: employees } = useQuery<Employee[]>({
    queryKey: ["employees", "ativo"],
    queryFn: () => apiGet<Employee[]>("/employees?status=ativo"),
    retry: false,
    enabled: manager,
  });

  if (!manager) {
    return (
      <AppShell title="Banco de Horas" subtitle="Saldo acumulado por competência">
        <Extract employeeId="" canClose={false} />
      </AppShell>
    );
  }

  return (
    <AppShell title="Banco de Horas" subtitle="Saldo mensal, acumulado e fechamento por competência">
      <Tabs defaultValue="board">
        <TabsList variant="line">
          <TabsTrigger value="board" data-testid="hours-bank-tab-board">
            Quadro da equipe
          </TabsTrigger>
          <TabsTrigger value="extract" data-testid="hours-bank-tab-extract">
            Extrato individual
          </TabsTrigger>
        </TabsList>

        <TabsContent value="board" className="mt-5">
          <Board />
        </TabsContent>

        <TabsContent value="extract" className="mt-5 space-y-5">
          <Card>
            <CardContent className="p-4">
              <div className="max-w-sm space-y-1.5">
                <Label htmlFor="bh-employee">Funcionário</Label>
                <Select value={employeeId || "self"} onValueChange={(value: string) => setEmployeeId(value === "self" ? "" : value)}>
                  <SelectTrigger id="bh-employee" data-testid="hours-bank-employee-select">
                    <SelectValue>
                      {(v) => (v === "self" ? "Selecionar…" : (employees ?? []).find((e) => e.id === v)?.name ?? "Selecionar…")}
                    </SelectValue>
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="self">Selecionar…</SelectItem>
                    {(employees ?? []).map((employee) => (
                      <SelectItem key={employee.id} value={employee.id} data-testid={`hours-bank-employee-option-${employee.matricula}`}>
                        {employee.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </CardContent>
          </Card>
          <Extract employeeId={employeeId} canClose={canClose} />
        </TabsContent>
      </Tabs>
    </AppShell>
  );
}
