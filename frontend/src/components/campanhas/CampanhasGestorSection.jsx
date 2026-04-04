export default function CampanhasGestorSection({
  icon,
  title,
  subtitle,
  isOpen,
  onToggle,
  children,
}) {
  return (
    <div className="bg-white rounded-xl border shadow-sm overflow-hidden">
      <button
        onClick={onToggle}
        className="w-full px-6 py-4 flex items-center justify-between hover:bg-gray-50 transition-colors"
      >
        <div className="flex items-center gap-3">
          <span className="text-xl">{icon}</span>
          <div className="text-left">
            <p className="font-semibold text-gray-800">{title}</p>
            <p className="text-xs text-gray-500">{subtitle}</p>
          </div>
        </div>
        <span className="text-gray-400 text-sm">{isOpen ? "▲" : "▼"}</span>
      </button>

      {isOpen && <div className="border-t">{children}</div>}
    </div>
  );
}
