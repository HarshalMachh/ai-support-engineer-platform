import { useAuth } from "../hooks/useAuth";
import { formatDateTime, humanize } from "../utils/format";

export function ProfilePage() {
  const { user } = useAuth();
  if (!user) return null;

  const rows: [string, string][] = [
    ["Name", user.name],
    ["Email", user.email],
    ["Role", humanize(user.role)],
    ["Status", user.is_active ? "Active" : "Inactive"],
    ["Member since", formatDateTime(user.created_at)],
  ];

  return (
    <div className="max-w-xl space-y-4">
      <h1 className="page-title">Your profile</h1>
      <dl className="card divide-y divide-slate-100">
        {rows.map(([label, value]) => (
          <div key={label} className="grid grid-cols-3 px-4 py-3 text-sm">
            <dt className="text-slate-500">{label}</dt>
            <dd className="col-span-2 font-medium text-slate-900">{value}</dd>
          </div>
        ))}
      </dl>
    </div>
  );
}
