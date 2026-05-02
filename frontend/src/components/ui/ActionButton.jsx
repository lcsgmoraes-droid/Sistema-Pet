import { cloneElement, forwardRef, isValidElement } from "react";
import { Loader2 } from "lucide-react";
import { actionButtonClasses } from "./actionStyles";

const ICON_SIZES = {
  xs: 14,
  sm: 16,
  md: 18,
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

const ActionButton = forwardRef(function ActionButton(
  {
    children,
    className = "",
    disabled = false,
    icon,
    iconPosition = "left",
    intent = "neutral",
    loading = false,
    size = "sm",
    tone = "solid",
    type = "button",
    ...props
  },
  ref,
) {
  const iconSize = ICON_SIZES[size] || ICON_SIZES.sm;
  const isDisabled = disabled || loading;
  const iconNode = loading ? (
    <Loader2 size={iconSize} className="animate-spin" aria-hidden="true" />
  ) : (
    renderIcon(icon, iconSize)
  );

  return (
    <button
      ref={ref}
      type={type}
      disabled={isDisabled}
      className={actionButtonClasses({
        intent,
        tone,
        size,
        className,
      })}
      {...props}
    >
      {iconPosition === "left" ? iconNode : null}
      {children}
      {iconPosition === "right" ? iconNode : null}
    </button>
  );
});

export default ActionButton;
