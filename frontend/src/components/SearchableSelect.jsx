import { useEffect, useMemo, useRef, useState } from "react";
import { ChevronDown } from "lucide-react";

export default function SearchableSelect({
  label,
  options,
  value,
  onChange,
  placeholder = "Select",
  testid,
  className = "",
  emptyLabel = "No matches",
}) {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const rootRef = useRef(null);
  const selected = options.find((option) => option.value === value);
  const displayValue = open ? query : selected?.label || "";
  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return options;
    return options.filter((option) => `${option.label} ${option.search || ""}`.toLowerCase().includes(q));
  }, [options, query]);

  useEffect(() => {
    const handleClickAway = (event) => {
      if (!rootRef.current?.contains(event.target)) {
        setOpen(false);
        setQuery("");
      }
    };
    document.addEventListener("mousedown", handleClickAway);
    return () => document.removeEventListener("mousedown", handleClickAway);
  }, []);

  const choose = (nextValue) => {
    onChange(nextValue);
    setOpen(false);
    setQuery("");
  };

  return (
    <div ref={rootRef} className={`relative ${className}`} data-testid={testid ? `${testid}-wrapper` : undefined}>
      {label && <p className="text-xs uppercase tracking-[0.2em] text-stone-400 mb-1">{label}</p>}
      <div className="relative">
        <input
          value={displayValue}
          onFocus={() => setOpen(true)}
          onClick={() => setOpen(true)}
          onChange={(event) => {
            setQuery(event.target.value);
            setOpen(true);
          }}
          placeholder={placeholder}
          data-testid={testid}
          className="w-full h-11 border border-stone-300 bg-white px-3 pr-9 text-sm focus:outline-none focus:border-stone-900"
        />
        <ChevronDown className="pointer-events-none absolute right-3 top-1/2 h-4 w-4 -translate-y-1/2 text-stone-500" />
      </div>
      {open && (
        <div className="absolute z-40 mt-1 max-h-64 w-full overflow-auto border border-stone-200 bg-white shadow-lg" data-testid={testid ? `${testid}-options` : undefined}>
          {filtered.length === 0 ? (
            <div className="px-3 py-2 text-sm text-stone-500">{emptyLabel}</div>
          ) : filtered.map((option) => (
            <button
              key={option.value}
              type="button"
              onMouseDown={(event) => event.preventDefault()}
              onClick={() => choose(option.value)}
              data-testid={testid ? `${testid}-option-${option.value}` : undefined}
              className={`block w-full px-3 py-2 text-left text-sm hover:bg-stone-100 ${option.value === value ? "bg-stone-900 text-white hover:bg-stone-900" : "text-stone-700"}`}
            >
              {option.label}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
