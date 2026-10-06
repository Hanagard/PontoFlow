import { useQuery } from "@tanstack/react-query";
import { apiGet } from "@/lib/api";
import type { Me, Role } from "@/lib/types";

/** "Who am I" — answered by the server from the httpOnly session cookie. */
export function useMe() {
  return useQuery<Me>({
    queryKey: ["me"],
    queryFn: () => apiGet<Me>("/auth/me"),
    retry: false,
    staleTime: 30_000,
  });
}

export const ROLE_LABELS: Record<Role, string> = {
  super_admin: "Super Administrador",
  admin: "Administrador da Empresa",
  gestor: "Gestor",
  funcionario: "Funcionário",
};

export const MANAGER_ROLES: Role[] = ["super_admin", "admin", "gestor"];

export function isManager(role: Role | undefined): boolean {
  return !!role && MANAGER_ROLES.includes(role);
}

/** Landing route per role (§6) — employees go to the punch console, staff to management. */
export function homeFor(role: Role | undefined): string {
  if (!role) return "/login";
  return role === "funcionario" ? "/ponto" : "/painel";
}
