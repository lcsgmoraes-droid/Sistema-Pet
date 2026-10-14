import {
  Award,
  Cake,
  CalendarCheck,
  CheckCircle2,
  Dna,
  Droplet,
  Hash,
  Hourglass,
  Palette,
  PawPrint,
  Ruler,
  Scale,
  ScanLine,
  Tag,
  UserRound,
  XCircle,
} from "lucide-react";
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

function SecaoCampos({ children, titulo }) {
  return (
    <div>
      <h3 className="mb-2 text-xs font-semibold uppercase tracking-wider text-slate-500">
        {titulo}
      </h3>
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">{children}</div>
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
      <h2 className="text-xl font-bold text-gray-900 mb-4">Informações Gerais</h2>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <ResumoClinicoCard title="Última vacina" tone="blue">
          {ultimaVacina ? (
            <>
              <p className="text-sm font-semibold text-blue-900">
                {ultimaVacina.nome_vacina || "Vacina"}
              </p>
              <p className="text-xs text-blue-800">
                Aplicada em: {formatarData(ultimaVacina.data_aplicacao)}
              </p>
              <p className="text-xs text-blue-800">
                Próxima dose:{" "}
                {formatarData(ultimaVacina.proxima_dose || ultimaVacina.data_proxima_dose)}
              </p>
            </>
          ) : (
            <p className="text-sm text-blue-800">Nenhuma vacina registrada.</p>
          )}
        </ResumoClinicoCard>

        <ResumoClinicoCard title="Resumo da última alta" tone="green">
          {ultimaAlta ? (
            <>
              <p className="text-xs text-green-800">
                Alta em: {formatarDataHora(ultimaAlta.data_saida)}
              </p>
              <p className="text-sm font-semibold text-green-900 mt-1">
                Motivo: {ultimaAlta.motivo || "-"}
              </p>
              <p className="text-xs text-green-800 mt-1">
                Observação: {ultimaAlta.observacoes_alta || "Sem observação de alta."}
              </p>
            </>
          ) : (
            <p className="text-sm text-green-800">Nenhuma alta registrada.</p>
          )}
        </ResumoClinicoCard>
      </div>

      <div className="space-y-5">
        <SecaoCampos titulo="Identificação">
          <PetDetalhesInfoField icon={PawPrint} label="Nome" value={pet.nome} />
          <PetDetalhesInfoField icon={Hash} label="Código" mono value={pet.codigo} />
          <PetDetalhesInfoField icon={Tag} label="Espécie" value={pet.especie} />
          <PetDetalhesInfoField icon={Dna} label="Raça" value={pet.raca} />
          <PetDetalhesInfoField icon={UserRound} label="Sexo" value={pet.sexo} />
        </SecaoCampos>

        <SecaoCampos titulo="Características físicas">
          <PetDetalhesInfoField icon={Cake} label="Data de Nascimento" value={formatarData(pet.data_nascimento)} />
          <PetDetalhesInfoField icon={Hourglass} label="Idade" value={idade} />
          <PetDetalhesInfoField icon={Scale} label="Peso" value={pet.peso ? `${pet.peso} kg` : "-"} />
          <PetDetalhesInfoField icon={Ruler} label="Porte" value={pet.porte} />
          <PetDetalhesInfoField icon={Palette} label="Cor/Pelagem" value={pet.cor} />
          <PetDetalhesInfoField
            icon={pet.castrado ? CheckCircle2 : XCircle}
            label="Castrado"
            value={pet.castrado ? "Sim" : "Não"}
          />
          <PetDetalhesInfoField
            icon={CalendarCheck}
            label="Data da castração"
            value={formatarData(pet.castrado_data)}
          />
        </SecaoCampos>

        <SecaoCampos titulo="Outras informações">
          <PetDetalhesInfoField icon={ScanLine} label="Microchip" mono value={pet.microchip} />
          <PetDetalhesInfoField icon={Droplet} label="Tipo sanguíneo" value={pet.tipo_sanguineo} />
          <PetDetalhesInfoField icon={Award} label="Pedigree" value={pet.pedigree_registro} />
        </SecaoCampos>
      </div>

      {pet.observacoes && (
        <div>
          <p className="text-sm font-medium text-gray-700 mb-1">Observações</p>
          <p className="text-gray-900 bg-gray-50 p-3 rounded-lg">{pet.observacoes}</p>
        </div>
      )}

      <div className="pt-4 border-t border-gray-200 text-sm text-gray-500">
        <p>Cadastrado em: {formatarData(pet.created_at)}</p>
        <p>Última atualização: {formatarData(pet.updated_at)}</p>
      </div>
    </div>
  );
}
