import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { CalendarPlus, Download, Loader2, Trash2 } from "lucide-react";
import { apiDelete, apiGet, apiPost } from "@/lib/api";
import type { Assignment, Employee, Holiday, HolidayImport, Schedule } from "@/lib/types";
import AppShell from "@/components/layout/AppShell";
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
  DialogTrigger,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { EmptyBlock, ErrorBlock, LoadingBlock, errorMessage } from "@/components/States";

const KIND_LABEL: Record<Holiday["kind"], string> = {
  nacional: "Nacional",
  estadual: "Estadual",
  municipal: "Municipal",
  facultativo: "Facultativo",
};

const KIND_STYLE: Record<Holiday["kind"], string> = {
  nacional: "bg-red-100 text-red-900 dark:bg-red-950 dark:text-red-200",
  estadual: "bg-amber-100 text-amber-900 dark:bg-amber-950 dark:text-amber-200",
  municipal: "bg-sky-100 text-sky-900 dark:bg-sky-950 dark:text-sky-200",
  facultativo: "bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300",
};

function br(iso: string): string {
  return iso.split("-").reverse().join("/");
}

function Feriados() {
  const queryClient = useQueryClient();
  const currentYear = new Date().getFullYear();
  const [year, setYear] = useState(String(currentYear));
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState({ date: "", name: "", kind: "municipal" as Holiday["kind"] });

  const { data, isLoading, isError } = useQuery<Holiday[]>({
    queryKey: ["holidays", year],
    queryFn: () => apiGet<Holiday[]>(`/holidays?year=${year}`),
    retry: false,
  });

  const create = useMutation({
    mutationFn: () => apiPost<Holiday>("/holidays", form),
    onSuccess: (holiday) => {
      toast.success(`Feriado "${holiday.name}" cadastrado.`);
      setOpen(false);
      setForm({ date: "", name: "", kind: "municipal" });
      queryClient.invalidateQueries({ queryKey: ["holidays"] });
      queryClient.invalidateQueries({ queryKey: ["timesheet"] });
    },
    onError: (error) => toast.error(errorMessage(error, "Não foi possível cadastrar o feriado.")),
  });

  const importNational = useMutation({
    mutationFn: () => apiPost<HolidayImport>(`/holidays/import-national?year=${year}`),
    onSuccess: (result) => {
      toast.success(
        result.imported
          ? `${result.imported} feriados nacionais importados para ${result.year}.`
          : `Os feriados nacionais de ${result.year} já estavam cadastrados.`,
      );
      queryClient.invalidateQueries({ queryKey: ["holidays"] });
      queryClient.invalidateQueries({ queryKey: ["timesheet"] });
    },
    onError: (error) => toast.error(errorMessage(error, "Não foi possível importar os feriados.")),
  });

  const remove = useMutation({
    mutationFn: (id: string) => apiDelete(`/holidays/${id}`),
    onSuccess: () => {
      toast.success("Feriado removido.");
      queryClient.invalidateQueries({ queryKey: ["holidays"] });
      queryClient.invalidateQueries({ queryKey: ["timesheet"] });
    },
    onError: (error) => toast.error(errorMessage(error, "Não foi possível remover o feriado.")),
  });

  return (
    <div className="space-y-5">
      <Card>
        <CardContent className="flex flex-wrap items-end justify-between gap-4 p-4">
          <div className="space-y-1.5">
            <Label htmlFor="hol-year">Ano</Label>
            <Select value={year} onValueChange={(value: string) => setYear(value)}>
              <SelectTrigger id="hol-year" className="w-36" data-testid="holidays-year-select">
                <SelectValue>{(v) => String(v)}</SelectValue>
              </SelectTrigger>
              <SelectContent>
                {[currentYear - 1, currentYear, currentYear + 1].map((value) => (
                  <SelectItem key={value} value={String(value)}>
                    {value}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="flex flex-wrap gap-2">
            <Button
              variant="outline"
              onClick={() => importNational.mutate()}
              disabled={importNational.isPending}
              data-testid="import-national-holidays-btn"
            >
              {importNational.isPending ? <Loader2 className="size-4 animate-spin" aria-hidden="true" /> : <Download className="size-4" aria-hidden="true" />}
              Importar feriados nacionais
            </Button>
            <Dialog open={open} onOpenChange={setOpen}>
              <DialogTrigger
                render={
                  <Button data-testid="add-holiday-btn">
                    <CalendarPlus className="size-4" aria-hidden="true" /> Novo feriado
                  </Button>
                }
              />
              <DialogContent data-testid="holiday-form-dialog">
                <DialogHeader>
                  <DialogTitle>Cadastrar feriado</DialogTitle>
                  <DialogDescription>
                    Feriados nacionais, estaduais e municipais suspendem a jornada — o dia deixa de contar como falta.
                    Pontos facultativos mantêm a jornada prevista.
                  </DialogDescription>
                </DialogHeader>
                <div className="space-y-4">
                  <div className="space-y-1.5">
                    <Label htmlFor="hol-date">Data</Label>
                    <Input id="hol-date" type="date" value={form.date} onChange={(e) => setForm({ ...form, date: e.target.value })} data-testid="holiday-form-date" />
                  </div>
                  <div className="space-y-1.5">
                    <Label htmlFor="hol-name">Descrição</Label>
                    <Input id="hol-name" placeholder="Aniversário da cidade" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} data-testid="holiday-form-name" />
                  </div>
                  <div className="space-y-1.5">
                    <Label htmlFor="hol-kind">Tipo</Label>
                    <Select value={form.kind} onValueChange={(value: string) => setForm({ ...form, kind: value as Holiday["kind"] })}>
                      <SelectTrigger id="hol-kind" data-testid="holiday-form-kind">
                        <SelectValue>{(v) => KIND_LABEL[v as Holiday["kind"]] ?? "Selecione"}</SelectValue>
                      </SelectTrigger>
                      <SelectContent>
                        {(Object.keys(KIND_LABEL) as Holiday["kind"][]).map((kind) => (
                          <SelectItem key={kind} value={kind}>
                            {KIND_LABEL[kind]}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                </div>
                <DialogFooter>
                  <DialogClose render={<Button variant="outline" data-testid="holiday-form-cancel">Cancelar</Button>} />
                  <Button
                    onClick={() => create.mutate()}
                    disabled={!form.date || form.name.trim().length < 2 || create.isPending}
                    data-testid="holiday-form-submit-btn"
                  >
                    {create.isPending ? <Loader2 className="size-4 animate-spin" aria-hidden="true" /> : null}
                    Cadastrar
                  </Button>
                </DialogFooter>
              </DialogContent>
            </Dialog>
          </div>
        </CardContent>
      </Card>

      {isError ? (
        <ErrorBlock label="Não foi possível carregar o calendário." />
      ) : isLoading ? (
        <LoadingBlock label="Carregando feriados…" />
      ) : !data || data.length === 0 ? (
        <EmptyBlock
          label={`Nenhum feriado cadastrado em ${year}`}
          hint="Use 'Importar feriados nacionais' para começar."
          testId="holidays-empty"
        />
      ) : (
        <div className="rounded-xl border border-border bg-card">
          <Table data-testid="holidays-table">
            <TableHeader>
              <TableRow>
                <TableHead>Data</TableHead>
                <TableHead>Dia da semana</TableHead>
                <TableHead>Descrição</TableHead>
                <TableHead>Tipo</TableHead>
                <TableHead>Efeito na jornada</TableHead>
                <TableHead className="text-right">Ações</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {data.map((holiday) => (
                <TableRow key={holiday.id} data-testid="holiday-row">
                  <TableCell className="font-mono font-semibold">{br(holiday.date)}</TableCell>
                  <TableCell className="text-muted-foreground">{holiday.weekday}</TableCell>
                  <TableCell className="font-semibold" data-testid="holiday-row-name">
                    {holiday.name}
                  </TableCell>
                  <TableCell>
                    <Badge variant="secondary" className={`border-0 font-semibold ${KIND_STYLE[holiday.kind]}`} data-testid="holiday-row-kind">
                      {KIND_LABEL[holiday.kind]}
                    </Badge>
                  </TableCell>
                  <TableCell className="text-sm text-muted-foreground">
                    {holiday.kind === "facultativo" ? "Mantém jornada prevista" : "Suspende a jornada"}
                  </TableCell>
                  <TableCell className="text-right">
                    <Button
                      size="sm"
                      variant="ghost"
                      className="text-destructive hover:bg-destructive/10"
                      onClick={() => remove.mutate(holiday.id)}
                      disabled={remove.isPending}
                      data-testid={`holiday-delete-${holiday.date}`}
                    >
                      <Trash2 className="size-4" aria-hidden="true" /> Remover
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}
    </div>
  );
}

function Escalas() {
  const queryClient = useQueryClient();
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState({ employee_id: "", schedule_id: "", start_date: "", end_date: "", note: "" });

  const { data, isLoading, isError } = useQuery<Assignment[]>({
    queryKey: ["schedule-assignments"],
    queryFn: () => apiGet<Assignment[]>("/schedule-assignments"),
    retry: false,
  });
  const { data: employees } = useQuery<Employee[]>({
    queryKey: ["employees", "ativo"],
    queryFn: () => apiGet<Employee[]>("/employees?status=ativo"),
    retry: false,
  });
  const { data: schedules } = useQuery<Schedule[]>({
    queryKey: ["schedules"],
    queryFn: () => apiGet<Schedule[]>("/schedules"),
    retry: false,
  });

  const create = useMutation({
    mutationFn: () =>
      apiPost<Assignment>("/schedule-assignments", {
        employee_id: form.employee_id,
        schedule_id: form.schedule_id,
        start_date: form.start_date,
        end_date: form.end_date || null,
        note: form.note || null,
      }),
    onSuccess: (assignment) => {
      toast.success(`${assignment.schedule_name} atribuída a ${assignment.employee_name}.`);
      setOpen(false);
      setForm({ employee_id: "", schedule_id: "", start_date: "", end_date: "", note: "" });
      queryClient.invalidateQueries({ queryKey: ["schedule-assignments"] });
      queryClient.invalidateQueries({ queryKey: ["timesheet"] });
    },
    onError: (error) => toast.error(errorMessage(error, "Não foi possível atribuir a escala.")),
  });

  const remove = useMutation({
    mutationFn: (id: string) => apiDelete(`/schedule-assignments/${id}`),
    onSuccess: () => {
      toast.success("Escala removida.");
      queryClient.invalidateQueries({ queryKey: ["schedule-assignments"] });
      queryClient.invalidateQueries({ queryKey: ["timesheet"] });
    },
    onError: (error) => toast.error(errorMessage(error, "Não foi possível remover a escala.")),
  });

  const valid = form.employee_id && form.schedule_id && form.start_date;

  return (
    <div className="space-y-5">
      <div className="flex justify-end">
        <Dialog open={open} onOpenChange={setOpen}>
          <DialogTrigger
            render={
              <Button data-testid="add-assignment-btn">
                <CalendarPlus className="size-4" aria-hidden="true" /> Atribuir escala
              </Button>
            }
          />
          <DialogContent data-testid="assignment-form-dialog">
            <DialogHeader>
              <DialogTitle>Atribuir jornada por período</DialogTitle>
              <DialogDescription>
                A escala vigente no dia tem prioridade sobre a jornada do contrato. Deixe a data final em branco para
                valer até nova atribuição.
              </DialogDescription>
            </DialogHeader>
            <div className="space-y-4">
              <div className="space-y-1.5">
                <Label htmlFor="asg-employee">Funcionário</Label>
                <Select value={form.employee_id || "none"} onValueChange={(value: string) => setForm({ ...form, employee_id: value === "none" ? "" : value })}>
                  <SelectTrigger id="asg-employee" data-testid="assignment-form-employee">
                    <SelectValue>
                      {(v) => (v === "none" ? "Selecione" : (employees ?? []).find((e) => e.id === v)?.name ?? "Selecione")}
                    </SelectValue>
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="none">Selecione</SelectItem>
                    {(employees ?? []).map((employee) => (
                      <SelectItem key={employee.id} value={employee.id}>
                        {employee.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="asg-schedule">Jornada / escala</Label>
                <Select value={form.schedule_id || "none"} onValueChange={(value: string) => setForm({ ...form, schedule_id: value === "none" ? "" : value })}>
                  <SelectTrigger id="asg-schedule" data-testid="assignment-form-schedule">
                    <SelectValue>
                      {(v) => (v === "none" ? "Selecione" : (schedules ?? []).find((s) => s.id === v)?.name ?? "Selecione")}
                    </SelectValue>
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="none">Selecione</SelectItem>
                    {(schedules ?? []).map((schedule) => (
                      <SelectItem key={schedule.id} value={schedule.id}>
                        {schedule.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="grid gap-4 sm:grid-cols-2">
                <div className="space-y-1.5">
                  <Label htmlFor="asg-start">Início</Label>
                  <Input id="asg-start" type="date" value={form.start_date} onChange={(e) => setForm({ ...form, start_date: e.target.value })} data-testid="assignment-form-start" />
                </div>
                <div className="space-y-1.5">
                  <Label htmlFor="asg-end">Fim (opcional)</Label>
                  <Input id="asg-end" type="date" value={form.end_date} onChange={(e) => setForm({ ...form, end_date: e.target.value })} data-testid="assignment-form-end" />
                </div>
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="asg-note">Observação</Label>
                <Input id="asg-note" placeholder="Cobertura de férias, troca de turno…" value={form.note} onChange={(e) => setForm({ ...form, note: e.target.value })} data-testid="assignment-form-note" />
              </div>
            </div>
            <DialogFooter>
              <DialogClose render={<Button variant="outline" data-testid="assignment-form-cancel">Cancelar</Button>} />
              <Button onClick={() => create.mutate()} disabled={!valid || create.isPending} data-testid="assignment-form-submit-btn">
                {create.isPending ? <Loader2 className="size-4 animate-spin" aria-hidden="true" /> : null}
                Atribuir
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>

      {isError ? (
        <ErrorBlock label="Não foi possível carregar as escalas." />
      ) : isLoading ? (
        <LoadingBlock label="Carregando escalas…" />
      ) : !data || data.length === 0 ? (
        <EmptyBlock
          label="Nenhuma escala atribuída"
          hint="Atribua uma jornada por período para cobrir troca de turno ou plantão."
          testId="assignments-empty"
        />
      ) : (
        <div className="rounded-xl border border-border bg-card">
          <Table data-testid="assignments-table">
            <TableHeader>
              <TableRow>
                <TableHead>Funcionário</TableHead>
                <TableHead>Jornada / escala</TableHead>
                <TableHead>Início</TableHead>
                <TableHead>Fim</TableHead>
                <TableHead>Observação</TableHead>
                <TableHead>Situação</TableHead>
                <TableHead className="text-right">Ações</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {data.map((assignment) => (
                <TableRow key={assignment.id} data-testid="assignment-row">
                  <TableCell className="font-semibold">{assignment.employee_name}</TableCell>
                  <TableCell data-testid="assignment-row-schedule">{assignment.schedule_name}</TableCell>
                  <TableCell className="font-mono">{br(assignment.start_date)}</TableCell>
                  <TableCell className="font-mono">{assignment.end_date ? br(assignment.end_date) : "Em vigor"}</TableCell>
                  <TableCell className="text-sm text-muted-foreground">{assignment.note ?? "—"}</TableCell>
                  <TableCell>
                    <Badge
                      variant="secondary"
                      className={`border-0 font-semibold ${
                        assignment.active
                          ? "bg-emerald-100 text-emerald-900 dark:bg-emerald-950 dark:text-emerald-200"
                          : "bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300"
                      }`}
                      data-testid="assignment-row-status"
                    >
                      {assignment.active ? "Vigente" : "Fora do período"}
                    </Badge>
                  </TableCell>
                  <TableCell className="text-right">
                    <Button
                      size="sm"
                      variant="ghost"
                      className="text-destructive hover:bg-destructive/10"
                      onClick={() => remove.mutate(assignment.id)}
                      disabled={remove.isPending}
                      data-testid="assignment-delete-btn"
                    >
                      <Trash2 className="size-4" aria-hidden="true" /> Remover
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}
    </div>
  );
}

export default function Calendario() {
  return (
    <AppShell title="Calendário e Escalas" subtitle="Feriados da empresa e jornadas atribuídas por período">
      <Tabs defaultValue="feriados">
        <TabsList variant="line">
          <TabsTrigger value="feriados" data-testid="calendar-tab-holidays">
            Feriados
          </TabsTrigger>
          <TabsTrigger value="escalas" data-testid="calendar-tab-assignments">
            Escalas
          </TabsTrigger>
        </TabsList>
        <TabsContent value="feriados" className="mt-5">
          <Feriados />
        </TabsContent>
        <TabsContent value="escalas" className="mt-5">
          <Escalas />
        </TabsContent>
      </Tabs>
    </AppShell>
  );
}
