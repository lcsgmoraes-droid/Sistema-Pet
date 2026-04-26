export default function ExameIAArquivoCard({ exame }) {
  if (!exame.arquivo_nome) return null;

  return (
    <div className="rounded-lg border border-indigo-100 bg-indigo-50 px-3 py-2">
      <p className="font-medium text-indigo-800">Arquivo</p>
      <div className="mt-1 flex flex-wrap items-center gap-3">
        <span>{exame.arquivo_nome}</span>
        {exame.arquivo_url && (
          <a href={exame.arquivo_url} target="_blank" rel="noreferrer" className="text-indigo-700 underline">
            abrir arquivo
          </a>
        )}
      </div>
    </div>
  );
}
