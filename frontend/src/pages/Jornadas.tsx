import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { CalendarPlus, Loader2 } from "lucide-react";
import { apiGet, apiPost } from "@/lib/api";
import type { Schedule, ScheduleKind } from "@/lib/types";
import AppShell from "@/components/layout/AppShell";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
import { Dialog, DialogClose, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { EmptyBlock, ErrorBlock, LoadingBlock, errorMessage } from "@/components/States";

const WEEKDAYS = [
  { value: 0, label: "Seg" },
  { value: 1, label: "Ter" },
  { value: 2, label: "Qua" },
  { value: 3, label: "Qui" },
  { value: 4, label: "Sex" },
  { value: 5, label: "Sáb" },
  { value: 6, label: "Dom" },
];

const KIND_LABEL: Record<ScheduleKind, string> = {
  fixa: "Fixa (dias da semana)",
  "12x36": "Escala 12x36 (1 dia sim, 1 dia não)",
  "6x1": "Escala 6x1 (6 dias de trabalho, 1 de folga)",
  "5x2": "Escala 5x2 (5 dias de trabalho, 2 de folga)",
};

export default function Jornadas() {
  const queryClient = useQueryClient();
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState({
    name: "",
    entrada: "08:00",
    inicio_intervalo: "12:00",
    fim_intervalo: "13:00",
    saida: "18:00",
    tolerance_minutes: 10,
    work_days: [0, 1, 2, 3, 4] as number[],
    kind: "fixa" as ScheduleKind,
    cycle_anchor: "",
  });

  const { data, isLoading, isError } = useQuery<Schedule[]>({
    queryKey: ["schedules"],
    queryFn: () => apiGet<Schedule[]>("/schedules"),
    retry: false,
  });

  const rotating = form.kind !== "fixa";

  const create = useMutation({
    mutationFn: () =>
      apiPost<Schedule>("/schedules", {
        name: form.name,
        entrada: form.entrada,
        inicio_intervalo: form.inicio_intervalo,
        fim_intervalo: form.fim_intervalo,
        saida: form.saida,
        tolerance_minutes: form.tolerance_minutes,
        work_days: rotating ? [0, 1, 2, 3, 4, 5, 6] : form.work_days,
        kind: form.kind,
        cycle_anchor: rotating ? form.cycle_anchor : null,
      }),
    onSuccess: (schedule) => {
      toast.success(`Jornada "${schedule.name}" criada.`);
      setOpen(false);
      queryClient.invalidateQueries({ queryKey: ["schedules"] });
    },
    onError: (error) => toast.error(errorMessage(error, "Não foi possível criar a jornada.")),
  });

  const toggleDay = (day: number) =>
    setForm((prev) => ({
      ...prev,
      work_days: prev.work_days.includes(day) ? prev.work_days.filter((d) => d !== day) : [...prev.work_days, day].sort(),
    }));

  const valid = form.name.trim().length >= 2 && (!rotating || !!form.cycle_anchor);

  return (
    <AppShell title="Jornadas de Trabalho" subtitle="Horários previstos, tolerância, dias úteis e escalas rotativas">
      <div className="flex justify-end">
        <Dialog open={open} onOpenChange={setOpen}>
          <DialogTrigger
            render={
              <Button data-testid="add-schedule-btn">
                <CalendarPlus className="size-4" aria-hidden="true" /> Nova jornada
              </Button>
            }
          />
          <DialogContent className="max-h-[90svh] overflow-y-auto" data-testid="schedule-form-dialog">
            <DialogHeader>
              <DialogTitle>Nova jornada</DialogTitle>
              <DialogDescription>As regras da jornada são aplicadas no servidor no cálculo do espelho.</DialogDescription>
            </DialogHeader>

            <div className="space-y-4">
              <div className="space-y-1.5">
                <Label htmlFor="j-name">Nome da jornada</Label>
                <Input id="j-name" placeholder="Comercial 08:00 - 18:00" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} data-testid="schedule-form-name" />
              </div>

              <div className="space-y-1.5">
                <Label htmlFor="j-kind">Tipo de jornada</Label>
                <Select value={form.kind} onValueChange={(value: string) => setForm({ ...form, kind: value as ScheduleKind })}>
                  <SelectTrigger id="j-kind" data-testid="schedule-form-kind">
                    <SelectValue>{(v) => KIND_LABEL[v as ScheduleKind] ?? "Selecione"}</SelectValue>
                  </SelectTrigger>
                  <SelectContent>
                    {(Object.keys(KIND_LABEL) as ScheduleKind[]).map((kind) => (
                      <SelectItem key={kind} value={kind} data-testid={`schedule-form-kind-${kind}`}>
                        {KIND_LABEL[kind]}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-1.5">
                  <Label htmlFor="j-entrada">Entrada</Label>
                  <Input id="j-entrada" type="time" value={form.entrada} onChange={(e) => setForm({ ...form, entrada: e.target.value })} data-testid="schedule-form-entrada" />
                </div>
                <div className="space-y-1.5">
                  <Label htmlFor="j-saida">Saída</Label>
                  <Input id="j-saida" type="time" value={form.saida} onChange={(e) => setForm({ ...form, saida: e.target.value })} data-testid="schedule-form-saida" />
                </div>
                <div className="space-y-1.5">
                  <Label htmlFor="j-int-ini">Início do intervalo</Label>
                  <Input id="j-int-ini" type="time" value={form.inicio_intervalo} onChange={(e) => setForm({ ...form, inicio_intervalo: e.target.value })} data-testid="schedule-form-inicio-intervalo" />
                </div>
                <div className="space-y-1.5">
                  <Label htmlFor="j-int-fim">Retorno do intervalo</Label>
                  <Input id="j-int-fim" type="time" value={form.fim_intervalo} onChange={(e) => setForm({ ...form, fim_intervalo: e.target.value })} data-testid="schedule-form-fim-intervalo" />
                </div>
              </div>

              <div className="space-y-1.5">
                <Label htmlFor="j-tol">Tolerância de atraso (minutos)</Label>
                <Input
                  id="j-tol"
                  type="number"
                  min={0}
                  max={120}
                  value={form.tolerance_minutes}
                  onChange={(e) => setForm({ ...form, tolerance_minutes: Number(e.target.value) })}
                  data-testid="schedule-form-tolerance"
                />
              </div>

              {rotating ? (
                <div className="space-y-1.5 rounded-lg border border-dashed border-border p-3">
                  <Label htmlFor="j-anchor">Primeiro dia de trabalho do ciclo</Label>
                  <Input
                    id="j-anchor"
                    type="date"
                    value={form.cycle_anchor}
                    onChange={(e) => setForm({ ...form, cycle_anchor: e.target.value })}
                    data-testid="schedule-form-cycle-anchor"
                  />
                  <p className="text-xs text-muted-foreground">
                    O ciclo é contado a partir desta data, então a escala avança pelos dias da semana como no plantão real.
                  </p>
                </div>
              ) : (
                <div className="space-y-2">
                  <Label>Dias de trabalho</Label>
                  <div className="flex flex-wrap gap-3">
                    {WEEKDAYS.map((day) => (
                      <label key={day.value} className="flex items-center gap-1.5 text-sm">
                        <Checkbox
                          checked={form.work_days.includes(day.value)}
                          onCheckedChange={() => toggleDay(day.value)}
                          data-testid={`schedule-form-day-${day.value}`}
                        />
                        {day.label}
                      </label>
                    ))}
                  </div>
                </div>
              )}
            </div>

            <DialogFooter>
              <DialogClose render={<Button variant="outline" data-testid="schedule-form-cancel">Cancelar</Button>} />
              <Button onClick={() => create.mutate()} disabled={!valid || create.isPending} data-testid="schedule-form-submit-btn">
                {create.isPending ? <Loader2 className="size-4 animate-spin" aria-hidden="true" /> : null}
                Criar jornada
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>

      {isError ? (
        <ErrorBlock label="Não foi possível carregar as jornadas." />
      ) : isLoading ? (
        <LoadingBlock label="Carregando jornadas…" />
      ) : !data || data.length === 0 ? (
        <EmptyBlock label="Nenhuma jornada cadastrada" hint="Crie a jornada padrão da empresa para habilitar o cálculo." testId="schedules-empty" />
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {data.map((schedule) => (
            <Card key={schedule.id} data-testid="schedule-card">
              <CardHeader className="flex-row items-start justify-between gap-2">
                <CardTitle className="text-base">{schedule.name}</CardTitle>
                <Badge variant="outline" className="shrink-0 font-semibold" data-testid="schedule-card-kind">
                  {schedule.kind === "fixa" ? "Fixa" : schedule.kind}
                </Badge>
              </CardHeader>
              <CardContent className="space-y-2 text-sm">
                <div className="grid grid-cols-2 gap-2 font-mono">
                  <span className="text-muted-foreground">Entrada</span>
                  <span className="text-right font-semibold">{schedule.entrada}</span>
                  <span className="text-muted-foreground">Intervalo</span>
                  <span className="text-right font-semibold">
                    {schedule.inicio_intervalo} – {schedule.fim_intervalo}
                  </span>
                  <span className="text-muted-foreground">Saída</span>
                  <span className="text-right font-semibold">{schedule.saida}</span>
                  <span className="text-muted-foreground">Jornada diária</span>
                  <span className="text-right font-semibold" data-testid="schedule-card-expected">{schedule.expected_hhmm ?? "—"}</span>
                </div>
                <p className="text-xs text-muted-foreground">
                  Tolerância de {schedule.tolerance_minutes} min ·{" "}
                  {schedule.kind === "fixa"
                    ? `Dias: ${schedule.work_days.map((d) => WEEKDAYS[d]?.label).join(", ")}`
                    : `Ciclo ${schedule.cycle_on_days}x${schedule.cycle_off_days} desde ${schedule.cycle_anchor?.split("-").reverse().join("/")}`}
                </p>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </AppShell>
  );
}
