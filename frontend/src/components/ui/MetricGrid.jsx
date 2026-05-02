export default function MetricGrid({ children, className = "" }) {
  return (
    <div
      className={[
        "grid auto-rows-fr grid-cols-1 items-stretch gap-3 sm:grid-cols-2 xl:grid-cols-4",
        className,
      ]
        .filter(Boolean)
        .join(" ")}
    >
      {children}
    </div>
  );
}
