import { useQuery } from "@tanstack/react-query";
import { apiGet } from "@/lib/api";
import type { Alerts } from "@/lib/types";
import AppShell from "@/components/layout/AppShell";
import AlertCard, { AlertsEmpty } from "@/components/admin/AlertCard";
import KpiCard from "@/components/KpiCard";
import { ErrorBlock, LoadingBlock } from "@/components/States";

export default function Alertas() {
  const { data, isLoading, isError } = useQuery<Alerts>({
    queryKey: ["alerts"],
    queryFn: () => apiGet<Alerts>("/alerts"),
    retry: false,
    refetchInterval: 60_000,
  });

  const high = data?.alerts.filter((a) => a.severity === "alta") ?? [];
  const others = data?.alerts.filter((a) => a.severity !== "alta") ?? [];

  return (
    <AppShell
      title="Alertas de Pendência"
      subtitle={data ? `Situação de hoje, ${data.local_date.split("-").reverse().join("/")}` : "Pendências do dia"}
    >
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <KpiCard label="Total" value={data?.total ?? "—"} testId="alerts-kpi-total" />
        <KpiCard label="Urgentes" value={data?.high ?? "—"} tone="bad" testId="alerts-kpi-high" />
        <KpiCard label="Sem urgência" value={others.length} tone="warn" testId="alerts-kpi-others" />
        <KpiCard
          label="Atualizado às"
          value={data ? new Date(data.server_time).toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit", timeZone: "America/Belem" }) : "—"}
          hint="Horário do servidor"
          testId="alerts-kpi-updated"
        />
      </div>

      {isError ? (
        <ErrorBlock label="Não foi possível carregar os alertas." />
      ) : isLoading ? (
        <LoadingBlock label="Verificando pendências do dia…" />
      ) : !data || data.total === 0 ? (
        <AlertsEmpty />
      ) : (
        <div className="space-y-6">
          {high.length ? (
            <section className="space-y-3">
              <h2 className="text-lg font-bold tracking-tight">Precisam de ação hoje</h2>
              <div className="space-y-3">
                {high.map((alert) => (
                  <AlertCard key={`${alert.employee_id}-${alert.kind}-${alert.date}`} alert={alert} />
                ))}
              </div>
            </section>
          ) : null}

          {others.length ? (
            <section className="space-y-3">
              <h2 className="text-lg font-bold tracking-tight">Acompanhar</h2>
              <div className="space-y-3">
                {others.map((alert) => (
                  <AlertCard key={`${alert.employee_id}-${alert.kind}-${alert.date}`} alert={alert} />
                ))}
              </div>
            </section>
          ) : null}
        </div>
      )}
    </AppShell>
  );
}
