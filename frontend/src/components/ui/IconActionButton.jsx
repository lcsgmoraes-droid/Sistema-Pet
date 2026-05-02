import { cloneElement, forwardRef, isValidElement } from "react";
import { Loader2 } from "lucide-react";
import { iconActionButtonClasses } from "./actionStyles";

const ICON_SIZES = {
  xs: 14,
  sm: 16,
  md: 18,
  lg: 20,
};

function renderIcon(icon, size, className) {
  if (!icon) return null;
  if (isValidElement(icon)) {
    return cloneElement(icon, {
      className: [icon.props.className, className].filter(Boolean).join(" "),
      "aria-hidden": true,
    });
  }

  const Icon = icon;
  return <Icon size={size} className={className} aria-hidden="true" />;
}

const IconActionButton = forwardRef(function IconActionButton(
  {
    active = false,
    badge,
    className = "",
    disabled = false,
    icon,
    intent = "neutral",
    loading = false,
    size = "sm",
    tone = "soft",
    type = "button",
    ...props
  },
  ref,
) {
  const iconSize = ICON_SIZES[size] || ICON_SIZES.sm;
  const isDisabled = disabled || loading;

  return (
    <button
      ref={ref}
      type={type}
      disabled={isDisabled}
      className={iconActionButtonClasses({
        active,
        intent,
        tone,
        size,
        className,
      })}
      {...props}
    >
      {loading ? (
        <Loader2 size={iconSize} className="animate-spin" aria-hidden="true" />
      ) : (
        renderIcon(icon, iconSize)
      )}
      {badge ? (
        <span className="absolute -right-2 -top-2 flex min-h-5 min-w-5 items-center justify-center rounded-full bg-red-500 px-1 text-[10px] font-bold leading-none text-white">
          {badge}
        </span>
      ) : null}
    </button>
  );
});

export default IconActionButton;
