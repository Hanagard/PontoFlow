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

  return (
    <div className="min-h-svh lg:grid lg:grid-cols-[1.1fr_1fr]">
      <aside className="relative flex flex-col justify-between overflow-hidden bg-[#0f172a] p-8 text-white lg:p-12">
        <div className="pointer-events-none absolute -left-20 bottom-0 size-80 rounded-full bg-emerald-500/10 blur-3xl" aria-hidden="true" />
        <div className="relative flex items-center gap-2.5">
          <span className="grid size-9 place-items-center rounded-xl bg-emerald-500 font-mono text-sm font-bold text-emerald-950">PF</span>
          <span className="text-lg font-extrabold tracking-tight">PontoFlow</span>
        </div>
        <div className="relative my-10 max-w-md space-y-5 lg:my-0">
          <p className="font-mono text-5xl font-bold tracking-tight text-sky-300" data-testid="login-clock">{clock || "--:--"}</p>
          <h2 className="text-3xl font-extrabold leading-tight tracking-tight sm:text-4xl">
            Controle de jornada com horário oficial do servidor.
          </h2>
          <p className="text-sm leading-relaxed text-slate-400">
            Registro de entrada, intervalo e saída em sequência validada, espelho de ponto, solicitações de ajuste com
            aprovação e trilha de auditoria completa — por empresa, com dados isolados.
          </p>
          <ul className="space-y-2 text-sm text-slate-300">
            <li className="flex items-center gap-2"><ShieldCheck className="size-4 text-emerald-400" aria-hidden="true" /> Permissões validadas no servidor</li>
            <li className="flex items-center gap-2"><Clock className="size-4 text-emerald-400" aria-hidden="true" /> Fuso da empresa: America/Belem</li>
            <li className="flex items-center gap-2"><LockKeyhole className="size-4 text-emerald-400" aria-hidden="true" /> Sessão em cookie httpOnly</li>
          </ul>
        </div>
        <p className="relative text-xs text-slate-500">Jornada registrada conforme a configuração da empresa.</p>
      </aside>
      <main className="flex items-center justify-center bg-background p-6 sm:p-10">
        <div className="w-full max-w-sm space-y-7">
          <div className="space-y-1.5">
            <h1 className="text-2xl font-extrabold tracking-tight">Acessar o sistema</h1>
            <p className="text-sm text-muted-foreground">Informe suas credenciais corporativas.</p>
          </div>
          <form onSubmit={submit} className="space-y-4" noValidate>
            <div className="space-y-1.5">
              <Label htmlFor="email">E-mail</Label>
              <Input id="email" type="email" autoComplete="username" placeholder="nome@empresa.com.br"
                value={email} onChange={(e) => setEmail(e.target.value)} required data-testid="login-email-input" />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="password">Senha</Label>
              <Input id="password" type="password" autoComplete="current-password" placeholder="••••••••"
                value={password} onChange={(e) => setPassword(e.target.value)} required data-testid="login-password-input" />
            </div>
            {formError ? <p className="rounded-lg border border-destructive/30 bg-destructive/5 p-3 text-sm text-destructive"
              role="alert" data-testid="login-error">{formError}</p> : null}
            <Button type="submit" className="w-full" size="lg" disabled={login.isPending} data-testid="login-submit-button">
              {login.isPending ? <Loader2 className="size-4 animate-spin" aria-hidden="true" /> : null}
              Entrar
            </Button>
          </form>
        </div>
      </main>
    </div>
  );
}
