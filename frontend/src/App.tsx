import { Navigate, Route, Routes } from "react-router-dom";
import { Loader2 } from "lucide-react";
import { Toaster } from "@/components/ui/sonner";
import { homeFor, useMe } from "@/hooks/useMe";
import type { Role } from "@/lib/types";
import Login from "@/pages/Login";
import Ponto from "@/pages/Ponto";
import Espelho from "@/pages/Espelho";
import Solicitacoes from "@/pages/Solicitacoes";
import Painel from "@/pages/Painel";
import Funcionarios from "@/pages/Funcionarios";
import Jornadas from "@/pages/Jornadas";
import Aprovacoes from "@/pages/Aprovacoes";
import Relatorios from "@/pages/Relatorios";
import Auditoria from "@/pages/Auditoria";
import BancoHoras from "@/pages/BancoHoras";
import Calendario from "@/pages/Calendario";
import Alertas from "@/pages/Alertas";

function FullScreenLoader() {
  return (
    <div className="grid min-h-svh place-items-center bg-background" data-testid="route-loading">
      <Loader2 className="size-6 animate-spin text-muted-foreground" aria-hidden="true" />
      <span className="sr-only">Carregando…</span>
    </div>
  );
}

/** Route guard. The real authorization lives in the backend — this only shapes navigation. */
function Protected({ children, allow }: { children: React.ReactNode; allow?: Role[] }) {
  const { data: me, isLoading, isError } = useMe();
  if (isLoading) return <FullScreenLoader />;
  if (isError || !me) return <Navigate to="/login" replace />;
  if (allow && !allow.includes(me.role)) return <Navigate to={homeFor(me.role)} replace />;
  return <>{children}</>;
}

function RootRedirect() {
  const { data: me, isLoading, isError } = useMe();
  if (isLoading) return <FullScreenLoader />;
  if (isError || !me) return <Navigate to="/login" replace />;
  return <Navigate to={homeFor(me.role)} replace />;
}

const MANAGERS: Role[] = ["super_admin", "admin", "gestor"];
const ADMINS: Role[] = ["super_admin", "admin"];

export default function App() {
  return (
    <>
      <Routes>
        <Route path="/" element={<RootRedirect />} />
        <Route path="/login" element={<Login />} />

        {/* Área do funcionário */}
        <Route path="/ponto" element={<Protected allow={["funcionario"]}><Ponto /></Protected>} />
        <Route path="/solicitacoes" element={<Protected allow={["funcionario"]}><Solicitacoes /></Protected>} />

        {/* Compartilhadas: funcionário vê os seus dados, gestão vê os da equipe */}
        <Route path="/espelho" element={<Protected><Espelho /></Protected>} />
        <Route path="/banco-de-horas" element={<Protected><BancoHoras /></Protected>} />

        {/* Área administrativa */}
        <Route path="/painel" element={<Protected allow={MANAGERS}><Painel /></Protected>} />
        <Route path="/alertas" element={<Protected allow={MANAGERS}><Alertas /></Protected>} />
        <Route path="/funcionarios" element={<Protected allow={MANAGERS}><Funcionarios /></Protected>} />
        <Route path="/aprovacoes" element={<Protected allow={MANAGERS}><Aprovacoes /></Protected>} />
        <Route path="/relatorios" element={<Protected allow={MANAGERS}><Relatorios /></Protected>} />
        <Route path="/auditoria" element={<Protected allow={MANAGERS}><Auditoria /></Protected>} />
        <Route path="/jornadas" element={<Protected allow={ADMINS}><Jornadas /></Protected>} />
        <Route path="/calendario" element={<Protected allow={ADMINS}><Calendario /></Protected>} />

        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
      <Toaster richColors />
    </>
  );
}
