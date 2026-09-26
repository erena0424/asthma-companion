import { Navigate, Outlet } from "react-router";
import { useAuth } from "../../context/AuthContext";
import { urls } from "../../constants";

// any routes within this route required being logged out
export function PublicRoute() {
  const { user, token, setupComplete } = useAuth();

  // if logged in, go to home or setup
  if (user && token) {
    // if already finished setup, go to home
    if (setupComplete) {
      return <Navigate to={urls.home} replace />;
    }
    else {
      return <Navigate to={urls.setup} replace />;
    }
  }

  // Allowed
  return <Outlet />;
}

export default PublicRoute;