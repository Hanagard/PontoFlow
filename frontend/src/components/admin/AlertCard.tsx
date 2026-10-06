import { Link } from "react-router-dom";
import type { Alert } from "@/lib/types";
import { AlertTriangle, BellRing, CheckCircle2, Clock3, FileClock } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { buttonVariants } from "@/components/ui/button";
import { cn } from "@/lib/utils";

const ICONS: Record<Alert["kind"], typeof BellRing> = {
  saida_nao_registrada: AlertTriangle,
  sem_registro: BellRing,
  intervalo_aberto: Clock3,
  jornada_incompleta: Clock3,
  solicitacao_pendente: FileClock,
};

const SEVERITY: Record<Alert["severity"], { label: string; cls: string; dot: string }> = {
  alta: {
    label: "Alta",
    cls: "border-red-200 bg-red-50 dark:border-red-900/60 dark:bg-red-950/40",
    dot: "bg-red-500",
  },
  media: {
    label: "Média",
    cls: "border-amber-200 bg-amber-50 dark:border-amber-900/60 dark:bg-amber-950/40",
    dot: "bg-amber-500",
  },
  baixa: {
    label: "Baixa",
    cls: "border-border bg-card",
    dot: "bg-slate-400",
  },
};

/** Uma pendência do dia. O alerta desaparece sozinho quando o ponto que falta é registrado. */
export default function AlertCard({ alert }: { alert: Alert }) {
  const Icon = ICONS[alert.kind];
  const tone = SEVERITY[alert.severity];
  const isRequest = alert.kind === "solicitacao_pendente";

  return (
    <div className={cn("flex items-start gap-3 rounded-xl border p-4 transition-shadow duration-150 hover:shadow-sm", tone.cls)} data-testid="alert-card">
      <span className={cn("mt-1 grid size-8 shrink-0 place-items-center rounded-lg text-white", tone.dot)} aria-hidden="true">
        <Icon className="size-4" />
      </span>
      <div className="min-w-0 flex-1 space-y-1">
        <div className="flex flex-wrap items-center gap-2">
          <p className="font-semibold" data-testid="alert-card-title">
            {alert.title}
          </p>
          <Badge variant="outline" className="text-[11px] font-bold" data-testid="alert-card-severity">
            {tone.label}
          </Badge>
        </div>
        <p className="text-sm font-semibold text-foreground/90" data-testid="alert-card-employee">
          {alert.employee_name}
          {alert.department ? <span className="ml-1 font-normal text-muted-foreground">· {alert.department}</span> : null}
        </p>
        <p className="text-sm text-muted-foreground" data-testid="alert-card-detail">
          {alert.detail}
        </p>
      </div>
      <Link
        to={isRequest ? "/aprovacoes" : `/espelho?employee_id=${alert.employee_id}`}
        className={cn(buttonVariants({ variant: "outline", size: "sm" }), "shrink-0")}
        data-testid="alert-card-action"
      >
        {isRequest ? "Decidir" : "Ver espelho"}
      </Link>
    </div>
  );
}

export function AlertsEmpty() {
  return (
    <div className="flex flex-col items-center gap-2 rounded-xl border border-dashed border-emerald-300 bg-emerald-50/60 p-10 text-center dark:border-emerald-900 dark:bg-emerald-950/30" data-testid="alerts-empty">
      <CheckCircle2 className="size-6 text-emerald-600" aria-hidden="true" />
      <p className="text-sm font-semibold">Nenhuma pendência hoje</p>
      <p className="text-xs text-muted-foreground">Todos os registros do dia estão em ordem.</p>
    </div>
  );
}
