import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { apiGet } from "@/lib/api";
import type { Adjustment } from "@/lib/types";
import AppShell from "@/components/layout/AppShell";
import ApprovalQueueCard from "@/components/admin/ApprovalQueueCard";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { EmptyBlock, ErrorBlock, LoadingBlock } from "@/components/States";

const TABS = [
  { value: "pendente", label: "Pendentes" },
  { value: "aprovada", label: "Aprovadas" },
  { value: "rejeitada", label: "Rejeitadas" },
];

export default function Aprovacoes() {
  const [tab, setTab] = useState("pendente");
  const { data, isLoading, isError } = useQuery<Adjustment[]>({
    queryKey: ["adjustments", tab],
    queryFn: () => apiGet<Adjustment[]>(`/adjustment-requests?status=${tab}`),
    retry: false,
  });

  return (
    <AppShell title="Solicitações de Ajuste" subtitle="Aprove ou rejeite correções de ponto da equipe">
      <Tabs value={tab} onValueChange={(value: string) => setTab(value)}>
        <TabsList variant="line">
          {TABS.map((item) => (
            <TabsTrigger key={item.value} value={item.value} data-testid={`approvals-tab-${item.value}`}>
              {item.label}
            </TabsTrigger>
          ))}
        </TabsList>

        {TABS.map((item) => (
          <TabsContent key={item.value} value={item.value} className="mt-5 space-y-3">
            {isError ? (
              <ErrorBlock label="Não foi possível carregar as solicitações." />
            ) : isLoading ? (
              <LoadingBlock label="Carregando solicitações…" />
            ) : !data || data.length === 0 ? (
              <EmptyBlock label={`Nenhuma solicitação ${item.label.toLowerCase()}`} testId="approvals-empty" />
            ) : (
              <div className="grid gap-3 lg:grid-cols-2">
                {data.map((request) => (
                  <ApprovalQueueCard key={request.id} request={request} />
                ))}
              </div>
            )}
          </TabsContent>
        ))}
      </Tabs>
    </AppShell>
  );
}
