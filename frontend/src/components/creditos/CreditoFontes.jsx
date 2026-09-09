import { fontesHttpsSeguras } from "./creditosModel";

export default function CreditoFontes({ fontes }) {
  const urls = fontesHttpsSeguras(fontes);
  if (!urls.length) return null;
  return (
    <aside className="mx-6 my-3 rounded-xl border border-slate-200 bg-white p-4 text-sm">
      <p className="font-semibold text-slate-900">Fontes do rascunho de IA</p>
      <p className="mt-1 text-slate-600">
        Confira os dados do produto e a sugestão fiscal antes de salvar.
      </p>
      <ul className="mt-2 list-inside list-disc space-y-1">
        {urls.map((url) => (
          <li key={url}>
            <a
              href={url}
              target="_blank"
              rel="noopener noreferrer"
              className="break-all text-blue-700 underline"
            >
              {url}
            </a>
          </li>
        ))}
      </ul>
    </aside>
  );
}
