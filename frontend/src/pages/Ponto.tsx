import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { CalendarClock, FileCheck2 } from "lucide-react";
import { apiGet } from "@/lib/api";
import type { Adjustment, PunchStatus } from "@/lib/types";
import AppShell from "@/components/layout/AppShell";
import PunchClockHero from "@/components/ponto/PunchClockHero";
import AdjustmentRequestModal from "@/components/ponto/AdjustmentRequestModal";
import StatusBadge from "@/components/StatusBadge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { buttonVariants } from "@/components/ui/button";
import { EmptyBlock } from "@/components/States";

export default function Ponto() {
  const { data: status } = useQuery<PunchStatus>({
    queryKey: ["punch-today"],
    queryFn: () => apiGet<PunchStatus>("/time-records/today"),
    retry: false,
  });
  const { data: requests } = useQuery<Adjustment[]>({
    queryKey: ["adjustments", "mine"],
    queryFn: () => apiGet<Adjustment[]>("/adjustment-requests"),
    retry: false,
  });

  const records = status?.records ?? [];
  const pending = (requests ?? []).filter((r) => r.status === "pendente");

  return (
    <AppShell title="Registrar Ponto" subtitle={status ? `Hoje, ${status.local_date.split("-").reverse().join("/")}` : "Carregando jornada…"}>
      <div className="mx-auto w-full max-w-3xl space-y-6 lg:max-w-none lg:grid lg:grid-cols-12 lg:gap-7 lg:space-y-0">
        <div className="lg:col-span-7">
          <PunchClockHero />
        </div>

        <div className="space-y-6 lg:col-span-5">
          <Card>
            <CardHeader className="flex-row items-center justify-between gap-2">
              <CardTitle className="text-base">Registros de hoje</CardTitle>
              <AdjustmentRequestModal
                defaultDate={status?.local_date}
                triggerLabel="Solicitar correção"
                triggerTestId="ponto-request-adjustment-btn"
              />
            </CardHeader>
            <CardContent>
              {records.length === 0 ? (
                <EmptyBlock
                  label="Nenhum registro hoje"
                  hint="Use o botão REGISTRAR PONTO para marcar sua entrada."
                  testId="today-records-empty"
                />
              ) : (
                <ul className="space-y-2" data-testid="today-records-list">
                  {records.map((record) => (
                    <li
                      key={record.id}
                      className="flex items-center justify-between rounded-lg border border-border bg-card px-3 py-2.5"
                      data-testid="today-record-item"
                    >
                      <div>
                        <p className="text-sm font-semibold">{record.type_label}</p>
                        <p className="text-xs text-muted-foreground">
                          {record.adjusted ? "Ajustado" : "Registro original"} · {record.origin}
                        </p>
                      </div>
                      <span className="font-mono text-lg font-bold">{record.hhmm}</span>
                    </li>
                  ))}
                </ul>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-base">Minhas solicitações pendentes</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              {pending.length === 0 ? (
                <EmptyBlock label="Sem solicitações pendentes" testId="pending-requests-empty" />
              ) : (
                pending.slice(0, 3).map((request) => (
                  <div key={request.id} className="flex items-center justify-between gap-3 rounded-lg border border-border px-3 py-2.5">
                    <div className="min-w-0">
                      <p className="truncate text-sm font-semibold">{request.type_label}</p>
                      <p className="text-xs text-muted-foreground">
                        {request.target_date.split("-").reverse().join("/")} às {request.requested_time}
                      </p>
                    </div>
                    <StatusBadge status={request.status} />
                  </div>
                ))
              )}
              <div className="flex flex-wrap gap-2 pt-1">
                <Link to="/espelho" className={buttonVariants({ variant: "outline", size: "sm" })} data-testid="link-espelho">
                  <CalendarClock className="size-4" aria-hidden="true" /> Espelho de ponto
                </Link>
                <Link to="/solicitacoes" className={buttonVariants({ variant: "outline", size: "sm" })} data-testid="link-solicitacoes">
                  <FileCheck2 className="size-4" aria-hidden="true" /> Minhas solicitações
                </Link>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </AppShell>
  );
}
