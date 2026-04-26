export default function BanhoTosaHelpTooltip({ text }) {
  if (!text) return null;

  return (
    <span className="group relative inline-flex align-middle">
      <span
        tabIndex={0}
        className="ml-1 inline-flex h-4 w-4 cursor-help items-center justify-center rounded-full bg-orange-100 text-[10px] font-black text-orange-700 outline-none ring-orange-200 transition group-hover:bg-orange-200 focus:ring-2"
      >
        ?
      </span>
      <span className="pointer-events-none absolute left-1/2 top-6 z-20 hidden w-64 -translate-x-1/2 rounded-2xl border border-slate-200 bg-slate-950 px-3 py-2 text-xs font-semibold normal-case leading-relaxed tracking-normal text-white shadow-xl group-hover:block group-focus-within:block">
        {text}
      </span>
    </span>
  );
}
