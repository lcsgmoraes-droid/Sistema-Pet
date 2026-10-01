// Bolinha colorida + rotulo — indicador pequeno de "este item vem daquela
// origem" (ex.: no formulario de proposta comercial, qual segmento de plano
// concede um modulo). Mesmo vocabulario de cor de `InputRadio`'s prop `tom`
// (pet/vet/grooming), pra bolinha e radio do mesmo segmento usarem a mesma cor.
const CORES_TOM = {
  pet: "bg-blue-600",
  vet: "bg-emerald-600",
  grooming: "bg-violet-600",
};

export default function LegendaBolinha({ tom = "pet", rotulo }) {
  return (
    <span className="inline-flex items-center gap-1" title={rotulo}>
      <span
        className={`h-2.5 w-2.5 flex-none rounded-full ${CORES_TOM[tom] || CORES_TOM.pet}`}
        aria-hidden="true"
      />
      {rotulo ? (
        <span className="sr-only">{rotulo}</span>
      ) : null}
    </span>
  );
}
