import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import StatusBadge from "@/components/StatusBadge";
import AdjustmentRequestModal from "@/components/ponto/AdjustmentRequestModal";
import type { Timesheet } from "@/lib/types";
import { cn } from "@/lib/utils";

/** Espelho de ponto (§15) — presentation only; every number comes from the backend. */
export default function EspelhoPontoTable({ data, allowRequests }: { data: Timesheet; allowRequests: boolean }) {
  return (
    <div className="rounded-xl border border-border bg-card">
      <Table data-testid="espelho-table">
        <TableHeader>
          <TableRow>
            <TableHead>Data</TableHead>
            <TableHead>Entrada</TableHead>
            <TableHead>Saída Int.</TableHead>
            <TableHead>Retorno</TableHead>
            <TableHead>Saída</TableHead>
            <TableHead className="text-right">Total</TableHead>
            <TableHead className="text-right">Previsto</TableHead>
            <TableHead className="text-right">Saldo</TableHead>
            <TableHead>Status</TableHead>
            {allowRequests ? <TableHead className="text-right">Ações</TableHead> : null}
          </TableRow>
        </TableHeader>
        <TableBody>
          {data.days.map((day) => (
            <TableRow key={day.date} data-testid="espelho-row">
              <TableCell className="whitespace-nowrap">
                <span className="font-mono font-semibold">{day.date.split("-").reverse().join("/")}</span>
                <span className="ml-2 text-xs text-muted-foreground">{day.weekday.slice(0, 3)}</span>
              </TableCell>
              <TableCell className="font-mono">{day.entrada.hhmm ?? "—"}</TableCell>
              <TableCell className="font-mono">{day.inicio_intervalo.hhmm ?? "—"}</TableCell>
              <TableCell className="font-mono">{day.fim_intervalo.hhmm ?? "—"}</TableCell>
              <TableCell className="font-mono">{day.saida.hhmm ?? "—"}</TableCell>
              <TableCell className="text-right font-mono font-semibold">{day.worked_hhmm ?? "—"}</TableCell>
              <TableCell className="text-right font-mono text-muted-foreground">{day.expected_hhmm ?? "—"}</TableCell>
              <TableCell
                className={cn(
                  "text-right font-mono font-bold",
                  day.balance_minutes === null
                    ? "text-muted-foreground"
                    : day.balance_minutes > 0
                      ? "text-emerald-600 dark:text-emerald-400"
                      : day.balance_minutes < 0
                        ? "text-red-600 dark:text-red-400"
                        : "text-foreground",
                )}
                data-testid="espelho-row-balance"
              >
                {day.balance_hhmm ?? "—"}
              </TableCell>
              <TableCell>
                <StatusBadge status={day.status} testId="espelho-row-status" />
                {day.holiday_name ? (
                  <p className="mt-0.5 text-[11px] text-muted-foreground" data-testid="espelho-row-holiday">
                    {day.holiday_name}
                  </p>
                ) : null}
              </TableCell>
              {allowRequests ? (
                <TableCell className="text-right">
                  <AdjustmentRequestModal
                    defaultDate={day.date}
                    defaultType={day.entrada.hhmm ? "saida" : "entrada"}
                    triggerLabel="Ajustar"
                    triggerVariant="ghost"
                    triggerTestId={`espelho-request-adjustment-btn-${day.date}`}
                  />
                </TableCell>
              ) : null}
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}
