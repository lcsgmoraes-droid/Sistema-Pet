export default function VacinasTabs({ aba, vacinasVencendoTotal, onChangeAba }) {
  const abas = [
    { id: "registros", label: "Por pet" },
    { id: "vencendo", label: `A vencer (${vacinasVencendoTotal})` },
    { id: "calendario", label: "Calendário Preventivo" },
  ];

  return (
    <div className="flex border-b border-gray-200">
      {abas.map((item) => (
        <button
          key={item.id}
          type="button"
          onClick={() => onChangeAba(item.id)}
          className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
            aba === item.id
              ? "border-orange-500 text-orange-600"
              : "border-transparent text-gray-500 hover:text-gray-700"
          }`}
        >
          {item.label}
        </button>
      ))}
    </div>
  );
}
