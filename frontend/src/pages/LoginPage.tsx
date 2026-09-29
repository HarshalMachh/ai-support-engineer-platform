import { useState, type FormEvent } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { ErrorMessage } from "../components/ErrorMessage";
import { useAuth } from "../hooks/useAuth";
import { homePathForRole } from "../utils/roles";

export function LoginPage() {
  const { login, sessionExpired } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<unknown>(null);
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      const user = await login({ email: email.trim(), password });
      const from = (location.state as { from?: string } | null)?.from;
      navigate(from && from !== "/login" ? from : homePathForRole(user.role), { replace: true });
    } catch (err) {
      setError(err);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="card space-y-4 p-6" aria-label="Login form">
      <h2 className="text-base font-semibold">Sign in</h2>
      {sessionExpired && !error && (
        <p className="rounded-md bg-amber-50 px-3 py-2 text-sm text-amber-800">
          Your session expired. Please sign in again.
        </p>
      )}
      {Boolean(error) && <ErrorMessage error={error} title="Login failed" />}
      <div>
        <label htmlFor="email" className="label">
          Email
        </label>
        <input
          id="email"
          type="email"
          autoComplete="email"
          className="input"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
        />
      </div>
      <div>
        <label htmlFor="password" className="label">
          Password
        </label>
        <input
          id="password"
          type="password"
          autoComplete="current-password"
          className="input"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
        />
      </div>
      <button type="submit" className="btn-primary w-full" disabled={submitting}>
        {submitting ? "Signing in…" : "Sign in"}
      </button>
      <p className="text-center text-sm text-slate-600">
        New customer?{" "}
        <Link to="/register" className="font-medium text-brand-700 hover:underline">
          Create an account
        </Link>
      </p>
    </form>
  );
}
