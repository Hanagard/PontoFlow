import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { CheckCircle2, Fingerprint, Loader2, ShieldCheck } from "lucide-react";
import { apiGet, apiPost } from "@/lib/api";
import type { PunchStatus, TimeRecord } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Dialog, DialogClose, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { ErrorBlock, errorMessage } from "@/components/States";

const SLOTS: { type: TimeRecord["type"]; label: string; testId: string }[] = [
  { type: "entrada", label: "Entrada", testId: "timeline-entrada-time" },
  { type: "inicio_intervalo", label: "Saída Int.", testId: "timeline-intervalo-time" },
  { type: "fim_intervalo", label: "Retorno", testId: "timeline-retorno-time" },
  { type: "saida", label: "Saída", testId: "timeline-saida-time" },
];

/** Live clock seeded from the SERVER time and ticked locally — the displayed value is
 *  anchored to the backend, and the punch itself is always timestamped server-side (§9). */
function useServerClock(status: PunchStatus | undefined) {
  const [now, setNow] = useState<Date | null>(null);

  useEffect(() => {
    if (!status) return;
    const serverAtLoad = new Date(status.server_time).getTime();
    const localAtLoad = Date.now();
    const tick = () => setNow(new Date(serverAtLoad + (Date.now() - localAtLoad)));
    tick();
    const id = window.setInterval(tick, 1000);
    return () => window.clearInterval(id);
  }, [status]);

  if (!now || !status) return "--:--:--";
  return now.toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit", second: "2-digit", timeZone: status.timezone });
}

export default function PunchClockHero() {
  const queryClient = useQueryClient();
  const [confirmOpen, setConfirmOpen] = useState(false);

  const { data, isLoading, isError } = useQuery<PunchStatus>({
    queryKey: ["punch-today"],
    queryFn: () => apiGet<PunchStatus>("/time-records/today"),
    retry: false,
    refetchInterval: 60_000,
  });

  const clock = useServerClock(data);

  const punch = useMutation({
    mutationFn: () => apiPost<TimeRecord>("/time-records", {}),
    onSuccess: (record) => {
      setConfirmOpen(false);
      toast.success(`${record.type_label} registrada às ${record.hhmm}`, {
        description: `Comprovante ${record.id.slice(0, 8).toUpperCase()} — horário oficial do servidor.`,
      });
      queryClient.invalidateQueries({ queryKey: ["punch-today"] });
      queryClient.invalidateQueries({ queryKey: ["timesheet"] });
      queryClient.invalidateQueries({ queryKey: ["dashboard"] });
    },
    onError: (error) => {
      setConfirmOpen(false);
      toast.error(errorMessage(error, "Não foi possível registrar o ponto."));
    },
  });

  const done = !!data && data.next_type === null;
  const byType = new Map((data?.records ?? []).map((r) => [r.type, r]));

  return (
    <section className="space-y-4">
      {/* Hero card renders its static shell even if the fetch fails (§4) */}
      <div className="relative overflow-hidden rounded-3xl bg-[#0f172a] p-6 text-white shadow-xl sm:p-8">
        <div className="pointer-events-none absolute -right-16 -top-20 size-56 rounded-full bg-sky-400/10 blur-2xl" aria-hidden="true" />
        <div className="relative space-y-6">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div>
              <p className="text-xs font-bold uppercase tracking-wider text-slate-400">Controle de Ponto</p>
              <p className="mt-1 text-xl font-bold tracking-tight" data-testid="punch-employee-name">
                Olá, {data?.employee_name ?? "—"}
              </p>
              <p className="mt-1 text-sm text-slate-400" data-testid="punch-schedule-label">
                Jornada {data?.schedule_label ?? "não configurada"}
              </p>
            </div>
            <div className="text-right">
              <p
                className="font-mono text-4xl font-bold tracking-tight text-sky-300 sm:text-5xl"
                data-testid="punch-clock-live-time"
                aria-live="off"
              >
                {clock}
              </p>
              <p className="text-xs text-slate-400">
                Horário oficial · {data?.timezone ?? "America/Belem"}
              </p>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-3">
            <span className="inline-flex items-center gap-2 rounded-full bg-white/10 px-3 py-1.5 text-sm font-semibold" data-testid="punch-status-badge">
              <span className={done ? "size-2 rounded-full bg-slate-400" : "size-2 rounded-full bg-emerald-400"} aria-hidden="true" />
              {data?.status_label ?? "Carregando…"}
            </span>
            <span className="inline-flex items-center gap-1.5 text-xs text-slate-400">
              <ShieldCheck className="size-3.5" aria-hidden="true" /> Registro validado pelo servidor
            </span>
          </div>

          <Button
            size="lg"
            disabled={isLoading || isError || done || punch.isPending}
            onClick={() => setConfirmOpen(true)}
            data-testid="punch-clock-action-button"
            className={`h-auto min-h-[140px] w-full flex-col gap-2 rounded-3xl bg-emerald-500 text-lg font-extrabold text-emerald-950 shadow-lg transition-transform duration-150 hover:bg-emerald-400 active:scale-[0.98] disabled:opacity-60 sm:min-h-[160px] ${
              done || isLoading || isError ? "" : "animate-punch-pulse"
            }`}
          >
            {punch.isPending ? (
              <Loader2 className="size-8 animate-spin" aria-hidden="true" />
            ) : done ? (
              <CheckCircle2 className="size-8" aria-hidden="true" />
            ) : (
              <Fingerprint className="size-8" aria-hidden="true" />
            )}
            <span className="text-xl sm:text-2xl">{done ? "JORNADA CONCLUÍDA" : "REGISTRAR PONTO"}</span>
            {!done && data?.next_label ? (
              <span className="text-sm font-semibold text-emerald-900/80" data-testid="punch-next-label">
                Próximo registro: {data.next_label}
              </span>
            ) : null}
          </Button>

          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            {SLOTS.map((slot) => {
              const record = byType.get(slot.type);
              return (
                <div
                  key={slot.type}
                  className={`rounded-2xl border p-3 ${record ? "border-emerald-400/30 bg-emerald-400/10" : "border-white/10 bg-white/5"}`}
                >
                  <p className="text-[11px] font-bold uppercase tracking-wider text-slate-400">{slot.label}</p>
                  <p className="font-mono text-xl font-bold" data-testid={slot.testId}>
                    {record?.hhmm ?? "--:--"}
                  </p>
                </div>
              );
            })}
          </div>

          <div className="flex flex-wrap gap-x-6 gap-y-1 text-sm">
            <p className="text-slate-400">
              Trabalhado hoje: <span className="font-mono font-bold text-white" data-testid="punch-worked-today">{data?.worked_hhmm ?? "00:00"}</span>
            </p>
            <p className="text-slate-400">
              Previsto: <span className="font-mono font-bold text-white" data-testid="punch-expected-today">{data?.expected_hhmm ?? "00:00"}</span>
            </p>
          </div>
        </div>
      </div>

      {isError ? <ErrorBlock label="Não foi possível carregar sua jornada de hoje. Verifique sua conexão e tente novamente." testId="punch-error-block" /> : null}

      {/* Confirmação para ação crítica (§18) */}
      <Dialog open={confirmOpen} onOpenChange={setConfirmOpen}>
        <DialogContent data-testid="punch-confirm-dialog">
          <DialogHeader>
            <DialogTitle>Confirmar registro de {data?.next_label ?? "ponto"}?</DialogTitle>
            <DialogDescription>
              O horário gravado será o horário oficial do servidor no momento da confirmação. Este registro não pode ser
              alterado sem uma solicitação de ajuste aprovada.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <DialogClose render={<Button variant="outline" data-testid="punch-confirm-cancel">Cancelar</Button>} />
            <Button
              onClick={() => punch.mutate()}
              disabled={punch.isPending}
              className="bg-emerald-600 text-white hover:bg-emerald-500"
              data-testid="punch-confirm-submit"
            >
              {punch.isPending ? <Loader2 className="size-4 animate-spin" aria-hidden="true" /> : null}
              Confirmar registro
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </section>
  );
}
