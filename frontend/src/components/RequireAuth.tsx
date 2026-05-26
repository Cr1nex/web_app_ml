import { Navigate, useLocation } from "react-router-dom";
import { isAuthenticated } from "../types";

export default function RequireAuth({ children }: { children: JSX.Element }) {
  const location = useLocation();
  return isAuthenticated() ? (
    children
  ) : (
    <Navigate to="/login" replace state={{ from: location.pathname }} />
  );
}
