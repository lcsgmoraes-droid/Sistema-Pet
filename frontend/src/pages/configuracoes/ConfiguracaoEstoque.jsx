import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../../services/api";
import toast from "react-hot-toast";
import { FiChevronLeft, FiAlertTriangle, FiSave, FiShield } from "react-icons/fi";

export default function ConfiguracaoEstoque() {
  const [loading, setLoading] = useState(true);
  const [salvando, setSalvando] = useState(false);
  const [permiteEstoqueNegativo, setPermiteEstoqueNegativo] = useState(false);
  const [protecaoValidadeAtiva, setProtecaoValidadeAtiva] = useState(false);
  const [diasAlertaValidade, setDiasAlertaValidade] = useState(15);
  const [bloquearValidadePdv, setBloquearValidadePdv] = useState(true);
  const [bloquearValidadeEcommerce, setBloquearValidadeEcommerce] = useState(true);
  const [bloquearValidadeIntegracoesOnline, setBloquearValidadeIntegracoesOnline] = useState(false);

  useEffect(() => {
    async function carregar() {
      try {
        const res = await api.get("/empresa/config-estoque");
        setPermiteEstoqueNegativo(res.data.permite_estoque_negativo);
        setProtecaoValidadeAtiva(Boolean(res.data.protecao_validade_ativa));
        setDiasAlertaValidade(res.data.dias_alerta_validade || 15);
        setBloquearValidadePdv(res.data.bloquear_validade_pdv ?? true);
        setBloquearValidadeEcommerce(res.data.bloquear_validade_ecommerce ?? true);
        setBloquearValidadeIntegracoesOnline(Boolean(res.data.bloquear_validade_integracoes_online));
      } catch (e) {
        console.error("Erro ao carregar configurações de estoque", e);
        toast.error("Erro ao carregar configurações");
      } finally {
        setLoading(false);
      }
    }
    carregar();
  }, []);

  async function handleSalvar() {
    setSalvando(true);
    try {
      await api.put("/empresa/config-estoque", {
        permite_estoque_negativo: permiteEstoqueNegativo,
        protecao_validade_ativa: protecaoValidadeAtiva,
        dias_alerta_validade: Number(diasAlertaValidade) || 15,
        bloquear_validade_pdv: bloquearValidadePdv,
        bloquear_validade_ecommerce: bloquearValidadeEcommerce,
        bloquear_validade_integracoes_online: bloquearValidadeIntegracoesOnline
      });
      toast.success("Configurações de estoque atualizadas com sucesso!");
    } catch (e) {
      console.error("Erro ao salvar configurações", e);
      toast.error("Erro ao salvar configurações");
    } finally {
      setSalvando(false);
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">Carregando configurações...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 max-w-4xl mx-auto">
      {/* Cabeçalho */}
      <div className="mb-6">
        <Link
          to="/configuracoes"
          className="inline-flex items-center text-blue-600 hover:text-blue-700 mb-4"
        >
          <FiChevronLeft className="mr-1" />
          Voltar para Configurações
        </Link>
        <h1 className="text-3xl font-bold text-gray-900">Configurações de Estoque</h1>
        <p className="text-gray-600 mt-2">
          Configure o comportamento do controle de estoque do sistema
        </p>
      </div>

      {/* Card de Configuração */}
      <div className="bg-white rounded-lg shadow-md p-6">
        <div className="mb-6">
          <h2 className="text-xl font-semibold text-gray-800 mb-4">
            Controle de Estoque Negativo
          </h2>
          
          <div className="bg-yellow-50 border-l-4 border-yellow-400 p-4 mb-6">
            <div className="flex items-start">
              <FiAlertTriangle className="text-yellow-600 mt-1 mr-3 flex-shrink-0" />
              <div>
                <p className="text-sm text-gray-700">
                  <strong>Atenção:</strong> Esta configuração afeta diretamente o controle de vendas e estoque.
                </p>
              </div>
            </div>
          </div>

          <div className="space-y-4">
            <label className="flex items-start p-4 border-2 border-gray-200 rounded-lg cursor-pointer hover:bg-gray-50 transition-colors">
              <input
                type="radio"
                name="estoque-negativo"
                checked={!permiteEstoqueNegativo}
                onChange={() => setPermiteEstoqueNegativo(false)}
                className="mt-1 mr-3 text-blue-600 focus:ring-blue-500"
              />
              <div className="flex-1">
                <div className="font-semibold text-gray-900">
                  🔒 Bloquear vendas sem estoque (Recomendado)
                </div>
                <div className="text-sm text-gray-600 mt-1">
                  O sistema impedirá finalizar vendas quando não houver estoque suficiente. 
                  Ideal para controle rigoroso de estoque.
                </div>
              </div>
            </label>

            <label className="flex items-start p-4 border-2 border-gray-200 rounded-lg cursor-pointer hover:bg-gray-50 transition-colors">
              <input
                type="radio"
                name="estoque-negativo"
                checked={permiteEstoqueNegativo}
                onChange={() => setPermiteEstoqueNegativo(true)}
                className="mt-1 mr-3 text-blue-600 focus:ring-blue-500"
              />
              <div className="flex-1">
                <div className="font-semibold text-gray-900">
                  ✅ Permitir estoque negativo
                </div>
                <div className="text-sm text-gray-600 mt-1">
                  O sistema permitirá vendas mesmo sem estoque disponível. 
                  Útil para negócios que trabalham com encomendas ou reposição rápida.
                </div>
                <div className="text-xs text-red-600 mt-2 font-medium">
                  ⚠️ Use com cuidado: pode gerar descontinuidade no controle de estoque
                </div>
              </div>
            </label>
          </div>
        </div>

        {/* Botão Salvar */}
        <div className="pt-6 mt-6 border-t">
          <div className="flex items-start gap-3 mb-5">
            <div className="inline-flex h-10 w-10 items-center justify-center rounded-lg bg-emerald-50 text-emerald-700">
              <FiShield />
            </div>
            <div>
              <h2 className="text-xl font-semibold text-gray-800">
                Protecao por validade
              </h2>
              <p className="text-sm text-gray-600 mt-1">
                Remove do saldo vendavel os lotes proximos do vencimento e cria pendencias para decisao.
              </p>
            </div>
          </div>

          <div className="space-y-4">
            <label className="flex items-start p-4 border-2 border-gray-200 rounded-lg cursor-pointer hover:bg-gray-50 transition-colors">
              <input
                type="checkbox"
                checked={protecaoValidadeAtiva}
                onChange={(e) => setProtecaoValidadeAtiva(e.target.checked)}
                className="mt-1 mr-3 text-blue-600 focus:ring-blue-500"
              />
              <div className="flex-1">
                <div className="font-semibold text-gray-900">
                  Ativar protecao automatica
                </div>
                <div className="text-sm text-gray-600 mt-1">
                  Produtos em risco saem do estoque vendavel ate serem descartados, trocados ou retornados.
                </div>
              </div>
            </label>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <label className="block">
                <span className="text-sm font-medium text-gray-700">
                  Dias antes do vencimento
                </span>
                <input
                  type="number"
                  min="1"
                  max="365"
                  value={diasAlertaValidade}
                  onChange={(e) => setDiasAlertaValidade(e.target.value)}
                  disabled={!protecaoValidadeAtiva}
                  className="mt-2 w-full rounded-lg border border-gray-300 px-3 py-2 text-gray-900 focus:border-blue-500 focus:ring-blue-500 disabled:bg-gray-100 disabled:text-gray-500"
                />
              </label>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
              <label className="flex items-start p-3 border border-gray-200 rounded-lg cursor-pointer hover:bg-gray-50">
                <input
                  type="checkbox"
                  checked={bloquearValidadePdv}
                  onChange={(e) => setBloquearValidadePdv(e.target.checked)}
                  disabled={!protecaoValidadeAtiva}
                  className="mt-1 mr-3 text-blue-600 focus:ring-blue-500 disabled:opacity-50"
                />
                <span className="text-sm font-medium text-gray-800">Alertar no PDV</span>
              </label>

              <label className="flex items-start p-3 border border-gray-200 rounded-lg cursor-pointer hover:bg-gray-50">
                <input
                  type="checkbox"
                  checked={bloquearValidadeEcommerce}
                  onChange={(e) => setBloquearValidadeEcommerce(e.target.checked)}
                  disabled={!protecaoValidadeAtiva}
                  className="mt-1 mr-3 text-blue-600 focus:ring-blue-500 disabled:opacity-50"
                />
                <span className="text-sm font-medium text-gray-800">Bloquear ecommerce</span>
              </label>

              <label className="flex items-start p-3 border border-gray-200 rounded-lg cursor-pointer hover:bg-gray-50">
                <input
                  type="checkbox"
                  checked={bloquearValidadeIntegracoesOnline}
                  onChange={(e) => setBloquearValidadeIntegracoesOnline(e.target.checked)}
                  disabled={!protecaoValidadeAtiva}
                  className="mt-1 mr-3 text-blue-600 focus:ring-blue-500 disabled:opacity-50"
                />
                <span className="text-sm font-medium text-gray-800">Bloquear integracoes</span>
              </label>
            </div>
          </div>
        </div>

        <div className="flex justify-end pt-4 mt-6 border-t">
          <button
            onClick={handleSalvar}
            disabled={salvando}
            className="inline-flex items-center px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors font-medium"
          >
            <FiSave className="mr-2" />
            {salvando ? "Salvando..." : "Salvar Configurações"}
          </button>
        </div>
      </div>

      {/* Informações Adicionais */}
      <div className="mt-6 bg-blue-50 border border-blue-200 rounded-lg p-4">
        <h3 className="font-semibold text-blue-900 mb-2">💡 Como funciona?</h3>
        <ul className="text-sm text-blue-800 space-y-1 list-disc list-inside">
          <li>
            <strong>Estoque Bloqueado:</strong> Ao tentar vender um produto sem estoque, 
            o sistema exibirá um erro e impedirá a finalização da venda.
          </li>
          <li>
            <strong>Estoque Negativo:</strong> O sistema permite a venda e o estoque 
            ficará com valor negativo até a próxima reposição.
          </li>
          <li>
            Esta configuração é global e afeta todas as vendas realizadas no PDV e 
            outros pontos de venda.
          </li>
        </ul>
      </div>
    </div>
  );
}
