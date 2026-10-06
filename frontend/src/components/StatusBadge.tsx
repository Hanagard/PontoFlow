import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

const STATUS_STYLES: Record<string, string> = {
  completa: "bg-emerald-100 text-emerald-900 dark:bg-emerald-950 dark:text-emerald-200",
  incompleta: "bg-amber-100 text-amber-900 dark:bg-amber-950 dark:text-amber-200",
  falta: "bg-red-100 text-red-900 dark:bg-red-950 dark:text-red-200",
  justificada: "bg-sky-100 text-sky-900 dark:bg-sky-950 dark:text-sky-200",
  folga: "bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300",
  feriado: "bg-violet-100 text-violet-900 dark:bg-violet-950 dark:text-violet-200",
  pendente: "bg-amber-100 text-amber-900 dark:bg-amber-950 dark:text-amber-200",
  aprovada: "bg-emerald-100 text-emerald-900 dark:bg-emerald-950 dark:text-emerald-200",
  rejeitada: "bg-red-100 text-red-900 dark:bg-red-950 dark:text-red-200",
  cancelada: "bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300",
  trabalhando: "bg-emerald-100 text-emerald-900 dark:bg-emerald-950 dark:text-emerald-200",
  intervalo: "bg-sky-100 text-sky-900 dark:bg-sky-950 dark:text-sky-200",
  ausente: "bg-red-100 text-red-900 dark:bg-red-950 dark:text-red-200",
  encerrado: "bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300",
  ativo: "bg-emerald-100 text-emerald-900 dark:bg-emerald-950 dark:text-emerald-200",
  inativo: "bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300",
};

const STATUS_LABELS: Record<string, string> = {
  completa: "Completa",
  incompleta: "Incompleta",
  falta: "Falta",
  justificada: "Justificada",
  folga: "Folga",
  feriado: "Feriado",
  pendente: "Pendente",
  aprovada: "Aprovada",
  rejeitada: "Rejeitada",
  cancelada: "Cancelada",
  trabalhando: "Trabalhando",
  intervalo: "Em intervalo",
  ausente: "Ausente",
  encerrado: "Jornada encerrada",
  ativo: "Ativo",
  inativo: "Inativo",
};

export default function StatusBadge({ status, testId }: { status: string; testId?: string }) {
  return (
    <Badge
      variant="secondary"
      data-testid={testId}
      className={cn("border-0 font-semibold", STATUS_STYLES[status] ?? STATUS_STYLES.folga)}
    >
      {STATUS_LABELS[status] ?? status}
    </Badge>
  );
}
