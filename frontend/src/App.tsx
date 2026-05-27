import { Navigate, Route, Routes } from "react-router-dom";
import LandingPage from "./components/LandingPage";
import AuthPage from "./components/AuthPage";
import WorkspaceLayout from "./components/WorkspaceLayout";
import WorkspaceHome from "./components/WorkspaceHome";
import GamePage from "./components/GamePage";
import PredictionPage from "./components/PredictionPage";
import RequireAuth from "./components/RequireAuth";

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<LandingPage />} />
      <Route path="/login" element={<AuthPage mode="login" />} />
      <Route path="/signup" element={<AuthPage mode="signup" />} />
      <Route
        path="/app"
        element={
          <RequireAuth>
            <WorkspaceLayout />
          </RequireAuth>
        }
      >
        <Route index element={<WorkspaceHome />} />
        <Route path="game" element={<GamePage />} />
        <Route path="predict" element={<PredictionPage />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
