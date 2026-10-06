import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { Check, Loader2, X } from "lucide-react";
import { apiPatch } from "@/lib/api";
import type { Adjustment } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import StatusBadge from "@/components/StatusBadge";
import { errorMessage } from "@/components/States";

export default function ApprovalQueueCard({ request }: { request: Adjustment }) {
  const queryClient = useQueryClient();
  const [note, setNote] = useState("");

  const decide = useMutation({
    mutationFn: (decision: "aprovada" | "rejeitada") =>
      apiPatch<Adjustment>(`/adjustment-requests/${request.id}`, { decision, note: note || null }),
    onSuccess: (updated) => {
      toast.success(updated.status === "aprovada" ? "Solicitação aprovada e ponto corrigido." : "Solicitação rejeitada.");
      queryClient.invalidateQueries({ queryKey: ["adjustments"] });
      queryClient.invalidateQueries({ queryKey: ["dashboard"] });
      queryClient.invalidateQueries({ queryKey: ["timesheet"] });
      queryClient.invalidateQueries({ queryKey: ["audit"] });
    },
    onError: (error) => toast.error(errorMessage(error, "Não foi possível registrar a decisão.")),
  });

  const pending = request.status === "pendente";

  return (
    <Card className="animate-rise" data-testid="approval-item">
      <CardContent className="space-y-3 p-4">
        <div className="flex flex-wrap items-start justify-between gap-2">
          <div className="min-w-0">
            <p className="font-semibold" data-testid="approval-item-employee">
              {request.employee_name}
            </p>
            <p className="text-sm text-muted-foreground">
              {request.type_label} em{" "}
              <span className="font-mono font-semibold text-foreground">
                {request.target_date.split("-").reverse().join("/")}
              </span>{" "}
              → <span className="font-mono font-semibold text-foreground" data-testid="approval-item-time">{request.requested_time}</span>
              {request.previous_time ? <span className="ml-1 text-xs">(anterior {request.previous_time})</span> : null}
            </p>
          </div>
          <StatusBadge status={request.status} testId="approval-item-status" />
        </div>

        <p className="rounded-lg bg-muted/60 p-3 text-sm" data-testid="approval-item-reason">
          “{request.reason}”
        </p>

        {request.decision_note ? (
          <p className="text-xs text-muted-foreground">Observação da decisão: {request.decision_note}</p>
        ) : null}
        {request.decided_by_name ? (
          <p className="text-xs text-muted-foreground">Decidido por {request.decided_by_name}</p>
        ) : null}

        {pending ? (
          <div className="space-y-2">
            <Input
              placeholder="Observação (opcional)"
              value={note}
              onChange={(e) => setNote(e.target.value)}
              aria-label="Observação da decisão"
              data-testid="approval-item-note-input"
            />
            <div className="flex gap-2">
              <Button
                size="sm"
                className="flex-1 bg-emerald-600 text-white hover:bg-emerald-500"
                disabled={decide.isPending}
                onClick={() => decide.mutate("aprovada")}
                data-testid="approval-item-approve-btn"
              >
                {decide.isPending ? <Loader2 className="size-4 animate-spin" aria-hidden="true" /> : <Check className="size-4" aria-hidden="true" />}
                Aprovar
              </Button>
              <Button
                size="sm"
                variant="outline"
                className="flex-1 border-destructive/40 text-destructive hover:bg-destructive/10"
                disabled={decide.isPending}
                onClick={() => decide.mutate("rejeitada")}
                data-testid="approval-item-reject-btn"
              >
                <X className="size-4" aria-hidden="true" /> Rejeitar
              </Button>
            </div>
          </div>
        ) : null}
      </CardContent>
    </Card>
  );
}
