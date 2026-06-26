import { useState } from "react";
import { Plus, Save, X } from "lucide-react";
import { formatarPrecoPorKg } from "../../utils/racaoPrecoKg";
import TabelaConsumoEditor from "../TabelaConsumoEditor";

export default function ProdutosNovoRacaoTab({
  formData,
  handleChange,
  handleApresentacaoPesoChange,
  handleClassificacaoRacaoChange,
  handleCriarOpcaoRacao,
  handleFasePublicoChange,
  opcoesApresentacoes,
  opcoesFases,
  opcoesLinhas,
  opcoesPortes,
  opcoesSabores,
  opcoesTratamentos,
}) {
  const [modalOpcao, setModalOpcao] = useState(null);
  const [nomeOpcao, setNomeOpcao] = useState("");
  const [pesoOpcao, setPesoOpcao] = useState("");
  const [descricaoOpcao, setDescricaoOpcao] = useState("");
  const [erroOpcao, setErroOpcao] = useState("");
  const [salvandoOpcao, setSalvandoOpcao] = useState(false);

  const linhaSelecionada = opcoesLinhas.find(
    (linha) => String(linha.id) === String(formData.linha_racao_id || ""),
  );
  const nomeLinhaSelecionada = linhaSelecionada?.nome || "";
  const quickAddDisponivel = typeof handleCriarOpcaoRacao === "function";
  const precoPorKgPreview = formatarPrecoPorKg(formData);

  const abrirModalOpcao = (tipo, titulo) => {
    setModalOpcao({ tipo, titulo });
    setNomeOpcao("");
    setPesoOpcao("");
    setDescricaoOpcao("");
    setErroOpcao("");
  };

  const fecharModalOpcao = () => {
    if (salvandoOpcao) return;
    setModalOpcao(null);
    setErroOpcao("");
  };

  const salvarOpcao = async () => {
    if (!modalOpcao || !quickAddDisponivel) return;
    setErroOpcao("");

    const isApresentacao = modalOpcao.tipo === "apresentacao";
    const nome = nomeOpcao.trim();
    const peso = Number(String(pesoOpcao).replace(",", "."));

    if (isApresentacao && (!Number.isFinite(peso) || peso <= 0)) {
      setErroOpcao("Informe um peso valido em kg.");
      return;
    }
    if (!isApresentacao && !nome) {
      setErroOpcao("Informe um nome.");
      return;
    }

    try {
      setSalvandoOpcao(true);
      await handleCriarOpcaoRacao(modalOpcao.tipo, {
        nome,
        peso_kg: peso,
        descricao: descricaoOpcao.trim() || null,
      });
      setModalOpcao(null);
    } catch (error) {
      const detalhe = error?.response?.data?.detail;
      setErroOpcao(typeof detalhe === "string" ? detalhe : "Nao foi possivel salvar agora.");
    } finally {
      setSalvandoOpcao(false);
    }
  };

  const LabelComNovo = ({ children, tipo, titulo, opcional = false }) => (
    <div className="mb-1 flex items-center justify-between gap-2">
      <label className="block text-sm font-medium text-gray-700">
        {children} {opcional && <span className="text-gray-400">(Opcional)</span>}
      </label>
      {quickAddDisponivel && (
        <button
          type="button"
          onClick={() => abrirModalOpcao(tipo, titulo)}
          className="inline-flex h-7 items-center gap-1 rounded-md border border-blue-200 bg-white px-2 text-xs font-semibold text-blue-700 hover:bg-blue-50"
        >
          <Plus className="h-3.5 w-3.5" />
          Novo
        </button>
      )}
    </div>
  );

  return (
    <div className="space-y-6">
      <div className="mb-6 border-l-4 border-orange-500 bg-orange-50 p-4">
        <div className="flex items-start">
          <div className="flex-shrink-0">
            <svg className="h-5 w-5 text-orange-400" viewBox="0 0 20 20" fill="currentColor">
              <path
                fillRule="evenodd"
                d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z"
                clipRule="evenodd"
              />
            </svg>
          </div>
          <div className="ml-3">
            <h3 className="text-sm font-medium text-orange-800">Calculadora de Racao (Fase 2)</h3>
            <div className="mt-2 text-sm text-orange-700">
              <p>Configure informacoes de racao para usar na calculadora de duracao e custo.</p>
              <p className="mt-1">A IA usara esses dados para recomendar racoes aos clientes.</p>
            </div>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        <div>
          <label className="mb-1 block text-sm font-medium text-gray-700">E racao?</label>
          <select
            value={formData.eh_racao ? "sim" : "nao"}
            onChange={(e) => handleClassificacaoRacaoChange(e.target.value)}
            className="w-full rounded-lg border border-gray-300 px-3 py-2 focus:border-transparent focus:ring-2 focus:ring-orange-500"
          >
            <option value="nao">Nao</option>
            <option value="sim">Sim</option>
          </select>
        </div>

        <div className="rounded-lg border border-slate-200 bg-slate-50 p-3">
          <label className="flex cursor-pointer items-start gap-3">
            <input
              type="checkbox"
              checked={Boolean(formData.e_granel)}
              onChange={(e) => {
                const marcado = e.target.checked;
                handleChange("e_granel", marcado);
                if (marcado) {
                  handleChange("eh_racao", true);
                  handleChange("unidade", "KG");
                }
              }}
              className="mt-1 h-4 w-4 rounded border-gray-300 text-orange-600 focus:ring-orange-500"
            />
            <span>
              <span className="block text-sm font-semibold text-slate-800">
                Produto vendido a granel
              </span>
              <span className="mt-1 block text-xs text-slate-600">
                O estoque fica em kg. O abastecimento parte do produto fechado em Movimentacoes.
              </span>
            </span>
          </label>
        </div>
      </div>

      {formData.e_granel && (
        <div className="rounded-lg border border-cyan-200 bg-cyan-50 p-4 text-sm text-cyan-800">
          Para abastecer este granel, abra o produto fechado de origem e use "Lancar granel". O
          sistema baixa pacote(s) do produto fechado e entra kg aqui usando o peso da embalagem da
          racao.
        </div>
      )}

      {formData.eh_racao && (
        <div className="border-l-4 border-blue-500 bg-blue-50 p-4">
          <h4 className="mb-4 text-sm font-semibold text-blue-900">
            Informacoes detalhadas da racao
          </h4>
          <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
            <div>
              <LabelComNovo tipo="linha" titulo="Nova linha">
                Linha
              </LabelComNovo>
              <select
                value={formData.linha_racao_id}
                onChange={(e) => {
                  const linhaId = e.target.value;
                  const linha = opcoesLinhas.find((item) => String(item.id) === String(linhaId));
                  handleChange("linha_racao_id", linhaId);
                  handleChange("classificacao_racao", linha?.nome || "");
                }}
                className="w-full rounded-lg border border-gray-300 px-3 py-2 focus:border-transparent focus:ring-2 focus:ring-blue-500"
              >
                <option value="">Selecione...</option>
                {opcoesLinhas.map((linha) => (
                  <option key={linha.id} value={linha.id}>
                    {linha.nome}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <LabelComNovo tipo="porte" titulo="Novo porte">
                Porte do animal
              </LabelComNovo>
              <select
                value={formData.porte_animal_id}
                onChange={(e) => handleChange("porte_animal_id", e.target.value)}
                className="w-full rounded-lg border border-gray-300 px-3 py-2 focus:border-transparent focus:ring-2 focus:ring-blue-500"
              >
                <option value="">Selecione...</option>
                {opcoesPortes.map((porte) => (
                  <option key={porte.id} value={porte.id}>
                    {porte.nome}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <LabelComNovo tipo="fase" titulo="Nova fase/publico">
                Fase/Publico
              </LabelComNovo>
              <select
                value={formData.fase_publico_id}
                onChange={(e) => handleFasePublicoChange(e.target.value)}
                className="w-full rounded-lg border border-gray-300 px-3 py-2 focus:border-transparent focus:ring-2 focus:ring-blue-500"
              >
                <option value="">Selecione...</option>
                {opcoesFases.map((fase) => (
                  <option key={fase.id} value={fase.id}>
                    {fase.nome}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <LabelComNovo tipo="tratamento" titulo="Novo tratamento" opcional>
                Tratamento
              </LabelComNovo>
              <select
                value={formData.tipo_tratamento_id}
                onChange={(e) => handleChange("tipo_tratamento_id", e.target.value)}
                className="w-full rounded-lg border border-gray-300 px-3 py-2 focus:border-transparent focus:ring-2 focus:ring-blue-500"
              >
                <option value="">Nenhum</option>
                {opcoesTratamentos.map((tratamento) => (
                  <option key={tratamento.id} value={tratamento.id}>
                    {tratamento.nome}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <LabelComNovo tipo="sabor" titulo="Novo sabor/proteina">
                Sabor/Proteina
              </LabelComNovo>
              <select
                value={formData.sabor_proteina_id}
                onChange={(e) => handleChange("sabor_proteina_id", e.target.value)}
                className="w-full rounded-lg border border-gray-300 px-3 py-2 focus:border-transparent focus:ring-2 focus:ring-blue-500"
              >
                <option value="">Selecione...</option>
                {opcoesSabores.map((sabor) => (
                  <option key={sabor.id} value={sabor.id}>
                    {sabor.nome}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <LabelComNovo tipo="apresentacao" titulo="Nova apresentacao">
                Apresentacao (Peso)
              </LabelComNovo>
              <select
                value={formData.apresentacao_peso_id}
                onChange={(e) => handleApresentacaoPesoChange(e.target.value)}
                className="w-full rounded-lg border border-gray-300 px-3 py-2 focus:border-transparent focus:ring-2 focus:ring-blue-500"
              >
                <option value="">Selecione...</option>
                {opcoesApresentacoes.map((apr) => (
                  <option key={apr.id} value={apr.id}>
                    {apr.peso_kg}kg
                  </option>
                ))}
              </select>
            </div>
          </div>

          <p className="mt-3 text-xs text-blue-600">
            <strong>Dica:</strong> Essas informacoes ajudam a IA a recomendar a racao ideal para
            cada pet no PDV. Voce pode gerenciar as opcoes disponiveis em{" "}
            <strong>Cadastros &gt; Opcoes de Racao</strong>.
          </p>
        </div>
      )}

      <div
        className="grid grid-cols-1 gap-4 md:grid-cols-2"
        style={{ display: formData.eh_racao ? undefined : "none" }}
      >
        <div>
          <label className="mb-2 block text-sm font-medium text-gray-700">Especies indicadas</label>
          <div className="flex gap-4">
            <label className="flex items-center">
              <input
                type="radio"
                name="especies_indicadas"
                value="both"
                checked={formData.especies_indicadas === "both"}
                onChange={(e) => handleChange("especies_indicadas", e.target.value)}
                className="h-4 w-4 border-gray-300 text-orange-600 focus:ring-orange-500"
              />
              <span className="ml-2 text-sm text-gray-700">Ambos</span>
            </label>
            <label className="flex items-center">
              <input
                type="radio"
                name="especies_indicadas"
                value="dog"
                checked={formData.especies_indicadas === "dog"}
                onChange={(e) => handleChange("especies_indicadas", e.target.value)}
                className="h-4 w-4 border-gray-300 text-orange-600 focus:ring-orange-500"
              />
              <span className="ml-2 text-sm text-gray-700">Caes</span>
            </label>
            <label className="flex items-center">
              <input
                type="radio"
                name="especies_indicadas"
                value="cat"
                checked={formData.especies_indicadas === "cat"}
                onChange={(e) => handleChange("especies_indicadas", e.target.value)}
                className="h-4 w-4 border-gray-300 text-orange-600 focus:ring-orange-500"
              />
              <span className="ml-2 text-sm text-gray-700">Gatos</span>
            </label>
          </div>
        </div>
      </div>

      <input type="hidden" value={formData.tabela_nutricional} readOnly />

      <div style={{ display: formData.eh_racao ? undefined : "none" }}>
        <TabelaConsumoEditor
          value={formData.tabela_consumo}
          onChange={(value) => handleChange("tabela_consumo", value)}
          pesoEmbalagem={parseFloat(formData.peso_embalagem) || null}
        />
      </div>

      {formData.eh_racao && formData.peso_embalagem && nomeLinhaSelecionada && (
        <div className="rounded-lg border border-orange-200 bg-orange-50 p-4">
          <h4 className="mb-2 text-sm font-semibold text-orange-900">Preview da calculadora</h4>
          <div className="space-y-1 text-sm text-orange-700">
            <p>
              Peso: <strong>{formData.peso_embalagem}kg</strong>
            </p>
            {precoPorKgPreview && (
              <p>
                Preco/kg: <strong>{precoPorKgPreview}</strong>
              </p>
            )}
            <p>
              Linha: <strong>{nomeLinhaSelecionada}</strong>
            </p>
            {formData.categoria_racao && (
              <p>
                Categoria: <strong>{formData.categoria_racao}</strong>
              </p>
            )}
            {formData.tabela_consumo ? (
              <p className="text-green-600">Tabela de consumo configurada</p>
            ) : (
              <p className="text-yellow-600">Sem tabela de consumo (usara calculo generico)</p>
            )}
            <p className="mt-2 text-orange-800">
              Use a Calculadora de Racao para ver duracao e custo/dia.
            </p>
          </div>
        </div>
      )}

      {modalOpcao && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/45 p-4">
          <div className="w-full max-w-md rounded-lg bg-white shadow-xl">
            <div className="flex items-center justify-between border-b border-slate-200 px-5 py-4">
              <div>
                <h3 className="text-base font-semibold text-slate-900">{modalOpcao.titulo}</h3>
                <p className="text-sm text-slate-500">Cadastro rapido para este produto</p>
              </div>
              <button
                type="button"
                onClick={fecharModalOpcao}
                className="rounded-md p-1 text-slate-500 hover:bg-slate-100 hover:text-slate-700"
                aria-label="Fechar"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            <div className="space-y-4 px-5 py-4">
              {modalOpcao.tipo === "apresentacao" ? (
                <div>
                  <label className="mb-1 block text-sm font-medium text-slate-700">
                    Peso em kg
                  </label>
                  <input
                    type="number"
                    step="0.01"
                    min="0"
                    value={pesoOpcao}
                    onChange={(e) => setPesoOpcao(e.target.value)}
                    className="w-full rounded-lg border border-slate-300 px-3 py-2 focus:border-transparent focus:ring-2 focus:ring-blue-500"
                    placeholder="Ex: 10.1"
                    autoFocus
                  />
                </div>
              ) : (
                <div>
                  <label className="mb-1 block text-sm font-medium text-slate-700">Nome</label>
                  <input
                    type="text"
                    value={nomeOpcao}
                    onChange={(e) => setNomeOpcao(e.target.value)}
                    className="w-full rounded-lg border border-slate-300 px-3 py-2 focus:border-transparent focus:ring-2 focus:ring-blue-500"
                    placeholder="Digite o nome"
                    autoFocus
                  />
                </div>
              )}

              <div>
                <label className="mb-1 block text-sm font-medium text-slate-700">Descricao</label>
                <input
                  type="text"
                  value={descricaoOpcao}
                  onChange={(e) => setDescricaoOpcao(e.target.value)}
                  className="w-full rounded-lg border border-slate-300 px-3 py-2 focus:border-transparent focus:ring-2 focus:ring-blue-500"
                  placeholder="Opcional"
                />
              </div>

              {erroOpcao && (
                <div className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
                  {erroOpcao}
                </div>
              )}
            </div>

            <div className="flex justify-end gap-3 border-t border-slate-200 px-5 py-4">
              <button
                type="button"
                onClick={fecharModalOpcao}
                className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-50"
                disabled={salvandoOpcao}
              >
                Cancelar
              </button>
              <button
                type="button"
                onClick={salvarOpcao}
                className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-60"
                disabled={salvandoOpcao}
              >
                <Save className="h-4 w-4" />
                {salvandoOpcao ? "Salvando..." : "Salvar"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
