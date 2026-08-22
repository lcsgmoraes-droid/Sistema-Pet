import { Navigate, useLocation } from "react-router-dom";

import { usePlatformAuth } from "../contexts/PlatformAuthContext";

export default function PlatformProtectedRoute({ children }) {
  const { isAuthenticated, loading } = usePlatformAuth();
  const location = useLocation();

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-slate-950 text-slate-300">
        Validando acesso administrativo...
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/ops/login" replace state={{ from: location.pathname }} />;
  }

  return children;
}
