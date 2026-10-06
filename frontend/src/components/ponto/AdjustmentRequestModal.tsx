import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { Loader2, PlusCircle } from "lucide-react";
import { apiPost } from "@/lib/api";
import type { Adjustment, RecordType } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Dialog, DialogClose, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { errorMessage } from "@/components/States";

const TYPE_LABELS: Record<RecordType, string> = {
  entrada: "Entrada",
  inicio_intervalo: "Saída para Intervalo",
  fim_intervalo: "Retorno do Intervalo",
  saida: "Saída",
};

export default function AdjustmentRequestModal({
  defaultDate,
  defaultType,
  triggerLabel = "Solicitar ajuste",
  triggerVariant = "outline",
  triggerTestId = "espelho-request-adjustment-btn",
}: {
  defaultDate?: string;
  defaultType?: RecordType;
  triggerLabel?: string;
  triggerVariant?: "outline" | "default" | "ghost";
  triggerTestId?: string;
}) {
  const queryClient = useQueryClient();
  const [open, setOpen] = useState(false);
  const [targetDate, setTargetDate] = useState(defaultDate ?? "");
  const [type, setType] = useState<RecordType>(defaultType ?? "entrada");
  const [requestedTime, setRequestedTime] = useState("");
  const [reason, setReason] = useState("");

  const create = useMutation({
    mutationFn: () =>
      apiPost<Adjustment>("/adjustment-requests", {
        target_date: targetDate,
        type,
        requested_time: requestedTime,
        reason,
      }),
    onSuccess: () => {
      toast.success("Solicitação enviada para aprovação.");
      setOpen(false);
      setReason("");
      setRequestedTime("");
      queryClient.invalidateQueries({ queryKey: ["adjustments"] });
      queryClient.invalidateQueries({ queryKey: ["dashboard"] });
    },
    onError: (error) => toast.error(errorMessage(error, "Não foi possível enviar a solicitação.")),
  });

  const valid = targetDate && /^\d{2}:\d{2}$/.test(requestedTime) && reason.trim().length >= 5;

  return (
    <Dialog
      open={open}
      onOpenChange={(next) => {
        setOpen(next);
        if (next) {
          setTargetDate(defaultDate ?? targetDate);
          setType(defaultType ?? type);
        }
      }}
    >
      <DialogTrigger
        render={
          <Button variant={triggerVariant} size="sm" data-testid={triggerTestId}>
            <PlusCircle className="size-4" aria-hidden="true" /> {triggerLabel}
          </Button>
        }
      />
      <DialogContent data-testid="adjustment-modal">
        <DialogHeader>
          <DialogTitle>Solicitar correção de ponto</DialogTitle>
          <DialogDescription>
            O registro só será alterado após aprovação do gestor. O valor anterior fica guardado na auditoria.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-1.5">
              <Label htmlFor="adj-date">Data</Label>
              <Input
                id="adj-date"
                type="date"
                value={targetDate}
                onChange={(e) => setTargetDate(e.target.value)}
                data-testid="adjustment-modal-date-input"
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="adj-time">Horário solicitado</Label>
              <Input
                id="adj-time"
                type="time"
                value={requestedTime}
                onChange={(e) => setRequestedTime(e.target.value)}
                data-testid="adjustment-modal-time-input"
              />
            </div>
          </div>

          <div className="space-y-1.5">
            <Label htmlFor="adj-type">Registro</Label>
            <Select value={type} onValueChange={(value: string) => setType(value as RecordType)}>
              <SelectTrigger id="adj-type" data-testid="adjustment-modal-type-select">
                <SelectValue>{(v) => TYPE_LABELS[v as RecordType] ?? "Selecione"}</SelectValue>
              </SelectTrigger>
              <SelectContent>
                {(Object.keys(TYPE_LABELS) as RecordType[]).map((key) => (
                  <SelectItem key={key} value={key} data-testid={`adjustment-type-option-${key}`}>
                    {TYPE_LABELS[key]}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-1.5">
            <Label htmlFor="adj-reason">Justificativa</Label>
            <Textarea
              id="adj-reason"
              rows={3}
              placeholder="Explique o motivo da correção (mínimo 5 caracteres)."
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              data-testid="adjustment-modal-reason-textarea"
            />
          </div>
        </div>

        <DialogFooter>
          <DialogClose render={<Button variant="outline" data-testid="adjustment-modal-cancel">Cancelar</Button>} />
          <Button onClick={() => create.mutate()} disabled={!valid || create.isPending} data-testid="adjustment-modal-submit-btn">
            {create.isPending ? <Loader2 className="size-4 animate-spin" aria-hidden="true" /> : null}
            Enviar solicitação
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
