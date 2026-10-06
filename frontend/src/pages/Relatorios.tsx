import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { apiGet } from "@/lib/api";
import type { Report } from "@/lib/types";
import AppShell from "@/components/layout/AppShell";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { EmptyBlock, ErrorBlock, LoadingBlock } from "@/components/States";

const KINDS: Record<string, string> = {
  espelho: "Espelho por período",
  atrasos: "Relatório de atrasos",
  extras: "Relatório de horas extras",
  faltas: "Relatório de faltas",
  pendencias: "Relatório de pendências",
};

function firstDayOfMonth(): string {
  const now = new Date();
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}-01`;
}

export default function Relatorios() {
  const [kind, setKind] = useState("espelho");
  const [start, setStart] = useState(firstDayOfMonth());
  const [end, setEnd] = useState(new Date().toISOString().slice(0, 10));

  const { data, isLoading, isError } = useQuery<Report>({
    queryKey: ["reports", kind, start, end],
    queryFn: () => apiGet<Report>(`/reports?${new URLSearchParams({ kind, start, end }).toString()}`),
    retry: false,
  });

  return (
    <AppShell title="Relatórios" subtitle="Consolidado por funcionário, calculado no servidor">
      <Card>
        <CardContent className="grid gap-4 p-4 sm:grid-cols-3">
          <div className="space-y-1.5">
            <Label htmlFor="r-kind">Tipo de relatório</Label>
            <Select value={kind} onValueChange={(value: string) => setKind(value)}>
              <SelectTrigger id="r-kind" data-testid="report-kind-select">
                <SelectValue>{(v) => KINDS[v as string] ?? "Selecione"}</SelectValue>
              </SelectTrigger>
              <SelectContent>
                {Object.entries(KINDS).map(([value, label]) => (
                  <SelectItem key={value} value={value} data-testid={`report-kind-${value}`}>
                    {label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="r-start">Início</Label>
            <Input id="r-start" type="date" value={start} onChange={(e) => setStart(e.target.value)} data-testid="report-start-input" />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="r-end">Fim</Label>
            <Input id="r-end" type="date" value={end} onChange={(e) => setEnd(e.target.value)} data-testid="report-end-input" />
          </div>
        </CardContent>
      </Card>

      {isError ? (
        <ErrorBlock label="Não foi possível gerar o relatório. Revise o período." />
      ) : isLoading ? (
        <LoadingBlock label="Gerando relatório…" />
      ) : !data || data.rows.length === 0 ? (
        <EmptyBlock label="Sem dados no período" hint="Altere o período ou cadastre funcionários." testId="report-empty" />
      ) : (
        <div className="rounded-xl border border-border bg-card">
          <Table data-testid="report-table">
            <TableHeader>
              <TableRow>
                <TableHead>Funcionário</TableHead>
                <TableHead>Matrícula</TableHead>
                <TableHead>Departamento</TableHead>
                <TableHead className="text-right">Trabalhado</TableHead>
                <TableHead className="text-right">Previsto</TableHead>
                <TableHead className="text-right">Saldo</TableHead>
                <TableHead className="text-right">Extras</TableHead>
                <TableHead className="text-right">Atrasos</TableHead>
                <TableHead className="text-right">Faltas</TableHead>
                <TableHead className="text-right">Pendências</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {data.rows.map((row) => (
                <TableRow key={row.employee_id} data-testid="report-row">
                  <TableCell className="font-semibold">{row.employee_name}</TableCell>
                  <TableCell className="font-mono">{row.matricula ?? "—"}</TableCell>
                  <TableCell>{row.department ?? "—"}</TableCell>
                  <TableCell className="text-right font-mono">{row.worked_hhmm}</TableCell>
                  <TableCell className="text-right font-mono text-muted-foreground">{row.expected_hhmm}</TableCell>
                  <TableCell
                    className={`text-right font-mono font-bold ${row.balance_hhmm.startsWith("-") ? "text-red-600 dark:text-red-400" : "text-emerald-600 dark:text-emerald-400"}`}
                    data-testid="report-row-balance"
                  >
                    {row.balance_hhmm}
                  </TableCell>
                  <TableCell className="text-right font-mono">{row.overtime_hhmm}</TableCell>
                  <TableCell className="text-right font-mono text-amber-600 dark:text-amber-400">{row.delay_hhmm}</TableCell>
                  <TableCell className="text-right font-mono">{row.faltas}</TableCell>
                  <TableCell className="text-right font-mono">{row.incompletas}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}
    </AppShell>
  );
}
