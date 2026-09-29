import { humanize } from "../utils/format";

interface BarListProps {
  title: string;
  data: Record<string, number>;
}

/** Minimal horizontal bar chart built with Tailwind (no chart library needed). */
export function BarList({ title, data }: BarListProps) {
  const entries = Object.entries(data);
  const max = Math.max(1, ...entries.map(([, count]) => count));
  return (
    <section className="card">
      <div className="card-header">
        <h3 className="card-title">{title}</h3>
      </div>
      <ul className="space-y-2 px-4 py-3">
        {entries.map(([key, count]) => (
          <li key={key} className="text-sm">
            <div className="mb-0.5 flex justify-between text-slate-600">
              <span>{humanize(key)}</span>
              <span className="font-mono tabular-nums">{count}</span>
            </div>
            <div className="h-2 rounded bg-slate-100">
              <div className="h-2 rounded bg-brand-500" style={{ width: `${(count / max) * 100}%` }} />
            </div>
          </li>
        ))}
      </ul>
    </section>
  );
}
