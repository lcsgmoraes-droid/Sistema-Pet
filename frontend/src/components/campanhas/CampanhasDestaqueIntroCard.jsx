export default function CampanhasDestaqueIntroCard() {
  return (
    <div className="bg-amber-50 border border-amber-200 rounded-xl p-4 flex items-start gap-3">
      <span className="text-2xl">{"\u{1F31F}"}</span>
      <div>
        <p className="font-semibold text-amber-800">Destaque Mensal</p>
        <p className="text-sm text-amber-700 mt-0.5">
          O sistema identifica os clientes que mais gastaram e mais compraram
          no m\u00EAs anterior. Voc\u00EA pode premiar cada vencedor com um
          cupom de recompensa.
        </p>
      </div>
    </div>
  );
}
