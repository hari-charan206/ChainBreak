import { BrowserRouter, Navigate, Route, Routes, useLocation } from "react-router-dom";
import { AuthProvider, useAuth } from "./hooks/useAuth";
import Briefing from "./pages/Briefing";
import Login from "./pages/Login";
import Signup from "./pages/Signup";
import EnvironmentsPage from "./pages/EnvironmentsPage";
import EnvironmentBuilderPage from "./pages/EnvironmentBuilderPage";
import Dashboard from "./pages/Dashboard";

// Route map (build prompt Section 4.3). "/" is public; auth routes are
// public; everything else requires a valid token.
// NOTE: no Lenis/ScrollTrigger here — smooth scroll lives only on the
// Briefing page (Section 3.4).

function RequireAuth({ children }: { children: React.ReactNode }) {
  const { token } = useAuth();
  const location = useLocation();
  if (!token) return <Navigate to="/login" state={{ from: location }} replace />;
  return <>{children}</>;
}

function RedirectIfAuthed({ children }: { children: React.ReactNode }) {
  const { token } = useAuth();
  if (token) return <Navigate to="/environments" replace />;
  return <>{children}</>;
}

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Briefing />} />
          <Route path="/login" element={<RedirectIfAuthed><Login /></RedirectIfAuthed>} />
          <Route path="/signup" element={<RedirectIfAuthed><Signup /></RedirectIfAuthed>} />
          <Route path="/environments" element={<RequireAuth><EnvironmentsPage /></RequireAuth>} />
          <Route path="/environments/new" element={<RequireAuth><EnvironmentBuilderPage /></RequireAuth>} />
          <Route path="/dashboard/:environmentId" element={<RequireAuth><Dashboard /></RequireAuth>} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}
