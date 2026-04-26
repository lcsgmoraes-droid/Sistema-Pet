export default function ExameIAValoresEstruturados({ resultadoEstruturado }) {
  if (resultadoEstruturado.length === 0) return null;

  return (
    <div className="space-y-2">
      <p className="font-medium text-indigo-900">Valores estruturados</p>
      <div className="flex flex-wrap gap-2">
        {resultadoEstruturado.slice(0, 12).map(([chave, valor]) => (
          <span
            key={chave}
            className="rounded-full border border-indigo-200 bg-white px-2 py-1 text-[11px] text-indigo-700"
          >
            {chave}: {String(valor)}
          </span>
        ))}
      </div>
    </div>
  );
}
