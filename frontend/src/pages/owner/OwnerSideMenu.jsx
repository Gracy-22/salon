import { TABS } from "./utils";

export function OwnerSideMenu({ tab, setTab, collapsed }) {
  return (
    <nav className="space-y-2" data-testid="owner-side-menu" aria-label="Owner dashboard sections">
      {TABS.map((item) => {
        const Icon = item.icon;
        const active = tab === item.key;
        return (
          <button
            key={item.key}
            type="button"
            onClick={() => setTab(item.key)}
            aria-pressed={active}
            title={collapsed ? item.label : undefined}
            data-testid={`owner-tab-${item.key}`}
            className={`group flex w-full items-center gap-3 border px-3 py-3 text-left transition-colors ${active ? "border-stone-900 bg-stone-900 text-stone-50" : "border-stone-200 bg-white text-stone-700 hover:border-stone-900"} ${collapsed ? "justify-center" : "justify-start"}`}
          >
            <span className={`inline-flex h-9 w-9 shrink-0 items-center justify-center border ${active ? "border-stone-50" : "border-stone-200 group-hover:border-stone-900"}`}>
              <Icon className="h-4 w-4" />
            </span>
            {!collapsed && (
              <span className="min-w-0">
                <span className="block text-xs uppercase tracking-[0.16em]" data-testid={`owner-tab-label-${item.key}`}>{item.label}</span>
                <span className={`mt-1 block text-[11px] ${active ? "text-stone-300" : "text-stone-500"}`}>{item.description}</span>
              </span>
            )}
          </button>
        );
      })}
    </nav>
  );
}
