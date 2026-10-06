import { Card, CardContent } from "@/components/ui/card";
import { cn } from "@/lib/utils";

export default function KpiCard({
  label,
  value,
  hint,
  tone = "neutral",
  testId,
}: {
  label: string;
  value: string | number;
  hint?: string;
  tone?: "neutral" | "good" | "warn" | "bad" | "info";
  testId?: string;
}) {
  const tones = {
    neutral: "text-foreground",
    good: "text-emerald-600 dark:text-emerald-400",
    warn: "text-amber-600 dark:text-amber-400",
    bad: "text-red-600 dark:text-red-400",
    info: "text-sky-600 dark:text-sky-400",
  };
  return (
    <Card className="animate-rise border-border/80 shadow-sm transition-shadow duration-200 hover:shadow-md">
      <CardContent className="space-y-1 p-4">
        <p className="text-xs font-bold uppercase tracking-wider text-muted-foreground">{label}</p>
        <p className={cn("font-mono text-2xl font-bold tracking-tight", tones[tone])} data-testid={testId}>
          {value}
        </p>
        {hint ? <p className="text-xs text-muted-foreground">{hint}</p> : null}
      </CardContent>
    </Card>
  );
}
