import { useState } from "react";
import { ErrorMessage } from "../../components/ErrorMessage";
import { LoadingSpinner } from "../../components/LoadingSpinner";
import { Pagination } from "../../components/Pagination";
import { useDebounce } from "../../hooks/useDebounce";
import { useUsers } from "../../hooks/useUsers";
import type { UserRole } from "../../types";
import { formatDateTime, humanize } from "../../utils/format";

const ROLE_TABS: { value: UserRole | ""; label: string }[] = [
  { value: "", label: "All users" },
  { value: "CUSTOMER", label: "Customers" },
  { value: "AGENT", label: "Agents" },
  { value: "ADMIN", label: "Admins" },
];

export function AdminUsersPage() {
  const [role, setRole] = useState<UserRole | "">("");
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const debouncedSearch = useDebounce(search);
  const users = useUsers({ role, search: debouncedSearch, page, page_size: 20 });

  return (
    <div className="space-y-4">
      <h1 className="page-title">Users</h1>
      <div className="flex flex-wrap items-center gap-2">
        <div className="flex rounded-md border border-slate-200 bg-white p-0.5" role="tablist">
          {ROLE_TABS.map((tab) => (
            <button
              key={tab.label}
              type="button"
              role="tab"
              aria-selected={role === tab.value}
              className={`rounded px-3 py-1.5 text-sm ${
                role === tab.value ? "bg-brand-600 text-white" : "text-slate-600 hover:bg-slate-50"
              }`}
              onClick={() => {
                setRole(tab.value);
                setPage(1);
              }}
            >
              {tab.label}
            </button>
          ))}
        </div>
        <input
          type="search"
          className="input w-64"
          placeholder="Search name or email"
          aria-label="Search users"
          value={search}
          onChange={(e) => {
            setSearch(e.target.value);
            setPage(1);
          }}
        />
      </div>

      <div className="card overflow-x-auto">
        {users.isLoading && <LoadingSpinner className="p-4" />}
        {users.isError && (
          <div className="p-4">
            <ErrorMessage error={users.error} />
          </div>
        )}
        {users.data && (
          <table className="min-w-full divide-y divide-slate-200 text-sm">
            <thead className="bg-slate-50 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">
              <tr>
                <th className="px-4 py-2">Name</th>
                <th className="px-4 py-2">Email</th>
                <th className="px-4 py-2">Role</th>
                <th className="px-4 py-2">Status</th>
                <th className="px-4 py-2">Created</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {users.data.items.map((u) => (
                <tr key={u.id}>
                  <td className="px-4 py-2.5 font-medium">{u.name}</td>
                  <td className="px-4 py-2.5 font-mono text-xs">{u.email}</td>
                  <td className="px-4 py-2.5">{humanize(u.role)}</td>
                  <td className="px-4 py-2.5">{u.is_active ? "Active" : "Inactive"}</td>
                  <td className="px-4 py-2.5 text-slate-500">{formatDateTime(u.created_at)}</td>
                </tr>
              ))}
              {users.data.items.length === 0 && (
                <tr>
                  <td colSpan={5} className="px-4 py-8 text-center text-slate-500">No users found.</td>
                </tr>
              )}
            </tbody>
          </table>
        )}
      </div>
      {users.data && users.data.total > 0 && (
        <Pagination page={users.data.page} pages={users.data.pages} total={users.data.total} onPageChange={setPage} />
      )}
    </div>
  );
}
