import { Link } from "react-router-dom";

export function NotFoundPage() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-3 text-center">
      <p className="font-mono text-sm text-slate-400">404</p>
      <h1 className="text-xl font-semibold">Page not found</h1>
      <Link to="/" className="btn-secondary">
        Go home
      </Link>
    </div>
  );
}
