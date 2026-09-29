interface LoadingSpinnerProps {
  label?: string;
  size?: "sm" | "md";
  className?: string;
}

export function LoadingSpinner({ label = "Loading…", size = "md", className = "" }: LoadingSpinnerProps) {
  const dimension = size === "sm" ? "h-4 w-4" : "h-6 w-6";
  return (
    <div role="status" className={`flex items-center gap-2 text-sm text-slate-500 ${className}`}>
      <span
        className={`${dimension} animate-spin rounded-full border-2 border-slate-300 border-t-brand-600`}
        aria-hidden="true"
      />
      <span>{label}</span>
    </div>
  );
}
