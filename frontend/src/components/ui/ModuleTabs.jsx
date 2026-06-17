const SIZE_CLASSES = {
  sm: "px-3 py-1.5 text-xs",
  md: "px-4 py-2 text-sm",
};

export default function ModuleTabs({
  active,
  ariaLabel = "Abas do modulo",
  className = "",
  onChange,
  size = "md",
  tabs = [],
}) {
  const sizeClasses = SIZE_CLASSES[size] || SIZE_CLASSES.md;

  return (
    <div
      className={["erp-module-tabs border-b border-slate-200", className].filter(Boolean).join(" ")}
    >
      <div
        role="tablist"
        aria-label={ariaLabel}
        className="erp-module-tablist flex gap-1 overflow-x-auto"
      >
        {tabs.map((tab) => {
          const isActive = active === tab.id;

          return (
            <button
              key={tab.id}
              type="button"
              role="tab"
              aria-selected={isActive}
              disabled={tab.disabled}
              onClick={() => onChange?.(tab.id)}
              className={[
                "whitespace-nowrap rounded-t-lg border-b-2 font-medium transition-colors",
                "disabled:cursor-not-allowed disabled:text-slate-300",
                sizeClasses,
                isActive
                  ? "border-blue-600 bg-blue-50 text-blue-700"
                  : "border-transparent text-slate-600 hover:bg-slate-50 hover:text-slate-900",
                tab.className,
              ]
                .filter(Boolean)
                .join(" ")}
            >
              {tab.label}
            </button>
          );
        })}
      </div>
    </div>
  );
}
