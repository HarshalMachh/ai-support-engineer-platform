interface AnalyticsCardProps {
  label: string;
  value: string | number;
  hint?: string;
  tone?: "default" | "danger" | "success" | "warning";
}

const TONES = {
  default: "text-slate-900",
  danger: "text-rose-600",
  success: "text-emerald-600",
  warning: "text-amber-600",
};

export function AnalyticsCard({ label, value, hint, tone = "default" }: AnalyticsCardProps) {
  return (
    <div className="card px-4 py-3">
      <p className="text-xs font-medium uppercase tracking-wide text-slate-500">{label}</p>
      <p className={`mt-1 text-2xl font-semibold tabular-nums ${TONES[tone]}`}>{value}</p>
      {hint && <p className="mt-0.5 text-xs text-slate-500">{hint}</p>}
    </div>
  );
}
