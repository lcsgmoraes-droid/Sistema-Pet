import React, { useEffect, useState } from "react";
import api from "../../api";

const OPCOES_CATEGORIA_RACAO = [
  { value: "filhote", label: "Filhote" },
  { value: "adulto", label: "Adulto" },
  { value: "senior", label: "Senior" },
  { value: "gestante", label: "Gestante" },
  { value: "castrado", label: "Castrado" },
  { value: "terapeutica", label: "Terapeutica" },
  { value: "todas", label: "Todas" },
];

const OPCOES_ESPECIES = [
  { value: "both", label: "Caes e gatos" },
  { value: "dog", label: "Caes" },
  { value: "cat", label: "Gatos" },
  { value: "bird", label: "Passaros" },
  { value: "rodent", label: "Roedores" },
  { value: "fish", label: "Peixes" },
];

function CampoSelect({ label, value, onChange, children }) {
  return (
    <div>
      <label className="mb-1 block text-sm font-medium text-gray-700">{label}</label>
      <select
        value={value}
        onChange={onChange}
        className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-100"
      >
        {children}
      </select>
    </div>
  );
}

function CampoNumero({ label, value, onChange, placeholder }) {
  return (
    <div>
      <label className="mb-1 block text-sm font-medium text-gray-700">{label}</label>
      <input
        type="number"
        min="0"
        step="0.001"
        value={value}
        onChange={onChange}
        placeholder={placeholder}
        className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-100"
      />
    </div>
  );
}

export default function ProdutosEdicaoLoteModal({
  categorias,
  dadosEdicaoLote,
  departamentos,
  isOpen,
  marcas,
  onClose,
  onSalvar,
  selecionadosCount,
  setDadosEdicaoLote,
}) {
  const [loadingOpcoesRacao, setLoadingOpcoesRacao] = useState(false);
  const [opcoesRacao, setOpcoesRacao] = useState({
    linhas: [],
    portes: [],
    fases: [],
    tratamentos: [],
    sabores: [],
    apresentacoes: [],
  });

  useEffect(() => {
    if (!isOpen) return;

    let ativo = true;

    const carregarOpcoesRacao = async () => {
      try {
        setLoadingOpcoesRacao(true);
        const [linhas, portes, fases, tratamentos, sabores, apresentacoes] =
          await Promise.all([
            api.get("/opcoes-racao/linhas", { params: { apenas_ativos: true } }),
            api.get("/opcoes-racao/portes", { params: { apenas_ativos: true } }),
            api.get("/opcoes-racao/fases", { params: { apenas_ativos: true } }),
            api.get("/opcoes-racao/tratamentos", { params: { apenas_ativos: true } }),
            api.get("/opcoes-racao/sabores", { params: { apenas_ativos: true } }),
            api.get("/opcoes-racao/apresentacoes", { params: { apenas_ativos: true } }),
          ]);

        if (!ativo) return;

        setOpcoesRacao({
          linhas: linhas.data || [],
          portes: portes.data || [],
          fases: fases.data || [],
          tratamentos: tratamentos.data || [],
          sabores: sabores.data || [],
          apresentacoes: apresentacoes.data || [],
        });
      } catch (error) {
        console.error("Erro ao carregar opcoes de racao para edicao em lote:", error);
      } finally {
        if (ativo) {
          setLoadingOpcoesRacao(false);
        }
      }
    };

    void carregarOpcoesRacao();

    return () => {
      ativo = false;
    };
  }, [isOpen]);

  if (!isOpen) return null;

  const atualizarCampo = (campo, valor) => {
    setDadosEdicaoLote((prev) => {
      const proximoEstado = {
        ...prev,
        [campo]: valor,
      };

      if (campo === "eh_racao" && valor === "false") {
        proximoEstado.linha_racao_id = "";
        proximoEstado.porte_animal_id = "";
        proximoEstado.fase_publico_id = "";
        proximoEstado.tipo_tratamento_id = "";
        proximoEstado.sabor_proteina_id = "";
        proximoEstado.apresentacao_peso_id = "";
        proximoEstado.categoria_racao = "";
        proximoEstado.especies_indicadas = "";
      }

      return proximoEstado;
    });
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50 p-4">
      <div className="flex max-h-[92vh] w-full max-w-5xl flex-col overflow-hidden rounded-2xl bg-white shadow-xl">
        <div className="flex items-center justify-between border-b border-gray-100 px-6 py-4">
          <div>
            <h2 className="text-xl font-bold text-gray-900">Editar em lote</h2>
            <p className="mt-1 text-sm text-gray-600">
              Atualizar <strong>{selecionadosCount}</strong> produto(s) selecionado(s)
            </p>
          </div>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
            <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M6 18L18 6M6 6l12 12"
              />
            </svg>
          </button>
        </div>

        <div className="space-y-6 overflow-y-auto px-6 py-5">
          <section className="space-y-4">
            <div className="flex items-center justify-between gap-3">
              <div>
                <h3 className="text-sm font-semibold uppercase tracking-wide text-gray-800">
                  Cadastro base
                </h3>
                <p className="text-xs text-gray-500">
                  Marca, categoria e area de estoque para o grupo selecionado.
                </p>
              </div>
            </div>

            <div className="grid gap-4 md:grid-cols-3">
              <CampoSelect
                label="Marca"
                value={dadosEdicaoLote.marca_id}
                onChange={(event) => atualizarCampo("marca_id", event.target.value)}
              >
                <option value="">Nao alterar</option>
                {marcas.map((marca) => (
                  <option key={marca.id} value={marca.id}>
                    {marca.nome}
                  </option>
                ))}
              </CampoSelect>

              <CampoSelect
                label="Categoria"
                value={dadosEdicaoLote.categoria_id}
                onChange={(event) => atualizarCampo("categoria_id", event.target.value)}
              >
                <option value="">Nao alterar</option>
                {categorias.map((cat) => (
                  <option key={cat.id} value={cat.id}>
                    {cat.categoria_pai_id ? "-> " : ""}
                    {cat.nome}
                  </option>
                ))}
              </CampoSelect>

              <CampoSelect
                label="Area / setor"
                value={dadosEdicaoLote.departamento_id}
                onChange={(event) => atualizarCampo("departamento_id", event.target.value)}
              >
                <option value="">Nao alterar</option>
                {departamentos.map((dep) => (
                  <option key={dep.id} value={dep.id}>
                    {dep.nome}
                  </option>
                ))}
              </CampoSelect>
            </div>
          </section>

          <section className="space-y-4 rounded-2xl border border-blue-100 bg-blue-50/60 p-4">
            <div>
              <h3 className="text-sm font-semibold uppercase tracking-wide text-blue-900">
                Campos de racao
              </h3>
              <p className="text-xs text-blue-800">
                Ideal para padronizar linha, publico e atributos usados em comparacoes e filtros.
              </p>
            </div>

            {loadingOpcoesRacao ? (
              <p className="text-sm text-blue-900">Carregando opcoes de racao...</p>
            ) : (
              <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
                <CampoSelect
                  label="E racao?"
                  value={dadosEdicaoLote.eh_racao}
                  onChange={(event) => atualizarCampo("eh_racao", event.target.value)}
                >
                  <option value="">Nao alterar</option>
                  <option value="true">Sim</option>
                  <option value="false">Nao</option>
                </CampoSelect>

                <CampoSelect
                  label="Linha"
                  value={dadosEdicaoLote.linha_racao_id}
                  onChange={(event) => atualizarCampo("linha_racao_id", event.target.value)}
                >
                  <option value="">Nao alterar</option>
                  {opcoesRacao.linhas.map((item) => (
                    <option key={item.id} value={item.id}>
                      {item.nome}
                    </option>
                  ))}
                </CampoSelect>

                <CampoSelect
                  label="Porte"
                  value={dadosEdicaoLote.porte_animal_id}
                  onChange={(event) => atualizarCampo("porte_animal_id", event.target.value)}
                >
                  <option value="">Nao alterar</option>
                  {opcoesRacao.portes.map((item) => (
                    <option key={item.id} value={item.id}>
                      {item.nome}
                    </option>
                  ))}
                </CampoSelect>

                <CampoSelect
                  label="Fase / publico"
                  value={dadosEdicaoLote.fase_publico_id}
                  onChange={(event) => atualizarCampo("fase_publico_id", event.target.value)}
                >
                  <option value="">Nao alterar</option>
                  {opcoesRacao.fases.map((item) => (
                    <option key={item.id} value={item.id}>
                      {item.nome}
                    </option>
                  ))}
                </CampoSelect>

                <CampoSelect
                  label="Tratamento"
                  value={dadosEdicaoLote.tipo_tratamento_id}
                  onChange={(event) => atualizarCampo("tipo_tratamento_id", event.target.value)}
                >
                  <option value="">Nao alterar</option>
                  {opcoesRacao.tratamentos.map((item) => (
                    <option key={item.id} value={item.id}>
                      {item.nome}
                    </option>
                  ))}
                </CampoSelect>

                <CampoSelect
                  label="Sabor / proteina"
                  value={dadosEdicaoLote.sabor_proteina_id}
                  onChange={(event) => atualizarCampo("sabor_proteina_id", event.target.value)}
                >
                  <option value="">Nao alterar</option>
                  {opcoesRacao.sabores.map((item) => (
                    <option key={item.id} value={item.id}>
                      {item.nome}
                    </option>
                  ))}
                </CampoSelect>

                <CampoSelect
                  label="Apresentacao"
                  value={dadosEdicaoLote.apresentacao_peso_id}
                  onChange={(event) => atualizarCampo("apresentacao_peso_id", event.target.value)}
                >
                  <option value="">Nao alterar</option>
                  {opcoesRacao.apresentacoes.map((item) => (
                    <option key={item.id} value={item.id}>
                      {item.nome || `${item.peso_kg}kg`}
                    </option>
                  ))}
                </CampoSelect>

                <CampoSelect
                  label="Categoria da racao"
                  value={dadosEdicaoLote.categoria_racao}
                  onChange={(event) => atualizarCampo("categoria_racao", event.target.value)}
                >
                  <option value="">Nao alterar</option>
                  {OPCOES_CATEGORIA_RACAO.map((item) => (
                    <option key={item.value} value={item.value}>
                      {item.label}
                    </option>
                  ))}
                </CampoSelect>

                <CampoSelect
                  label="Especies indicadas"
                  value={dadosEdicaoLote.especies_indicadas}
                  onChange={(event) => atualizarCampo("especies_indicadas", event.target.value)}
                >
                  <option value="">Nao alterar</option>
                  {OPCOES_ESPECIES.map((item) => (
                    <option key={item.value} value={item.value}>
                      {item.label}
                    </option>
                  ))}
                </CampoSelect>
              </div>
            )}
          </section>

          <section className="space-y-4">
            <div>
              <h3 className="text-sm font-semibold uppercase tracking-wide text-gray-800">
                Estoque e operacao
              </h3>
              <p className="text-xs text-gray-500">
                Campos uteis para padronizar controle de lote e alertas de reposicao.
              </p>
            </div>

            <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
              <CampoSelect
                label="Controle de lote"
                value={dadosEdicaoLote.controle_lote}
                onChange={(event) => atualizarCampo("controle_lote", event.target.value)}
              >
                <option value="">Nao alterar</option>
                <option value="true">Ativar</option>
                <option value="false">Desativar</option>
              </CampoSelect>

              <CampoNumero
                label="Estoque minimo"
                value={dadosEdicaoLote.estoque_minimo}
                onChange={(event) => atualizarCampo("estoque_minimo", event.target.value)}
                placeholder="Ex.: 5"
              />

              <CampoNumero
                label="Estoque maximo"
                value={dadosEdicaoLote.estoque_maximo}
                onChange={(event) => atualizarCampo("estoque_maximo", event.target.value)}
                placeholder="Ex.: 30"
              />
            </div>
          </section>

          <section className="space-y-4 border-t border-gray-100 pt-4">
            <div>
              <h3 className="text-sm font-semibold uppercase tracking-wide text-gray-800">
                Canais de venda
              </h3>
              <p className="text-xs text-gray-500">
                Se o produto estiver inativo na loja fisica, os canais continuam sendo desligados automaticamente.
              </p>
            </div>

            <div className="grid gap-4 md:grid-cols-2">
              <CampoSelect
                label="E-commerce"
                value={dadosEdicaoLote.anunciar_ecommerce}
                onChange={(event) => atualizarCampo("anunciar_ecommerce", event.target.value)}
              >
                <option value="">Nao alterar</option>
                <option value="true">Ativar</option>
                <option value="false">Desativar</option>
              </CampoSelect>

              <CampoSelect
                label="App movel"
                value={dadosEdicaoLote.anunciar_app}
                onChange={(event) => atualizarCampo("anunciar_app", event.target.value)}
              >
                <option value="">Nao alterar</option>
                <option value="true">Ativar</option>
                <option value="false">Desativar</option>
              </CampoSelect>
            </div>
          </section>
        </div>

        <div className="flex gap-3 border-t border-gray-100 px-6 py-4">
          <button
            onClick={onClose}
            className="flex-1 rounded-lg border border-gray-300 px-4 py-2 text-gray-700 transition-colors hover:bg-gray-50"
          >
            Cancelar
          </button>
          <button
            onClick={onSalvar}
            className="flex-1 rounded-lg bg-blue-600 px-4 py-2 font-medium text-white transition-colors hover:bg-blue-700"
          >
            Salvar alteracoes
          </button>
        </div>
      </div>
    </div>
  );
}
