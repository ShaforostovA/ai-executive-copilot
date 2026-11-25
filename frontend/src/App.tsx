import { Navigate, Outlet, Route, Routes, useNavigate } from "react-router-dom";
import { useAuth } from "./auth/AuthContext";
import { LoadingState } from "./components/States";
import { DashboardPage } from "./pages/DashboardPage";
import { LoginPage } from "./pages/LoginPage";
import { SourcePage } from "./pages/SourcePage";

function ProtectedLayout() {
  const auth = useAuth();
  const navigate = useNavigate();
  if (auth.loading) return <main className="page-shell"><LoadingState label="Проверяем сессию…" /></main>;
  if (!auth.user) return <Navigate to="/login" replace />;

  async function logout() {
    await auth.logout();
    navigate("/login", { replace: true });
  }

  return (
    <>
      <header className="app-header">
        <a className="brand" href="/">AI Executive Co-pilot</a>
        <div className="account-area">
          <span>{auth.user.email}</span>
          <button className="button button-secondary" onClick={() => void logout()} type="button">
            Выйти
          </button>
        </div>
      </header>
      <main className="page-shell"><Outlet /></main>
    </>
  );
}

export function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route element={<ProtectedLayout />}>
        <Route index element={<DashboardPage />} />
        <Route path="/sources/:sourceId" element={<SourcePage />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
