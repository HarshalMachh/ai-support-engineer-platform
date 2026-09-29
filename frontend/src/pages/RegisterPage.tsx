import { useState, type ChangeEvent, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import { ErrorMessage } from "../components/ErrorMessage";
import { useAuth } from "../hooks/useAuth";
import { homePathForRole } from "../utils/roles";

export function RegisterPage() {
  const { register } = useAuth();
  const navigate = useNavigate();
  const [form, setForm] = useState({ name: "", email: "", password: "", confirm: "" });
  const [error, setError] = useState<unknown>(null);
  const [validationError, setValidationError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const update = (field: keyof typeof form) => (event: ChangeEvent<HTMLInputElement>) =>
    setForm((current) => ({ ...current, [field]: event.target.value }));

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
    setError(null);
    if (form.password.length < 8) return setValidationError("Password must be at least 8 characters.");
    if (form.password !== form.confirm) return setValidationError("Passwords do not match.");
    setValidationError(null);
    setSubmitting(true);
    try {
      const user = await register({ name: form.name.trim(), email: form.email.trim(), password: form.password });
      navigate(homePathForRole(user.role), { replace: true });
    } catch (err) {
      setError(err);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="card space-y-4 p-6" aria-label="Registration form">
      <h2 className="text-base font-semibold">Create a customer account</h2>
      {validationError && <ErrorMessage message={validationError} title="Check the form" />}
      {Boolean(error) && <ErrorMessage error={error} title="Registration failed" />}
      <div>
        <label htmlFor="name" className="label">Full name</label>
        <input id="name" className="input" value={form.name} onChange={update("name")} required minLength={2} />
      </div>
      <div>
        <label htmlFor="email" className="label">Email</label>
        <input id="email" type="email" className="input" value={form.email} onChange={update("email")} required />
      </div>
      <div>
        <label htmlFor="password" className="label">Password</label>
        <input
          id="password"
          type="password"
          autoComplete="new-password"
          className="input"
          value={form.password}
          onChange={update("password")}
          required
        />
      </div>
      <div>
        <label htmlFor="confirm" className="label">Confirm password</label>
        <input
          id="confirm"
          type="password"
          autoComplete="new-password"
          className="input"
          value={form.confirm}
          onChange={update("confirm")}
          required
        />
      </div>
      <button type="submit" className="btn-primary w-full" disabled={submitting}>
        {submitting ? "Creating account…" : "Create account"}
      </button>
      <p className="text-center text-sm text-slate-600">
        Already have an account?{" "}
        <Link to="/login" className="font-medium text-brand-700 hover:underline">Sign in</Link>
      </p>
    </form>
  );
}
