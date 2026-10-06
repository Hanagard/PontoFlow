import { AlertCircle, Inbox, Loader2 } from "lucide-react";

/** Loading / empty / error states (§18). Never gates the whole page — only the data region. */
export function LoadingBlock({ label = "Carregando…", testId }: { label?: string; testId?: string }) {
  return (
    <div className="flex items-center justify-center gap-2 rounded-xl border border-dashed border-border bg-card/50 p-10 text-sm text-muted-foreground" data-testid={testId ?? "loading-block"}>
      <Loader2 className="size-4 animate-spin" aria-hidden="true" />
      <span role="status">{label}</span>
    </div>
  );
}

export function EmptyBlock({ label, hint, testId }: { label: string; hint?: string; testId?: string }) {
  return (
    <div className="flex flex-col items-center justify-center gap-2 rounded-xl border border-dashed border-border bg-card/50 p-10 text-center" data-testid={testId ?? "empty-block"}>
      <Inbox className="size-6 text-muted-foreground" aria-hidden="true" />
      <p className="text-sm font-semibold">{label}</p>
      {hint ? <p className="max-w-sm text-xs text-muted-foreground">{hint}</p> : null}
    </div>
  );
}

export function ErrorBlock({ label = "Não foi possível carregar os dados agora.", testId }: { label?: string; testId?: string }) {
  return (
    <div className="flex items-center gap-2 rounded-xl border border-destructive/30 bg-destructive/5 p-5 text-sm text-destructive" data-testid={testId ?? "error-block"}>
      <AlertCircle className="size-4 shrink-0" aria-hidden="true" />
      <span role="alert">{label}</span>
    </div>
  );
}

/** Extracts the backend's `detail` message; never shows a stack trace to the user (§25). */
export function errorMessage(error: unknown, fallback = "Não foi possível concluir a ação."): string {
  const body = (error as { body?: unknown })?.body;
  if (body && typeof body === "object" && "detail" in body) {
    const detail = (body as { detail: unknown }).detail;
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail) && detail.length) {
      const first = detail[0] as { msg?: string };
      if (first?.msg) return first.msg;
    }
  }
  return fallback;
}
