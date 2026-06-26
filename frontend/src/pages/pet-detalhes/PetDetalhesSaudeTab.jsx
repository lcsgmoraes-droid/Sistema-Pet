import PetDetalhesExamesPanel from "./PetDetalhesExamesPanel";
import { listaClinica } from "./petDetalhesUtils";

function ClinicalList({ empty, items, title }) {
  return (
    <div>
      <label className="block text-sm font-medium text-gray-700 mb-2">{title}</label>
      <div className="bg-gray-50 p-4 rounded-lg border border-gray-200">
        {items.length > 0 ? (
          <div className="flex flex-wrap gap-2">
            {items.map((item) => (
              <span
                key={`${title}_${item}`}
                className="px-3 py-1 bg-white border border-gray-200 rounded-full text-sm text-gray-800"
              >
                {item}
              </span>
            ))}
          </div>
        ) : (
          <p className="text-gray-500">{empty}</p>
        )}
      </div>
    </div>
  );
}

export default function PetDetalhesSaudeTab({
  carregarExames,
  carteirinha,
  exames,
  loadingExames,
  novoExame,
  onInterpretarExameIA,
  onSalvarNovoExame,
  pet,
  salvandoExame,
  setNovoExame,
}) {
  return (
    <div className="space-y-6">
      <h2 className="text-xl font-bold text-gray-900 mb-4">InformaÃ§Ãµes de SaÃºde</h2>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <ClinicalList
          title="Alergias"
          items={listaClinica(pet.alergias_lista, pet.alergias)}
          empty="Nenhuma alergia registrada"
        />
        <ClinicalList
          title="DoenÃ§as crÃ´nicas"
          items={listaClinica(pet.condicoes_cronicas_lista, pet.doencas_cronicas)}
          empty="Nenhuma doenÃ§a crÃ´nica registrada"
        />
        <ClinicalList
          title="Medicamentos contÃ­nuos"
          items={listaClinica(pet.medicamentos_continuos_lista, pet.medicamentos_continuos)}
          empty="Nenhum medicamento contÃ­nuo registrado"
        />
        <ClinicalList
          title="RestriÃ§Ãµes alimentares"
          items={listaClinica(pet.restricoes_alimentares_lista)}
          empty="Nenhuma restriÃ§Ã£o alimentar registrada"
        />
      </div>

      {Array.isArray(carteirinha?.alertas) && carteirinha.alertas.length > 0 && (
        <div className="bg-amber-50 border border-amber-200 rounded-xl p-4">
          <h3 className="text-sm font-semibold text-amber-900 mb-2">
            Alertas para atendimento e venda
          </h3>
          <div className="space-y-2">
            {carteirinha.alertas.slice(0, 6).map((alerta, idx) => (
              <div key={`alerta_${idx}`} className="text-sm text-amber-900">
                â€¢ {alerta.mensagem}
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            HistÃ³rico ClÃ­nico
          </label>
          <div className="bg-gray-50 p-4 rounded-lg border border-gray-200">
            <p className="text-gray-900 whitespace-pre-line">
              {pet.historico_clinico || "Nenhum histÃ³rico clÃ­nico registrado"}
            </p>
          </div>
        </div>

        <PetDetalhesExamesPanel
          exames={exames}
          loadingExames={loadingExames}
          novoExame={novoExame}
          onInterpretarExameIA={onInterpretarExameIA}
          onRefresh={carregarExames}
          onSalvarNovoExame={onSalvarNovoExame}
          salvandoExame={salvandoExame}
          setNovoExame={setNovoExame}
        />
      </div>
    </div>
  );
}
