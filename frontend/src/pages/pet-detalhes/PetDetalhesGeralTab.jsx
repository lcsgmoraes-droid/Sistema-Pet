import { formatarIdadeMeses } from "../../helpers/idadeHelper";
import PetDetalhesInfoField from "./PetDetalhesInfoField";
import { calcularIdade, formatarData, formatarDataHora } from "./petDetalhesUtils";

function ResumoClinicoCard({ children, title, tone }) {
  const tones = {
    blue: "border-blue-200 bg-blue-50 text-blue-700",
    green: "border-green-200 bg-green-50 text-green-700",
  };

  return (
    <div className={`border rounded-lg p-4 ${tones[tone]}`}>
      <p className="text-xs font-semibold mb-1">{title}</p>
      {children}
    </div>
  );
}

export default function PetDetalhesGeralTab({ pet, ultimaAlta, ultimaVacina }) {
  const idade = pet.idade_meses
    ? formatarIdadeMeses(pet.idade_meses)
    : pet.idade_aproximada
      ? formatarIdadeMeses(pet.idade_aproximada)
      : pet.data_nascimento
        ? calcularIdade(pet.data_nascimento)
        : "-";

  return (
    <div className="space-y-6">
      <h2 className="text-xl font-bold text-gray-900 mb-4">InformaÃ§Ãµes Gerais</h2>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <ResumoClinicoCard title="Ãšltima vacina" tone="blue">
          {ultimaVacina ? (
            <>
              <p className="text-sm font-semibold text-blue-900">
                {ultimaVacina.nome_vacina || "Vacina"}
              </p>
              <p className="text-xs text-blue-800">
                Aplicada em: {formatarData(ultimaVacina.data_aplicacao)}
              </p>
              <p className="text-xs text-blue-800">
                PrÃ³xima dose:{" "}
                {formatarData(ultimaVacina.proxima_dose || ultimaVacina.data_proxima_dose)}
              </p>
            </>
          ) : (
            <p className="text-sm text-blue-800">Nenhuma vacina registrada.</p>
          )}
        </ResumoClinicoCard>

        <ResumoClinicoCard title="Resumo da Ãºltima alta" tone="green">
          {ultimaAlta ? (
            <>
              <p className="text-xs text-green-800">
                Alta em: {formatarDataHora(ultimaAlta.data_saida)}
              </p>
              <p className="text-sm font-semibold text-green-900 mt-1">
                Motivo: {ultimaAlta.motivo || "-"}
              </p>
              <p className="text-xs text-green-800 mt-1">
                ObservaÃ§Ã£o: {ultimaAlta.observacoes_alta || "Sem observaÃ§Ã£o de alta."}
              </p>
            </>
          ) : (
            <p className="text-sm text-green-800">Nenhuma alta registrada.</p>
          )}
        </ResumoClinicoCard>
      </div>

      <div className="grid grid-cols-2 gap-6">
        <PetDetalhesInfoField label="Nome">{pet.nome}</PetDetalhesInfoField>
        <PetDetalhesInfoField label="CÃ³digo" mono>
          {pet.codigo}
        </PetDetalhesInfoField>
        <PetDetalhesInfoField label="EspÃ©cie">{pet.especie}</PetDetalhesInfoField>
        <PetDetalhesInfoField label="RaÃ§a">{pet.raca}</PetDetalhesInfoField>
        <PetDetalhesInfoField label="Sexo">{pet.sexo}</PetDetalhesInfoField>
        <PetDetalhesInfoField label="Castrado">
          {pet.castrado ? "Sim" : "NÃ£o"}
        </PetDetalhesInfoField>
        <PetDetalhesInfoField label="Data de Nascimento">
          {formatarData(pet.data_nascimento)}
        </PetDetalhesInfoField>
        <PetDetalhesInfoField label="Idade">{idade}</PetDetalhesInfoField>
        <PetDetalhesInfoField label="Peso">
          {pet.peso ? `${pet.peso} kg` : "-"}
        </PetDetalhesInfoField>
        <PetDetalhesInfoField label="Porte">{pet.porte}</PetDetalhesInfoField>
        <PetDetalhesInfoField label="Cor/Pelagem">{pet.cor}</PetDetalhesInfoField>
        <PetDetalhesInfoField label="Microchip" mono>
          {pet.microchip}
        </PetDetalhesInfoField>
        <PetDetalhesInfoField label="Tipo sanguÃ­neo">{pet.tipo_sanguineo}</PetDetalhesInfoField>
        <PetDetalhesInfoField label="Pedigree">{pet.pedigree_registro}</PetDetalhesInfoField>
        <PetDetalhesInfoField label="Data da castraÃ§Ã£o">
          {formatarData(pet.castrado_data)}
        </PetDetalhesInfoField>
      </div>

      {pet.observacoes && (
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">ObservaÃ§Ãµes</label>
          <p className="text-gray-900 bg-gray-50 p-3 rounded-lg">{pet.observacoes}</p>
        </div>
      )}

      <div className="pt-4 border-t border-gray-200 text-sm text-gray-500">
        <p>Cadastrado em: {formatarData(pet.created_at)}</p>
        <p>Ãšltima atualizaÃ§Ã£o: {formatarData(pet.updated_at)}</p>
      </div>
    </div>
  );
}
