interface PaginationProps {
  page: number;
  pages: number;
  total: number;
  onPageChange: (page: number) => void;
}

export function Pagination({ page, pages, total, onPageChange }: PaginationProps) {
  return (
    <nav className="flex items-center justify-between px-1 py-2 text-sm text-slate-600" aria-label="Pagination">
      <span>
        {total} result{total === 1 ? "" : "s"} · page {page} of {pages}
      </span>
      <div className="flex gap-2">
        <button
          type="button"
          className="btn-secondary py-1"
          disabled={page <= 1}
          onClick={() => onPageChange(page - 1)}
        >
          Previous
        </button>
        <button
          type="button"
          className="btn-secondary py-1"
          disabled={page >= pages}
          onClick={() => onPageChange(page + 1)}
        >
          Next
        </button>
      </div>
    </nav>
  );
}
