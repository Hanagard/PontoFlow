import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useMutation } from "@tanstack/react-query";
import { Clock, Loader2, LockKeyhole, ShieldCheck } from "lucide-react";
import { apiPost } from "@/lib/api";
import type { Me } from "@/lib/types";
import { beginSession } from "@/lib/session";
import { homeFor } from "@/hooks/useMe";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { errorMessage } from "@/components/States";

const DEMO = [
  { label: "Administrador", email: "admin@pontoflow.com.br", testId: "quick-login-admin-btn" },
  { label: "Gestor", email: "gestor@pontoflow.com.br", testId: "quick-login-gestor-btn" },
  { label: "Funcionário", email: "maria.silva@pontoflow.com.br", testId: "quick-login-funcionario-btn" },
];
const DEMO_PASSWORD = "Ponto@2026";
const DEMO_MODE = import.meta.env.VITE_DEMO_MODE === "true";

export default function Login() {
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [formError, setFormError] = useState<string | null>(null);
  const [clock, setClock] = useState("");

  useEffect(() => {
    const tick = () =>
      setClock(new Date().toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit", timeZone: "America/Belem" }));
    tick();
    const id = window.setInterval(tick, 10_000);
    return () => window.clearInterval(id);
  }, []);

  const login = useMutation({
    mutationFn: (creds: { email: string; password: string }) => apiPost<Me>("/auth/login", creds),
    onSuccess: async (me) => {
      await beginSession();
      navigate(homeFor(me.role), { replace: true });
    },
    onError: (error) => setFormError(errorMessage(error, "Não foi possível entrar. Tente novamente.")),
  });

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    setFormError(null);
    login.mutate({ email: email.trim(), password });
  };

  const quickLogin = (demoEmail: string) => {
    setFormError(null);
    setEmail(demoEmail);
    setPassword(DEMO_PASSWORD);
    login.mutate({ email: demoEmail, password: DEMO_PASSWORD });
  };

  return (
    <div className="min-h-svh lg:grid lg:grid-cols-[1.1fr_1fr]">
      {/* Painel institucional */}
      <aside className="relative flex flex-col justify-between overflow-hidden bg-[#0f172a] p-8 text-white lg:p-12">
        <div className="pointer-events-none absolute -left-20 bottom-0 size-80 rounded-full bg-emerald-500/10 blur-3xl" aria-hidden="true" />
        <div className="relative flex items-center gap-2.5">
          <span className="grid size-9 place-items-center rounded-xl bg-emerald-500 font-mono text-sm font-bold text-emerald-950">PF</span>
          <span className="text-lg font-extrabold tracking-tight">PontoFlow</span>
        </div>
        <div className="relative my-10 max-w-md space-y-5 lg:my-0">
          <p className="font-mono text-5xl font-bold tracking-tight text-sky-300" data-testid="login-clock">
            {clock || "--:--"}
          </p>
          <h2 className="text-3xl font-extrabold leading-tight tracking-tight sm:text-4xl">
            Controle de jornada com horário oficial do servidor.
          </h2>
          <p className="text-sm leading-relaxed text-slate-400">
            Registro de entrada, intervalo e saída em sequência validada, espelho de ponto, solicitações de ajuste com
            aprovação e trilha de auditoria completa — por empresa, com dados isolados.
          </p>
          <ul className="space-y-2 text-sm text-slate-300">
            <li className="flex items-center gap-2">
              <ShieldCheck className="size-4 text-emerald-400" aria-hidden="true" /> Permissões validadas no servidor
            </li>
            <li className="flex items-center gap-2">
              <Clock className="size-4 text-emerald-400" aria-hidden="true" /> Fuso da empresa: America/Belem
            </li>
            <li className="flex items-center gap-2">
              <LockKeyhole className="size-4 text-emerald-400" aria-hidden="true" /> Sessão em cookie httpOnly
            </li>
          </ul>
        </div>
        <p className="relative text-xs text-slate-500">Jornada registrada conforme a configuração da empresa.</p>
      </aside>

      {/* Formulário */}
      <main className="flex items-center justify-center bg-background p-6 sm:p-10">
        <div className="w-full max-w-sm space-y-7">
          <div className="space-y-1.5">
            <h1 className="text-2xl font-extrabold tracking-tight">Acessar o sistema</h1>
            <p className="text-sm text-muted-foreground">Informe suas credenciais corporativas.</p>
          </div>

          <form onSubmit={submit} className="space-y-4" noValidate>
            <div className="space-y-1.5">
              <Label htmlFor="email">E-mail</Label>
              <Input
                id="email"
                type="email"
                autoComplete="username"
                placeholder="nome@empresa.com.br"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                data-testid="login-email-input"
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="password">Senha</Label>
              <Input
                id="password"
                type="password"
                autoComplete="current-password"
                placeholder="••••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                data-testid="login-password-input"
              />
            </div>

            {formError ? (
              <p className="rounded-lg border border-destructive/30 bg-destructive/5 p-3 text-sm text-destructive" role="alert" data-testid="login-error">
                {formError}
              </p>
            ) : null}

            <Button type="submit" className="w-full" size="lg" disabled={login.isPending} data-testid="login-submit-button">
              {login.isPending ? <Loader2 className="size-4 animate-spin" aria-hidden="true" /> : null}
              Entrar
            </Button>
          </form>

          {DEMO_MODE ? (
          <div className="space-y-2.5 rounded-xl border border-dashed border-border bg-card p-4">
            <p className="text-xs font-bold uppercase tracking-wider text-muted-foreground">Acesso de demonstração</p>
            <div className="grid gap-2">
              {DEMO.map((account) => (
                <Button
                  key={account.email}
                  type="button"
                  variant="outline"
                  size="sm"
                  disabled={login.isPending}
                  onClick={() => quickLogin(account.email)}
                  data-testid={account.testId}
                >
                  Entrar como {account.label}
                </Button>
              ))}
            </div>
            <p className="text-[11px] text-muted-foreground">Senha de todos os perfis de demonstração: {DEMO_PASSWORD}</p>
          </div>
          ) : null}
        </div>
      </main>
    </div>
  );
}
