export default function StyleGuideSection({ title, description, children, id }) {
  return (
    <section id={id} className="scroll-mt-20 border-t border-slate-200 pt-8 dark:border-slate-800">
      <h2 className="text-lg font-bold text-slate-950 dark:text-slate-100">{title}</h2>
      {description ? (
        <p className="mt-1 max-w-3xl text-sm text-slate-500 dark:text-slate-400">{description}</p>
      ) : null}
      <div className="mt-5 space-y-6">{children}</div>
    </section>
  );
}
