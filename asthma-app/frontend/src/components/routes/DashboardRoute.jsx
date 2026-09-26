import { Navigate, Outlet } from "react-router";
import { useAuth } from "../../context/AuthContext";
import { urls } from "../../constants";

// any routes within this route require being logged in
export function DashboardRoute() {
  const { user, token, setupComplete } = useAuth();

  // if not logged in, go to landing
  if (!user || !token) {
    return <Navigate to={urls.landing} replace />;
  }

  // if setup not finished, force them back to setup
  if (!setupComplete) {
    return <Navigate to={urls.setup} replace />;
  }

  // Allowed
  return <Outlet />;
}

export default DashboardRoute;