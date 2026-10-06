import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { Loader2, UserPlus } from "lucide-react";
import { apiGet, apiPatch, apiPost } from "@/lib/api";
import type { Employee, Schedule } from "@/lib/types";
import { useMe } from "@/hooks/useMe";
import AppShell from "@/components/layout/AppShell";
import StatusBadge from "@/components/StatusBadge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
import { Dialog, DialogClose, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { EmptyBlock, ErrorBlock, LoadingBlock, errorMessage } from "@/components/States";

interface FormState {
  name: string;
  cpf: string;
  matricula: string;
  email: string;
  phone: string;
  cargo: string;
  department: string;
  schedule_id: string;
  hired_at: string;
  create_login: boolean;
  login_password: string;
}

const EMPTY_FORM: FormState = {
  name: "",
  cpf: "",
  matricula: "",
  email: "",
  phone: "",
  cargo: "",
  department: "",
  schedule_id: "",
  hired_at: "",
  create_login: false,
  login_password: "",
};

export default function Funcionarios() {
  const queryClient = useQueryClient();
  const { data: me } = useMe();
  const canWrite = me?.role === "admin" || me?.role === "super_admin";

  const [search, setSearch] = useState("");
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState<FormState>(EMPTY_FORM);

  const { data, isLoading, isError } = useQuery<Employee[]>({
    queryKey: ["employees", search],
    queryFn: () => apiGet<Employee[]>(`/employees${search ? `?q=${encodeURIComponent(search)}` : ""}`),
    retry: false,
  });
  const { data: schedules } = useQuery<Schedule[]>({
    queryKey: ["schedules"],
    queryFn: () => apiGet<Schedule[]>("/schedules"),
    retry: false,
  });

  const create = useMutation({
    mutationFn: () =>
      apiPost<Employee>("/employees", {
        name: form.name,
        cpf: form.cpf,
        matricula: form.matricula,
        email: form.email || null,
        phone: form.phone || null,
        cargo: form.cargo || null,
        department: form.department || null,
        schedule_id: form.schedule_id || null,
        hired_at: form.hired_at || null,
        create_login: form.create_login,
        login_password: form.create_login ? form.login_password : null,
      }),
    onSuccess: (employee) => {
      toast.success(`Funcionário ${employee.name} cadastrado.`);
      setOpen(false);
      setForm(EMPTY_FORM);
      queryClient.invalidateQueries({ queryKey: ["employees"] });
      queryClient.invalidateQueries({ queryKey: ["dashboard"] });
    },
    onError: (error) => toast.error(errorMessage(error, "Não foi possível cadastrar o funcionário.")),
  });

  const toggleStatus = useMutation({
    mutationFn: (employee: Employee) =>
      apiPatch<Employee>(`/employees/${employee.id}`, { status: employee.status === "ativo" ? "inativo" : "ativo" }),
    onSuccess: () => {
      toast.success("Situação atualizada.");
      queryClient.invalidateQueries({ queryKey: ["employees"] });
    },
    onError: (error) => toast.error(errorMessage(error, "Não foi possível atualizar a situação.")),
  });

  const valid = form.name.trim().length > 1 && form.cpf.replace(/\D/g, "").length === 11 && form.matricula.trim();

  return (
    <AppShell title="Funcionários" subtitle="Cadastro, jornada e situação da equipe">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <Input
          className="max-w-xs"
          placeholder="Buscar por nome ou matrícula"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          aria-label="Buscar funcionário"
          data-testid="employee-search-input"
        />
        {canWrite ? (
          <Dialog open={open} onOpenChange={setOpen}>
            <DialogTrigger
              render={
                <Button data-testid="add-employee-btn">
                  <UserPlus className="size-4" aria-hidden="true" /> Novo funcionário
                </Button>
              }
            />
            <DialogContent className="max-h-[90svh] overflow-y-auto sm:max-w-2xl" data-testid="employee-form-dialog">
              <DialogHeader>
                <DialogTitle>Cadastrar funcionário</DialogTitle>
                <DialogDescription>O CPF é validado no servidor e exibido de forma mascarada nas listagens.</DialogDescription>
              </DialogHeader>

              <div className="grid gap-4 sm:grid-cols-2">
                <div className="space-y-1.5">
                  <Label htmlFor="f-name">Nome completo</Label>
                  <Input id="f-name" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} data-testid="employee-form-name" />
                </div>
                <div className="space-y-1.5">
                  <Label htmlFor="f-cpf">CPF</Label>
                  <Input id="f-cpf" placeholder="000.000.000-00" value={form.cpf} onChange={(e) => setForm({ ...form, cpf: e.target.value })} data-testid="employee-form-cpf" />
                </div>
                <div className="space-y-1.5">
                  <Label htmlFor="f-matricula">Matrícula</Label>
                  <Input id="f-matricula" value={form.matricula} onChange={(e) => setForm({ ...form, matricula: e.target.value })} data-testid="employee-form-matricula" />
                </div>
                <div className="space-y-1.5">
                  <Label htmlFor="f-email">E-mail</Label>
                  <Input id="f-email" type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} data-testid="employee-form-email" />
                </div>
                <div className="space-y-1.5">
                  <Label htmlFor="f-cargo">Cargo</Label>
                  <Input id="f-cargo" value={form.cargo} onChange={(e) => setForm({ ...form, cargo: e.target.value })} data-testid="employee-form-cargo" />
                </div>
                <div className="space-y-1.5">
                  <Label htmlFor="f-dep">Departamento</Label>
                  <Input id="f-dep" value={form.department} onChange={(e) => setForm({ ...form, department: e.target.value })} data-testid="employee-form-department" />
                </div>
                <div className="space-y-1.5">
                  <Label htmlFor="f-phone">Telefone</Label>
                  <Input id="f-phone" value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} data-testid="employee-form-phone" />
                </div>
                <div className="space-y-1.5">
                  <Label htmlFor="f-hired">Data de admissão</Label>
                  <Input id="f-hired" type="date" value={form.hired_at} onChange={(e) => setForm({ ...form, hired_at: e.target.value })} data-testid="employee-form-hired" />
                </div>
                <div className="space-y-1.5 sm:col-span-2">
                  <Label htmlFor="f-schedule">Jornada</Label>
                  <Select value={form.schedule_id || "none"} onValueChange={(value: string) => setForm({ ...form, schedule_id: value === "none" ? "" : value })}>
                    <SelectTrigger id="f-schedule" data-testid="employee-form-schedule">
                      <SelectValue>
                        {(v) => (v === "none" ? "Sem jornada" : (schedules ?? []).find((s) => s.id === v)?.name ?? "Sem jornada")}
                      </SelectValue>
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="none">Sem jornada</SelectItem>
                      {(schedules ?? []).map((schedule) => (
                        <SelectItem key={schedule.id} value={schedule.id}>
                          {schedule.name}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                <div className="space-y-3 rounded-lg border border-dashed border-border p-3 sm:col-span-2">
                  <div className="flex items-center gap-2">
                    <Checkbox
                      id="f-login"
                      checked={form.create_login}
                      onCheckedChange={(checked) => setForm({ ...form, create_login: checked === true })}
                      data-testid="employee-form-create-login"
                    />
                    <Label htmlFor="f-login">Criar acesso ao sistema para este funcionário</Label>
                  </div>
                  {form.create_login ? (
                    <div className="space-y-1.5">
                      <Label htmlFor="f-password">Senha inicial (mínimo 6 caracteres)</Label>
                      <Input
                        id="f-password"
                        type="password"
                        value={form.login_password}
                        onChange={(e) => setForm({ ...form, login_password: e.target.value })}
                        data-testid="employee-form-password"
                      />
                      <p className="text-xs text-muted-foreground">O acesso usará o e-mail informado acima.</p>
                    </div>
                  ) : null}
                </div>
              </div>

              <DialogFooter>
                <DialogClose render={<Button variant="outline" data-testid="employee-form-cancel">Cancelar</Button>} />
                <Button onClick={() => create.mutate()} disabled={!valid || create.isPending} data-testid="employee-form-submit-btn">
                  {create.isPending ? <Loader2 className="size-4 animate-spin" aria-hidden="true" /> : null}
                  Cadastrar
                </Button>
              </DialogFooter>
            </DialogContent>
          </Dialog>
        ) : null}
      </div>

      {isError ? (
        <ErrorBlock label="Não foi possível carregar os funcionários." />
      ) : isLoading ? (
        <LoadingBlock label="Carregando funcionários…" />
      ) : !data || data.length === 0 ? (
        <EmptyBlock label="Nenhum funcionário encontrado" hint="Cadastre o primeiro funcionário da empresa." testId="employees-empty" />
      ) : (
        <Card className="p-0">
          <CardContent className="p-0">
            <Table data-testid="employees-table">
              <TableHeader>
                <TableRow>
                  <TableHead>Nome</TableHead>
                  <TableHead>Matrícula</TableHead>
                  <TableHead>CPF</TableHead>
                  <TableHead>Cargo</TableHead>
                  <TableHead>Departamento</TableHead>
                  <TableHead>Jornada</TableHead>
                  <TableHead>Situação</TableHead>
                  {canWrite ? <TableHead className="text-right">Ações</TableHead> : null}
                </TableRow>
              </TableHeader>
              <TableBody>
                {data.map((employee) => (
                  <TableRow key={employee.id} data-testid="employee-row">
                    <TableCell className="font-semibold">{employee.name}</TableCell>
                    <TableCell className="font-mono">{employee.matricula}</TableCell>
                    <TableCell className="font-mono text-muted-foreground" data-testid="employee-row-cpf">{employee.cpf_masked}</TableCell>
                    <TableCell>{employee.cargo ?? "—"}</TableCell>
                    <TableCell>{employee.department ?? "—"}</TableCell>
                    <TableCell className="text-sm">{employee.schedule_name ?? "—"}</TableCell>
                    <TableCell>
                      <StatusBadge status={employee.status} testId="employee-row-status" />
                    </TableCell>
                    {canWrite ? (
                      <TableCell className="text-right">
                        <Button
                          size="sm"
                          variant="ghost"
                          onClick={() => toggleStatus.mutate(employee)}
                          disabled={toggleStatus.isPending}
                          data-testid={`employee-toggle-status-${employee.matricula}`}
                        >
                          {employee.status === "ativo" ? "Desativar" : "Ativar"}
                        </Button>
                      </TableCell>
                    ) : null}
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}
    </AppShell>
  );
}
