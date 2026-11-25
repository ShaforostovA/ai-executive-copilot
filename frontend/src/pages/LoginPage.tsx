import { useState } from "react";
import type { FormEvent } from "react";
import { Navigate, useNavigate } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";

export function LoginPage() {
  const auth = useAuth();
  const navigate = useNavigate();
  const [organization, setOrganization] = useState("demo");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);

  if (auth.user) return <Navigate to="/" replace />;

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitting(true);
    try {
      await auth.login({ organization_slug: organization, email, password });
      navigate("/", { replace: true });
    } catch {
      setPassword("");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="login-layout">
      <section className="login-card" aria-labelledby="login-heading">
        <div className="brand-mark" aria-hidden="true">AI</div>
        <p className="eyebrow">AI Executive Co-pilot</p>
        <h1 id="login-heading">Вход в рабочее пространство</h1>
        <p className="muted">Серверная сессия хранится в защищенной cookie.</p>
        <form onSubmit={submit}>
          <label htmlFor="organization">Организация</label>
          <input
            id="organization"
            name="organization"
            autoComplete="organization"
            value={organization}
            onChange={(event) => setOrganization(event.target.value)}
            required
          />
          <label htmlFor="email">Email</label>
          <input
            id="email"
            name="email"
            type="email"
            autoComplete="email"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            required
          />
          <label htmlFor="password">Пароль</label>
          <input
            id="password"
            name="password"
            type="password"
            autoComplete="current-password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            required
          />
          {auth.error ? <p className="form-error" role="alert">{auth.error}</p> : null}
          <button className="button button-primary" disabled={submitting} type="submit">
            {submitting ? "Вход…" : "Войти"}
          </button>
        </form>
      </section>
    </main>
  );
}
