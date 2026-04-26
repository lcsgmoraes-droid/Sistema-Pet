const ABAS = [
  { id: "ativas", label: "Ativas" },
  { id: "historico", label: "Histórico" },
];

export default function InternacoesTabs({ aba, onChangeAba }) {
  return (
    <div className="flex border-b border-gray-200">
      {ABAS.map((item) => (
        <button
          key={item.id}
          type="button"
          onClick={() => onChangeAba(item.id)}
          className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
            aba === item.id
              ? "border-purple-500 text-purple-600"
              : "border-transparent text-gray-500 hover:text-gray-700"
          }`}
        >
          {item.label}
        </button>
      ))}
    </div>
  );
}
