import { Moon, Sun } from "lucide-react";
import { useTheme } from "../../theme/ThemeContext";

export default function ThemeToggle({ className = "" }) {
  const { isDark, toggleTheme } = useTheme();
  const Icon = isDark ? Sun : Moon;
  const title = isDark ? "Usar tela clara" : "Usar tela escura";

  return (
    <button
      type="button"
      onClick={toggleTheme}
      aria-label={title}
      aria-pressed={isDark}
      title={title}
      className={[
        "inline-flex h-10 w-10 shrink-0 items-center justify-center rounded-lg border border-gray-200 bg-white text-gray-700 shadow-sm transition-colors",
        "hover:bg-gray-50 hover:text-gray-900 focus:outline-none focus:ring-2 focus:ring-[#0f8b8d] focus:ring-offset-2",
        "dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200 dark:hover:bg-slate-800 dark:hover:text-white dark:focus:ring-cyan-400 dark:focus:ring-offset-slate-950",
        className,
      ]
        .filter(Boolean)
        .join(" ")}
    >
      <Icon className="h-5 w-5" aria-hidden="true" />
      <span className="sr-only">{title}</span>
    </button>
  );
}
