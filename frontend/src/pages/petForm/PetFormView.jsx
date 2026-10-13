import { AlertCircle, ArrowLeft, CheckCircle2, PawPrint, Plus } from "lucide-react";

import CampoIdadeInteligente from "../../components/CampoIdadeInteligente";
import QuickAddModal from "../../components/QuickAddModal";
import BotaoCancelar from "../../components/v2/BotaoCancelar/BotaoCancelar";
import BotaoInteracao from "../../components/v2/BotaoInteracao/BotaoInteracao";
import BotaoLink from "../../components/v2/BotaoLink/BotaoLink";
import BotaoSalva from "../../components/v2/BotaoSalva/BotaoSalva";
import InputCheckTexto from "../../components/v2/InputCheckTexto/InputCheckTexto";
import InputCombobox from "../../components/v2/InputCombobox/InputCombobox";
import InputData from "../../components/v2/InputData/InputData";
import InputRadio from "../../components/v2/InputRadio/InputRadio";
import InputTexto from "../../components/v2/InputTexto/InputTexto";
import InputTextoLongo from "../../components/v2/InputTextoLongo/InputTextoLongo";
import PetAvatar from "../../components/ui/PetAvatar";

const OPCOES_SEXO = [
  { value: "Macho", label: "Macho" },
  { value: "Fêmea", label: "Fêmea" },
];

const OPCOES_PORTE = [
  { value: "Mini", label: "Mini" },
  { value: "Pequeno", label: "Pequeno" },
  { value: "Médio", label: "Médio" },
  { value: "Grande", label: "Grande" },
  { value: "Gigante", label: "Gigante" },
];

// Aceita digitos com virgula ou ponto, igual ao InputQuantidade — mas sem forcar um minimo:
// peso do pet e uma caracteristica opcional, pode ficar em branco indefinidamente.
function aoDigitarPeso(bruto, setFormData) {
  if (bruto === "" || /^[0-9]*[.,]?[0-9]*$/.test(bruto)) {
    setFormData((prev) => ({ ...prev, peso: bruto }));
  }
}

export default function PetFormView({
  loading,
  isEditing,
  returnTo,
  navigate,
  petId,
  error,
  success,
  clienteIdPreSelecionado,
  handleSubmit,
  formData,
  setField,
  handleEspecieChange,
  clientes,
  abrirQuickAdd,
  especies,
  racas,
  especieSelecionadaAtual,
  setFormData,
  saving,
  showQuickAddModal,
  quickAddTipo,
  handleQuickAddSuccess,
  fecharQuickAdd,
}) {
  if (loading) {
    return (
      <div className="flex h-96 items-center justify-center">
        <div className="text-center">
          <div
            className="mx-auto h-12 w-12 animate-spin rounded-full border-b-2 border-blue-600 motion-reduce:animate-none"
            aria-hidden="true"
          />
          <p className="mt-4 text-gray-600">Carregando...</p>
        </div>
      </div>
    );
  }

  const opcoesClientes = clientes.map((cliente) => ({
    value: String(cliente.id),
    label: `${cliente.nome}${cliente.cpf ? ` - CPF: ${cliente.cpf}` : ""}`,
  }));
  const opcoesEspecies = especies.map((especie) => ({
    value: String(especie.id),
    label: especie.nome,
  }));
  const opcoesRacas = racas.map((raca) => ({ value: raca.nome, label: raca.nome }));

  const voltar = () => {
    if (!isEditing && returnTo) {
      navigate(returnTo);
      return;
    }
    navigate(isEditing ? `/pets/${petId}` : "/pets");
  };

  return (
    <div className="p-6">
      {/* Header */}
      <div className="mb-6">
        <BotaoLink onClick={voltar}>
          <span className="inline-flex items-center gap-2">
            <ArrowLeft size={14} aria-hidden="true" />
            {isEditing ? "Voltar para detalhes do pet" : "Voltar para lista de pets"}
          </span>
        </BotaoLink>

        <div className="mb-2 mt-4 flex items-center gap-3">
          <PawPrint className="text-blue-600" size={36} aria-hidden="true" />
          <h1 className="text-3xl font-bold text-gray-900">
            {isEditing ? "Editar Pet" : "Cadastrar Novo Pet"}
          </h1>
        </div>
        <p className="text-gray-600">
          {isEditing
            ? "Atualize as informações do pet"
            : "Preencha os dados do animal de estimação"}
        </p>
      </div>

      {/* Mensagens */}
      {error && (
        <div className="mb-6 flex items-center gap-2 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-red-700">
          <AlertCircle size={18} aria-hidden="true" />
          {error}
        </div>
      )}

      {success && (
        <div className="mb-6 flex items-center gap-2 rounded-lg border border-green-200 bg-green-50 px-4 py-3 text-green-700">
          <CheckCircle2 size={18} aria-hidden="true" />
          {success}
        </div>
      )}

      {/* Aviso de tutor pré-selecionado */}
      {clienteIdPreSelecionado && (
        <div className="mb-6 flex items-center gap-2 rounded-lg border border-blue-200 bg-blue-50 px-4 py-3 text-blue-700">
          <CheckCircle2 size={18} aria-hidden="true" />
          <span>Tutor pré-selecionado automaticamente! Você pode alterar se necessário.</span>
        </div>
      )}

      {/* Formulário */}
      <form onSubmit={handleSubmit} noValidate className="space-y-6">
        {/* Dados Básicos */}
        <div className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm">
          <h2 className="mb-4 text-xl font-bold text-gray-900">Dados Básicos</h2>

          <div className="grid grid-cols-2 gap-4">
            <div className="col-span-2">
              <InputCombobox
                id="pet-cliente"
                label="Cliente (Tutor)"
                opcoes={opcoesClientes}
                value={formData.cliente_id ? String(formData.cliente_id) : ""}
                onChange={setField("cliente_id")}
                placeholder="Selecione o tutor..."
                required
              />
              {clienteIdPreSelecionado && (
                <p className="mt-1 text-xs text-blue-600">Tutor selecionado automaticamente</p>
              )}
            </div>

            <div className="col-span-2">
              <InputTexto
                id="pet-nome"
                label="Nome do Pet"
                value={formData.nome}
                onChange={setField("nome")}
                required
                placeholder="Ex: Rex, Miau, Totó"
              />
            </div>

            <div>
              <div className="flex items-end gap-2">
                <div className="flex-1">
                  <InputCombobox
                    id="pet-especie"
                    label="Espécie"
                    opcoes={opcoesEspecies}
                    value={formData.especie}
                    onChange={handleEspecieChange}
                    placeholder="Selecione..."
                    required
                  />
                </div>
                <BotaoInteracao icon={Plus} onClick={() => abrirQuickAdd("especie")} tamanho="normal">
                  Nova
                </BotaoInteracao>
              </div>
              {especies.length === 0 && (
                <p className="mt-1 text-xs text-amber-800">
                  Nenhuma espécie cadastrada. Cadastre em Cadastros → Espécies e Raças.
                </p>
              )}
            </div>

            <div>
              <div className="flex items-end gap-2">
                <div className="flex-1">
                  <InputCombobox
                    id="pet-raca"
                    label="Raça"
                    opcoes={opcoesRacas}
                    value={formData.raca}
                    onChange={setField("raca")}
                    placeholder={
                      !formData.especie ? "Selecione uma espécie primeiro" : "Selecione uma raça..."
                    }
                    disabled={!formData.especie}
                  />
                </div>
                <BotaoInteracao
                  icon={Plus}
                  onClick={() => abrirQuickAdd("raca")}
                  tamanho="normal"
                  disabled={!formData.especie}
                >
                  Nova
                </BotaoInteracao>
              </div>
              {formData.especie && racas.length === 0 && (
                <p className="mt-1 text-xs text-amber-800">
                  Nenhuma raça cadastrada para{" "}
                  {especieSelecionadaAtual?.nome || "a espécie selecionada"}.
                </p>
              )}
            </div>

            <InputRadio
              name="sexo"
              label="Sexo"
              opcoes={OPCOES_SEXO}
              value={formData.sexo}
              onChange={setField("sexo")}
            />

            <div className="flex items-end">
              <InputCheckTexto
                id="pet-castrado"
                checked={formData.castrado}
                onChange={setField("castrado")}
              >
                Pet castrado
              </InputCheckTexto>
            </div>
          </div>
        </div>

        {/* Características Físicas */}
        <div className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm">
          <h2 className="mb-4 text-xl font-bold text-gray-900">Características Físicas</h2>

          <div className="grid grid-cols-2 gap-4">
            <CampoIdadeInteligente
              value={formData.idade_aproximada}
              onChange={(meses) =>
                setFormData((prev) => ({ ...prev, idade_aproximada: meses, data_nascimento: "" }))
              }
              name="idade_aproximada"
              label="Idade do Pet"
              mostrarDataNascimento={true}
              className="col-span-2"
            />

            <InputTexto
              id="pet-peso"
              label="Peso (kg)"
              value={formData.peso}
              onChange={(bruto) => aoDigitarPeso(bruto, setFormData)}
              inputMode="decimal"
              placeholder="Ex: 5.5"
            />

            <InputCombobox
              id="pet-porte"
              label="Porte"
              opcoes={OPCOES_PORTE}
              value={formData.porte}
              onChange={setField("porte")}
              placeholder="Selecione..."
            />

            <InputTexto
              id="pet-cor"
              label="Cor/Pelagem"
              value={formData.cor}
              onChange={setField("cor")}
              placeholder="Ex: Preto, Branco, Caramelo"
            />

            <InputTexto
              id="pet-microchip"
              label="Microchip"
              value={formData.microchip}
              onChange={setField("microchip")}
              placeholder="Número do microchip"
            />

            <InputTexto
              id="pet-tipo-sanguineo"
              label="Tipo sanguíneo"
              value={formData.tipo_sanguineo}
              onChange={setField("tipo_sanguineo")}
              placeholder="Ex: DEA 1.1, A, B"
            />

            <InputTexto
              id="pet-pedigree"
              label="Registro de pedigree"
              value={formData.pedigree_registro}
              onChange={setField("pedigree_registro")}
              placeholder="Código do registro, se houver"
            />

            <InputData
              id="pet-castrado-data"
              label="Data da castração"
              value={formData.castrado_data}
              onChange={setField("castrado_data")}
              disabled={!formData.castrado}
            />

            <div className="col-span-2 flex items-end gap-3">
              <div className="flex-1">
                <InputTexto
                  id="pet-foto-url"
                  label="URL da Foto"
                  type="url"
                  value={formData.foto_url}
                  onChange={setField("foto_url")}
                  placeholder="https://exemplo.com/foto-do-pet.jpg"
                />
              </div>
              <PetAvatar name={formData.nome} url={formData.foto_url} size="lg" />
            </div>
          </div>
        </div>

        {/* Informações de Saúde */}
        <div className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm">
          <h2 className="mb-4 text-xl font-bold text-gray-900">Informações de Saúde</h2>

          <div className="space-y-4">
            <InputTextoLongo
              id="pet-alergias"
              label="Alergias"
              help="Uma linha por item."
              value={formData.alergias}
              onChange={setField("alergias")}
              linhas={3}
              placeholder="Descreva alergias conhecidas (alimentares, medicamentos, etc)"
            />

            <InputTextoLongo
              id="pet-doencas-cronicas"
              label="Doenças Crônicas"
              help="Uma linha por condição registrada."
              value={formData.doencas_cronicas}
              onChange={setField("doencas_cronicas")}
              linhas={3}
              placeholder="Descreva doenças crônicas diagnosticadas"
            />

            <InputTextoLongo
              id="pet-medicamentos"
              label="Medicamentos Contínuos"
              help="Uma linha por medicamento, de preferência com dose."
              value={formData.medicamentos_continuos}
              onChange={setField("medicamentos_continuos")}
              linhas={3}
              placeholder="Liste medicamentos de uso contínuo com dosagem"
            />

            <InputTextoLongo
              id="pet-restricoes"
              label="Restrições alimentares"
              help="Uma linha por restrição, intolerância ou dieta especial."
              value={formData.restricoes_alimentares}
              onChange={setField("restricoes_alimentares")}
              linhas={3}
              placeholder="Ex: sem frango, dieta renal, alimento úmido controlado"
            />

            <InputTextoLongo
              id="pet-historico-clinico"
              label="Histórico Clínico"
              value={formData.historico_clinico}
              onChange={setField("historico_clinico")}
              linhas={4}
              placeholder="Descreva o histórico clínico do pet (cirurgias, tratamentos anteriores, etc)"
            />
          </div>
        </div>

        {/* Observações */}
        <div className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm">
          <h2 className="mb-4 text-xl font-bold text-gray-900">Observações Adicionais</h2>

          <div className="space-y-4">
            <InputTextoLongo
              id="pet-observacoes"
              label="Observações Gerais"
              value={formData.observacoes}
              onChange={setField("observacoes")}
              linhas={4}
              placeholder="Informações adicionais, comportamento, preferências, etc"
            />

            {isEditing && (
              <InputCheckTexto id="pet-ativo" checked={formData.ativo} onChange={setField("ativo")}>
                Pet ativo no sistema
              </InputCheckTexto>
            )}
          </div>
        </div>

        {/* Botões */}
        <div className="flex items-center gap-4">
          <BotaoSalva loading={saving} tamanho="grande">
            {isEditing ? "Salvar Alterações" : "Cadastrar Pet"}
          </BotaoSalva>

          <BotaoCancelar disabled={saving} onClick={voltar} tamanho="grande" />
        </div>
      </form>

      {/* Modal de Adicionar Rápido */}
      {showQuickAddModal && (
        <QuickAddModal
          tipo={quickAddTipo}
          especieId={quickAddTipo === "raca" ? Number.parseInt(formData.especie, 10) : null}
          especieNome={quickAddTipo === "raca" ? especieSelecionadaAtual?.nome : null}
          onSuccess={handleQuickAddSuccess}
          onClose={fecharQuickAdd}
        />
      )}
    </div>
  );
}
