import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { XCircle } from "lucide-react";
import { apiGet, apiPost } from "@/lib/api";
import type { Adjustment } from "@/lib/types";
import AppShell from "@/components/layout/AppShell";
import AdjustmentRequestModal from "@/components/ponto/AdjustmentRequestModal";
import StatusBadge from "@/components/StatusBadge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { EmptyBlock, ErrorBlock, LoadingBlock, errorMessage } from "@/components/States";

export default function Solicitacoes() {
  const queryClient = useQueryClient();
  const { data, isLoading, isError } = useQuery<Adjustment[]>({
    queryKey: ["adjustments", "mine"],
    queryFn: () => apiGet<Adjustment[]>("/adjustment-requests"),
    retry: false,
  });

  const cancel = useMutation({
    mutationFn: (id: string) => apiPost<Adjustment>(`/adjustment-requests/${id}/cancel`),
    onSuccess: () => {
      toast.success("Solicitação cancelada.");
      queryClient.invalidateQueries({ queryKey: ["adjustments"] });
    },
    onError: (error) => toast.error(errorMessage(error, "Não foi possível cancelar a solicitação.")),
  });

  return (
    <AppShell title="Minhas Solicitações" subtitle="Correções de ponto enviadas para aprovação">
      <div className="flex justify-end">
        <AdjustmentRequestModal triggerLabel="Nova solicitação" triggerVariant="default" triggerTestId="new-adjustment-btn" />
      </div>

      {isError ? (
        <ErrorBlock label="Não foi possível carregar suas solicitações." />
      ) : isLoading ? (
        <LoadingBlock label="Carregando solicitações…" />
      ) : !data || data.length === 0 ? (
        <EmptyBlock
          label="Você ainda não fez solicitações"
          hint="Use 'Nova solicitação' quando esquecer de registrar um ponto."
          testId="my-requests-empty"
        />
      ) : (
        <div className="space-y-3">
          {data.map((request) => (
            <Card key={request.id} data-testid="my-request-item">
              <CardContent className="flex flex-wrap items-start justify-between gap-4 p-4">
                <div className="min-w-0 space-y-1">
                  <p className="font-semibold">
                    {request.type_label} ·{" "}
                    <span className="font-mono">{request.target_date.split("-").reverse().join("/")}</span> às{" "}
                    <span className="font-mono">{request.requested_time}</span>
                  </p>
                  <p className="text-sm text-muted-foreground">“{request.reason}”</p>
                  {request.decided_by_name ? (
                    <p className="text-xs text-muted-foreground">
                      Decidido por {request.decided_by_name}
                      {request.decision_note ? ` — ${request.decision_note}` : ""}
                    </p>
                  ) : null}
                </div>
                <div className="flex items-center gap-2">
                  <StatusBadge status={request.status} testId="my-request-status" />
                  {request.status === "pendente" ? (
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => cancel.mutate(request.id)}
                      disabled={cancel.isPending}
                      data-testid="my-request-cancel-btn"
                    >
                      <XCircle className="size-4" aria-hidden="true" /> Cancelar
                    </Button>
                  ) : null}
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </AppShell>
  );
}
