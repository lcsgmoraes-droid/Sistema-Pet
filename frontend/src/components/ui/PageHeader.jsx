import { cloneElement, isValidElement } from "react";
import { HelpCircle } from "lucide-react";
import IconActionButton from "./IconActionButton";

function renderIcon(icon, className) {
  if (!icon) return null;
  if (isValidElement(icon)) {
    return cloneElement(icon, {
      className: [icon.props.className, className].filter(Boolean).join(" "),
      "aria-hidden": true,
    });
  }

  const Icon = icon;
  return <Icon className={className} aria-hidden="true" />;
}

export default function PageHeader({
  actions,
  className = "",
  icon,
  iconClassName = "",
  onTour,
  subtitle,
  title,
  tourTitle = "Ver tour guiado",
}) {
  return (
    <div
      className={[
        "erp-page-header",
        "flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between",
        className,
      ]
        .filter(Boolean)
        .join(" ")}
    >
      <div className="flex min-w-0 items-center gap-2.5">
        {icon ? (
          <div
            className={[
              "flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-blue-50 text-blue-600 shadow-sm dark:bg-blue-500/10 dark:text-blue-200",
              iconClassName,
            ]
              .filter(Boolean)
              .join(" ")}
          >
            {renderIcon(icon, "h-6 w-6")}
          </div>
        ) : null}

        <div className="min-w-0">
          <div className="flex min-w-0 flex-wrap items-center gap-2">
            <h1 className="truncate text-xl font-bold text-slate-950 dark:text-slate-100">{title}</h1>
            {onTour ? (
              <IconActionButton
                icon={HelpCircle}
                intent="neutral"
                tone="ghost"
                size="xs"
                onClick={onTour}
                title={tourTitle}
              />
            ) : null}
          </div>
          {subtitle ? <p className="text-xs text-slate-500 dark:text-slate-400">{subtitle}</p> : null}
        </div>
      </div>

      {actions ? (
        <div className="erp-page-header-actions flex flex-wrap items-center gap-2 lg:justify-end">
          {actions}
        </div>
      ) : null}
    </div>
  );
}
