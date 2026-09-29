import { useEffect, useState } from "react";
import { useDebounce } from "../hooks/useDebounce";

interface TicketSearchProps {
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
}

/** Debounced search input; calls onChange 300ms after the user stops typing. */
export function TicketSearch({ value, onChange, placeholder = "Search subject, description or #id" }: TicketSearchProps) {
  const [text, setText] = useState(value);
  const debounced = useDebounce(text);

  useEffect(() => {
    if (debounced !== value) onChange(debounced);
  }, [debounced, value, onChange]);

  return (
    <input
      type="search"
      className="input"
      aria-label="Search tickets"
      placeholder={placeholder}
      value={text}
      onChange={(event) => setText(event.target.value)}
    />
  );
}
