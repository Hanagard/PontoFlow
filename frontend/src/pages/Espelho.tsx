import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Download, FileText } from "lucide-react";
import { apiGet } from "@/lib/api";
import type { Employee, Timesheet } from "@/lib/types";
import { isManager, useMe } from "@/hooks/useMe";
import AppShell from "@/components/layout/AppShell";
import EspelhoPontoTable from "@/components/ponto/EspelhoPontoTable";
import KpiCard from "@/components/KpiCard";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { EmptyBlock, ErrorBlock, LoadingBlock } from "@/components/States";

const STATUS_OPTIONS: Record<string, string> = {
  todos: "Todos os status",
  completa: "Completa",
  incompleta: "Incompleta",
  falta: "Falta",
  justificada: "Justificada",
  feriado: "Feriado",
  folga: "Folga",
};

function firstDayOfMonth(): string {
  const now = new Date();
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}-01`;
}

function todayIso(): string {
  return new Date().toISOString().slice(0, 10);
}

export default function Espelho() {
  const { data: me } = useMe();
  const manager = isManager(me?.role);

  const [start, setStart] = useState(firstDayOfMonth());
  const [end, setEnd] = useState(todayIso());
  const [status, setStatus] = useState("todos");
  const [employeeId, setEmployeeId] = useState<string>("");

  const { data: employees } = useQuery<Employee[]>({
    queryKey: ["employees", "ativo"],
    queryFn: () => apiGet<Employee[]>("/employees?status=ativo"),
    retry: false,
    enabled: manager,
  });

  const params = new URLSearchParams({ start, end });
  if (status !== "todos") params.set("status", status);
  if (manager && employeeId) params.set("employee_id", employeeId);

  const { data, isLoading, isError } = useQuery<Timesheet>({
    queryKey: ["timesheet", start, end, status, employeeId, manager],
    queryFn: () => apiGet<Timesheet>(`/timesheet?${params.toString()}`),
    retry: false,
  });

  const exportParams = new URLSearchParams({ start, end, ...(manager && employeeId ? { employee_id: employeeId } : {}) }).toString();
  const exportUrl = `/api/timesheet/export?${exportParams}`;
  const pdfUrl = `/api/timesheet/pdf?${exportParams}`;

  return (
    <AppShell
      title="Espelho de Ponto"
      subtitle={data ? `${data.employee_name} · jornada ${data.schedule_name ?? "não configurada"}` : "Selecione o período desejado"}
    >
      <Card>
        <CardContent className="grid gap-4 p-4 sm:grid-cols-2 lg:grid-cols-5">
          <div className="space-y-1.5">
            <Label htmlFor="start">Início</Label>
            <Input id="start" type="date" value={start} onChange={(e) => setStart(e.target.value)} data-testid="espelho-filter-start" />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="end">Fim</Label>
            <Input id="end" type="date" value={end} onChange={(e) => setEnd(e.target.value)} data-testid="espelho-filter-end" />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="status">Status</Label>
            <Select value={status} onValueChange={(value: string) => setStatus(value)}>
              <SelectTrigger id="status" data-testid="espelho-filter-status">
                <SelectValue>{(v) => STATUS_OPTIONS[v as string] ?? "Todos os status"}</SelectValue>
              </SelectTrigger>
              <SelectContent>
                {Object.entries(STATUS_OPTIONS).map(([value, label]) => (
                  <SelectItem key={value} value={value}>
                    {label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          {manager ? (
            <div className="space-y-1.5">
              <Label htmlFor="employee">Funcionário</Label>
              <Select value={employeeId || "self"} onValueChange={(value: string) => setEmployeeId(value === "self" ? "" : value)}>
                <SelectTrigger id="employee" data-testid="espelho-filter-employee">
                  <SelectValue>
                    {(v) => (v === "self" ? "Selecionar…" : (employees ?? []).find((e) => e.id === v)?.name ?? "Selecionar…")}
                  </SelectValue>
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="self">Selecionar…</SelectItem>
                  {(employees ?? []).map((employee) => (
                    <SelectItem key={employee.id} value={employee.id} data-testid={`espelho-employee-option-${employee.matricula}`}>
                      {employee.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          ) : null}
          <div className="flex items-end gap-2 sm:col-span-2 lg:col-span-1">
            <a
              href={pdfUrl}
              className="inline-flex h-9 flex-1 items-center justify-center gap-2 rounded-lg bg-primary px-3 text-sm font-semibold text-primary-foreground transition-opacity duration-150 hover:opacity-90"
              data-testid="export-pdf-btn"
            >
              <FileText className="size-4" aria-hidden="true" /> PDF
            </a>
            <a
              href={exportUrl}
              className="inline-flex h-9 flex-1 items-center justify-center gap-2 rounded-lg border border-input bg-background px-3 text-sm font-semibold transition-colors duration-150 hover:bg-accent hover:text-accent-foreground"
              data-testid="export-report-btn"
            >
              <Download className="size-4" aria-hidden="true" /> CSV
            </a>
          </div>
        </CardContent>
      </Card>

      {data ? (
        <div className="grid grid-cols-2 gap-3 lg:grid-cols-6">
          <KpiCard label="Trabalhado" value={data.summary.total_worked_hhmm ?? "00:00"} testId="espelho-total-worked" />
          <KpiCard label="Previsto" value={data.summary.total_expected_hhmm ?? "00:00"} testId="espelho-total-expected" />
          <KpiCard
            label="Saldo"
            value={data.summary.total_balance_hhmm ?? "00:00"}
            tone={data.summary.total_balance_minutes >= 0 ? "good" : "bad"}
            testId="espelho-total-balance"
          />
          <KpiCard label="Horas extras" value={data.summary.total_overtime_hhmm ?? "00:00"} tone="info" testId="espelho-total-overtime" />
          <KpiCard label="Atrasos" value={data.summary.total_delay_hhmm ?? "00:00"} tone="warn" testId="espelho-total-delay" />
          <KpiCard label="Faltas" value={data.summary.faltas} tone={data.summary.faltas ? "bad" : "neutral"} testId="espelho-total-faltas" />
        </div>
      ) : null}

      {isError ? (
        <ErrorBlock label="Não foi possível carregar o espelho de ponto. Ajuste o período e tente novamente." />
      ) : isLoading ? (
        <LoadingBlock label="Calculando espelho de ponto…" />
      ) : !data || data.days.length === 0 ? (
        <EmptyBlock label="Nenhum dia encontrado" hint="Altere o período ou o filtro de status." testId="espelho-empty" />
      ) : (
        <EspelhoPontoTable data={data} allowRequests={me?.role === "funcionario"} />
      )}
    </AppShell>
  );
}
