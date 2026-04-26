import RepasseErro from "./repasse/RepasseErro";
import RepasseFiltros from "./repasse/RepasseFiltros";
import RepasseHeader from "./repasse/RepasseHeader";
import RepasseResumoCards from "./repasse/RepasseResumoCards";
import RepasseTabela from "./repasse/RepasseTabela";
import { useVetRepasse } from "./repasse/useVetRepasse";

export default function VetRepasse() {
  const repasse = useVetRepasse();

  return (
    <div className="p-6 space-y-5">
      <RepasseHeader carregando={repasse.carregando} onAtualizar={repasse.carregar} />
      <RepasseFiltros {...repasse} />
      <RepasseErro erro={repasse.erro} />
      {repasse.dados && <RepasseResumoCards {...repasse} />}
      <RepasseTabela {...repasse} />
      <p className="text-xs text-gray-400 text-right">
        Os lancamentos sao gerados ao finalizar uma consulta com procedimentos vinculados a um veterinario parceiro.
      </p>
    </div>
  );
}
