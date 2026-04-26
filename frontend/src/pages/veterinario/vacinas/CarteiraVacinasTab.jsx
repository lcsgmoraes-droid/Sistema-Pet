import { ChevronDown, Syringe } from "lucide-react";
import TutorAutocomplete from "../../../components/TutorAutocomplete";
import { badgeProxDose, formatData } from "./vacinaUtils";

export default function CarteiraVacinasTab({
  tutorFiltroSelecionado,
  pessoaFiltro,
  petSelecionado,
  petsFiltradosCarteira,
  vacinas,
  carregando,
  onSelecionarTutor,
  onSelecionarPet,
  onRegistrarPrimeiraVacina,
}) {
  return (
    <div className="space-y-4">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        <TutorAutocomplete
          label="Tutor"
          inputId="vacinas-tutor-filtro"
          selectedTutor={tutorFiltroSelecionado}
          onSelect={onSelecionarTutor}
        />

        <div className="relative">
          <label htmlFor="vacinas-pet-filtro" className="sr-only">
            Pet
          </label>
          <ChevronDown size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
          <select
            id="vacinas-pet-filtro"
            name="vacinas-pet-filtro"
            value={petSelecionado}
            onChange={(event) => onSelecionarPet(event.target.value)}
            disabled={!pessoaFiltro}
            className="w-full pl-9 pr-3 py-2.5 text-sm border border-gray-200 rounded-lg bg-white focus:outline-none focus:ring-2 focus:ring-orange-300 disabled:opacity-60"
          >
            <option value="">Selecione um pet para ver a carteira...</option>
            {petsFiltradosCarteira.map((pet) => (
              <option key={pet.id} value={pet.id}>
                {pet.nome} ({pet.especie ?? "pet"})
              </option>
            ))}
          </select>
        </div>
      </div>

      {!petSelecionado && (
        <div className="p-10 text-center bg-white border border-gray-200 rounded-xl">
          <Syringe size={36} className="mx-auto text-gray-200 mb-3" />
          <p className="text-gray-400 text-sm">Selecione um pet para ver sua carteira de vacinação.</p>
        </div>
      )}

      {petSelecionado && carregando && (
        <div className="flex justify-center py-8">
          <div className="animate-spin rounded-full h-7 w-7 border-b-2 border-orange-400" />
        </div>
      )}

      {petSelecionado && !carregando && (
        <>
          {vacinas.length === 0 ? (
            <CarteiraVazia onRegistrarPrimeiraVacina={onRegistrarPrimeiraVacina} />
          ) : (
            <CarteiraTabela vacinas={vacinas} />
          )}
        </>
      )}
    </div>
  );
}

function CarteiraVazia({ onRegistrarPrimeiraVacina }) {
  return (
    <div className="p-8 text-center bg-white border border-gray-200 rounded-xl">
      <p className="text-gray-400 text-sm">Nenhuma vacina registrada para este pet.</p>
      <button
        type="button"
        onClick={onRegistrarPrimeiraVacina}
        className="mt-3 text-sm text-orange-500 underline"
      >
        Registrar primeira vacina
      </button>
    </div>
  );
}

function CarteiraTabela({ vacinas }) {
  return (
    <div className="bg-white border border-gray-200 rounded-xl overflow-hidden">
      <table className="w-full text-sm">
        <thead className="bg-gray-50 border-b border-gray-100">
          <tr>
            <th className="text-left px-4 py-3 font-medium text-gray-600">Vacina</th>
            <th className="text-left px-4 py-3 font-medium text-gray-600">Aplicação</th>
            <th className="text-left px-4 py-3 font-medium text-gray-600">Próxima dose</th>
            <th className="text-left px-4 py-3 font-medium text-gray-600">Lote</th>
            <th className="text-left px-4 py-3 font-medium text-gray-600">Veterinário</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-50">
          {vacinas.map((vacina) => {
            const badge = badgeProxDose(vacina.proxima_dose);

            return (
              <tr key={vacina.id} className="hover:bg-orange-50 transition-colors">
                <td className="px-4 py-3 font-medium text-gray-800">{vacina.nome_vacina}</td>
                <td className="px-4 py-3 text-gray-600">{formatData(vacina.data_aplicacao)}</td>
                <td className="px-4 py-3">
                  {vacina.proxima_dose ? (
                    <div className="flex items-center gap-2">
                      <span className="text-gray-600">{formatData(vacina.proxima_dose)}</span>
                      {badge && (
                        <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${badge.cls}`}>
                          {badge.label}
                        </span>
                      )}
                    </div>
                  ) : (
                    "-"
                  )}
                </td>
                <td className="px-4 py-3 text-gray-500">{vacina.lote ?? "-"}</td>
                <td className="px-4 py-3 text-gray-500">{vacina.veterinario_responsavel ?? "-"}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
