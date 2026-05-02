import type { ReactNode } from "react";
import { Navigate } from "react-router-dom";
import { useAuth } from "@/lib/auth";
import type { UserRole } from "@/lib/types";

/** Renders children only if the current user has one of `allowed` roles.
 * Otherwise redirects home. Pair with <ProtectedRoute> which handles auth. */
export function RequireRole({
  allowed,
  children,
}: {
  allowed: UserRole[];
  children: ReactNode;
}) {
  const { user } = useAuth();
  if (!user) return null;
  if (!allowed.includes(user.role)) {
    return <Navigate to="/" replace />;
  }
  return <>{children}</>;
}
