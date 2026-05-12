function cx(...classes) {
  return classes.filter(Boolean).join(" ");
}

const containerSizes = {
  sm: "p-0.5 text-xs",
  md: "p-1 text-xs",
};

const optionSizes = {
  sm: "px-3 py-1",
  md: "px-3 py-1.5",
};

export default function SegmentedControl({
  ariaLabel,
  className = "",
  onChange,
  options = [],
  size = "sm",
  value,
}) {
  const containerSize = containerSizes[size] || containerSizes.sm;
  const optionSize = optionSizes[size] || optionSizes.sm;

  return (
    <div
      aria-label={ariaLabel}
      className={cx(
        "inline-flex rounded-lg border border-slate-200 bg-slate-50 font-semibold",
        containerSize,
        className,
      )}
      role="group"
    >
      {options.map((option) => {
        const active = option.value === value;

        return (
          <button
            key={option.value}
            type="button"
            aria-pressed={active}
            disabled={option.disabled}
            onClick={() => {
              onChange?.(option.value, option);
              option.onSelect?.(option.value, option);
            }}
            className={cx(
              "rounded-md transition-colors disabled:cursor-not-allowed disabled:opacity-50",
              optionSize,
              active
                ? option.activeClassName || "bg-white text-blue-700 shadow-sm"
                : option.inactiveClassName || "text-slate-600 hover:bg-white/80",
            )}
          >
            {option.label}
          </button>
        );
      })}
    </div>
  );
}
