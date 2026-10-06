import { Link, useLocation, useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import {
  Clock,
  LayoutDashboard,
  Users,
  CalendarClock,
  FileCheck2,
  BarChart3,
  ShieldCheck,
  LogOut,
  Menu,
  PiggyBank,
  CalendarDays,
  BellRing,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Sheet, SheetContent, SheetTrigger, SheetTitle, SheetHeader } from "@/components/ui/sheet";
import { Badge } from "@/components/ui/badge";
import { ROLE_LABELS, isManager, useMe } from "@/hooks/useMe";
import { endSession } from "@/lib/session";
import { apiGet } from "@/lib/api";
import { cn } from "@/lib/utils";
import type { Alerts, Me } from "@/lib/types";

interface NavItem {
  to: string;
  label: string;
  icon: typeof Clock;
  badge?: "alerts";
}

function navFor(me: Me | undefined): NavItem[] {
  if (!me) return [];
  if (me.role === "funcionario") {
    return [
      { to: "/ponto", label: "Registrar Ponto", icon: Clock },
      { to: "/espelho", label: "Espelho de Ponto", icon: CalendarClock },
      { to: "/banco-de-horas", label: "Banco de Horas", icon: PiggyBank },
      { to: "/solicitacoes", label: "Minhas Solicitações", icon: FileCheck2 },
    ];
  }
  const items: NavItem[] = [
    { to: "/painel", label: "Painel", icon: LayoutDashboard },
    { to: "/alertas", label: "Alertas", icon: BellRing, badge: "alerts" },
    { to: "/funcionarios", label: "Funcionários", icon: Users },
    { to: "/espelho", label: "Espelho de Ponto", icon: CalendarClock },
    { to: "/banco-de-horas", label: "Banco de Horas", icon: PiggyBank },
    { to: "/aprovacoes", label: "Solicitações", icon: FileCheck2 },
    { to: "/relatorios", label: "Relatórios", icon: BarChart3 },
  ];
  if (me.role !== "gestor") {
    items.push({ to: "/jornadas", label: "Jornadas", icon: Clock });
    items.push({ to: "/calendario", label: "Calendário", icon: CalendarDays });
  }
  items.push({ to: "/auditoria", label: "Auditoria", icon: ShieldCheck });
  return items;
}

function NavLinks({ me, alertCount, onNavigate }: { me: Me | undefined; alertCount: number; onNavigate?: () => void }) {
  const { pathname } = useLocation();
  return (
    <nav className="flex flex-col gap-1" aria-label="Menu principal">
      {navFor(me).map((item) => {
        const active = pathname === item.to;
        const Icon = item.icon;
        const showBadge = item.badge === "alerts" && alertCount > 0;
        return (
          <Link
            key={item.to}
            to={item.to}
            onClick={onNavigate}
            data-testid={`nav-${item.to.replace("/", "")}`}
            aria-current={active ? "page" : undefined}
            className={cn(
              "flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-semibold transition-colors duration-150",
              active
                ? "bg-sidebar-accent text-sidebar-primary"
                : "text-sidebar-foreground/75 hover:bg-sidebar-accent/70 hover:text-sidebar-foreground",
            )}
          >
            <Icon className="size-4 shrink-0" aria-hidden="true" />
            <span className="flex-1">{item.label}</span>
            {showBadge ? (
              <span
                className="grid min-w-5 place-items-center rounded-full bg-red-500 px-1.5 text-[11px] font-bold text-white"
                data-testid="nav-alerts-badge"
                aria-label={`${alertCount} pendências`}
              >
                {alertCount}
              </span>
            ) : null}
          </Link>
        );
      })}
    </nav>
  );
}

function Brand() {
  return (
    <div className="flex items-center gap-2.5">
      <span className="grid size-9 place-items-center rounded-xl bg-sidebar-primary font-mono text-sm font-bold text-sidebar-primary-foreground">
        PF
      </span>
      <span className="text-base font-extrabold tracking-tight text-sidebar-foreground">PontoFlow</span>
    </div>
  );
}

export default function AppShell({ children, title, subtitle }: { children: React.ReactNode; title: string; subtitle?: string }) {
  const { data: me } = useMe();
  const navigate = useNavigate();

  // Contador de pendências no menu — só faz sentido (e só é autorizado) para a gestão.
  const { data: alerts } = useQuery<Alerts>({
    queryKey: ["alerts"],
    queryFn: () => apiGet<Alerts>("/alerts"),
    retry: false,
    enabled: isManager(me?.role),
    refetchInterval: 60_000,
  });
  const alertCount = alerts?.total ?? 0;

  const logout = async () => {
    await endSession();
    navigate("/login", { replace: true });
  };

  return (
    <div className="min-h-svh bg-background lg:flex">
      {/* Desktop sidebar — administração é priorizada no desktop (§31) */}
      <aside className="hidden w-64 shrink-0 flex-col justify-between border-r border-sidebar-border bg-sidebar p-5 lg:flex">
        <div className="space-y-7">
          <Brand />
          <NavLinks me={me} alertCount={alertCount} />
        </div>
        <div className="space-y-3 border-t border-sidebar-border pt-4">
          <div>
            <p className="truncate text-sm font-semibold text-sidebar-foreground" data-testid="sidebar-user-name">
              {me?.name ?? "—"}
            </p>
            <p className="text-xs text-sidebar-foreground/60">{me ? ROLE_LABELS[me.role] : ""}</p>
          </div>
          <Button variant="outline" size="sm" className="w-full border-sidebar-border bg-transparent text-sidebar-foreground hover:bg-sidebar-accent" onClick={logout} data-testid="logout-btn">
            <LogOut className="size-4" aria-hidden="true" /> Sair
          </Button>
        </div>
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
        {/* Mobile header */}
        <header className="flex items-center justify-between gap-3 border-b border-border bg-sidebar px-4 py-3 lg:hidden">
          <Brand />
          <Sheet>
            <SheetTrigger
              render={
                <Button variant="ghost" size="icon" className="relative text-sidebar-foreground hover:bg-sidebar-accent" aria-label="Abrir menu" data-testid="mobile-menu-btn">
                  <Menu className="size-5" aria-hidden="true" />
                  {alertCount > 0 ? (
                    <span className="absolute right-1 top-1 size-2 rounded-full bg-red-500" aria-hidden="true" />
                  ) : null}
                </Button>
              }
            />
            <SheetContent side="left" className="w-72 overflow-y-auto border-sidebar-border bg-sidebar p-5">
              <SheetHeader className="p-0">
                <SheetTitle className="text-sidebar-foreground">Menu</SheetTitle>
              </SheetHeader>
              <div className="mt-6 space-y-6">
                <NavLinks me={me} alertCount={alertCount} />
                <Button variant="outline" size="sm" className="w-full border-sidebar-border bg-transparent text-sidebar-foreground" onClick={logout} data-testid="logout-btn-mobile">
                  <LogOut className="size-4" aria-hidden="true" /> Sair
                </Button>
              </div>
            </SheetContent>
          </Sheet>
        </header>

        <main className="min-w-0 flex-1 px-4 py-6 sm:px-6 lg:px-10 lg:py-9">
          <div className="mx-auto w-full max-w-7xl space-y-7">
            <div className="flex flex-wrap items-end justify-between gap-3">
              <div className="min-w-0">
                <h1 className="text-2xl font-extrabold tracking-tight sm:text-3xl" data-testid="page-title">
                  {title}
                </h1>
                {subtitle ? <p className="mt-1 text-sm text-muted-foreground">{subtitle}</p> : null}
              </div>
              {me ? (
                <Badge variant="secondary" className="font-semibold" data-testid="company-badge">
                  {me.company_name}
                </Badge>
              ) : null}
            </div>
            {children}
          </div>
        </main>
      </div>
    </div>
  );
}
