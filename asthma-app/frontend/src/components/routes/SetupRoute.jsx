import { Navigate, Outlet } from "react-router";
import { useAuth } from "../../context/AuthContext";
import { urls } from "../../constants";

export function SetupRoute() {
  const { user, token, setupComplete } = useAuth();

  // if not logged in, go to landing
  if (!user || !token) {
    return <Navigate to={urls.landing} replace />;
  }

  // if already finished setup, cannot enter setup again
  if (setupComplete) {
    return <Navigate to={urls.home} replace />;
  }

  // Allowed
  return <Outlet />;
}
