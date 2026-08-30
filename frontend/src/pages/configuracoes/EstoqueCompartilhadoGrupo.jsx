import { useCallback, useEffect, useMemo, useState } from "react";
import toast from "react-hot-toast";
import { FiPackage, FiSearch, FiShare2, FiTrash2 } from "react-icons/fi";
import ActionButton from "../../components/ui/ActionButton";
import { confirmarCorePet } from "../../services/corepetDialog";
import {
  buscarProdutosEstoqueCompartilhado,
  atualizarAcessoCatalogoCompartilhado,
  compartilharEstoqueGrupo,
  listarEstoqueCompartilhadoGrupo,
  removerEstoqueCompartilhadoGrupo,
} from "../../services/gruposEmpresas";

function mensagemErro(error, padrao) {
  return error?.response?.data?.detail || padrao;
}

function formatarEstoque(valor) {
  return new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 3 }).format(Number(valor || 0));
}

export default function EstoqueCompartilhadoGrupo({ empresaAtualId, grupo }) {
  const destinos = useMemo(
    () => grupo.membros.filter((membro) => membro.empresa_id !== empresaAtualId),
    [empresaAtualId, grupo.membros],
  );
  const [destinoId, setDestinoId] = useState(destinos[0]?.empresa_id || "");
  const [busca, setBusca] = useState("");
  const [produtos, setProdutos] = useState([]);
  const [compartilhamentos, setCompartilhamentos] = useState([]);
  const [selecionados, setSelecionados] = useState(new Set());
  const [carregando, setCarregando] = useState(false);
  const [acao, setAcao] = useState("");
  const [acessoCatalogoCompleto, setAcessoCatalogoCompleto] = useState(false);

  const carregarCompartilhamentos = useCallback(async () => {
    try {
      setCompartilhamentos(await listarEstoqueCompartilhadoGrupo(grupo.id));
    } catch (error) {
      toast.error(mensagemErro(error, "Não foi possível consultar o estoque compartilhado."));
    }
  }, [grupo.id]);

  const buscarProdutos = useCallback(async () => {
    if (!destinoId) return;
    setCarregando(true);
    try {
      const data = await buscarProdutosEstoqueCompartilhado(grupo.id, {
        empresa_consumidora_id: destinoId,
        busca: busca.trim(),
        limite: 100,
      });
      setProdutos(data);
      setSelecionados(new Set());
    } catch (error) {
      toast.error(mensagemErro(error, "Não foi possível buscar os produtos desta empresa."));
    } finally {
      setCarregando(false);
    }
  }, [busca, destinoId, grupo.id]);

  useEffect(() => {
    carregarCompartilhamentos();
  }, [carregarCompartilhamentos]);

  useEffect(() => {
    if (!destinoId) return undefined;
    let ativo = true;
    setCarregando(true);
    buscarProdutosEstoqueCompartilhado(grupo.id, {
      empresa_consumidora_id: destinoId,
      busca: "",
      limite: 100,
    })
      .then((data) => {
        if (ativo) {
          setProdutos(data);
          setSelecionados(new Set());
        }
      })
      .catch((error) => {
        if (ativo) {
          toast.error(mensagemErro(error, "Não foi possível buscar os produtos desta empresa."));
        }
      })
      .finally(() => {
        if (ativo) setCarregando(false);
      });
    return () => {
      ativo = false;
    };
  }, [destinoId, grupo.id]);

  function alternarProduto(produtoId) {
    setSelecionados((atual) => {
      const proximo = new Set(atual);
      if (proximo.has(produtoId)) proximo.delete(produtoId);
      else proximo.add(produtoId);
      return proximo;
    });
  }

  async function compartilharSelecionados() {
    const ids = Array.from(selecionados);
    if (!ids.length) {
      toast.error("Selecione ao menos um produto.");
      return;
    }
    const destino = destinos.find((item) => item.empresa_id === destinoId);
    if (
      !(await confirmarCorePet(
        `Autorizar ${destino?.empresa_nome || "a outra empresa"} a ${
          acessoCatalogoCompleto
            ? "vender o saldo e editar o cadastro completo de"
            : "vender o saldo de"
        } ${ids.length} produto(s)?`,
      ))
    ) {
      return;
    }
    setAcao("compartilhar");
    try {
      await compartilharEstoqueGrupo(grupo.id, destinoId, ids, acessoCatalogoCompleto);
      toast.success("Estoque autorizado para a empresa selecionada.");
      await Promise.all([buscarProdutos(), carregarCompartilhamentos()]);
    } catch (error) {
      toast.error(mensagemErro(error, "Não foi possível compartilhar os produtos."));
    } finally {
      setAcao("");
    }
  }

  async function alternarAcessoCatalogo(item) {
    const proximo = !item.acesso_catalogo_completo;
    const acaoLabel = proximo ? "liberar" : "retirar";
    if (
      !(await confirmarCorePet(
        `${acaoLabel === "liberar" ? "Liberar" : "Retirar"} acesso completo ao cadastro de ${
          item.produto_nome
        } para ${item.empresa_consumidora_nome}? O compartilhamento do saldo continuará ativo.`,
      ))
    ) {
      return;
    }
    setAcao(`catalogo-${item.id}`);
    try {
      await atualizarAcessoCatalogoCompartilhado(grupo.id, item.id, proximo);
      toast.success(
        proximo ? "Acesso completo ao catálogo liberado." : "Acesso ao catálogo retirado.",
      );
      await Promise.all([buscarProdutos(), carregarCompartilhamentos()]);
    } catch (error) {
      toast.error(mensagemErro(error, "Não foi possível atualizar o acesso ao catálogo."));
    } finally {
      setAcao("");
    }
  }

  async function remover(item) {
    if (!(await confirmarCorePet(`Parar de compartilhar o saldo de ${item.produto_nome}?`))) return;
    setAcao(`remover-${item.id}`);
    try {
      await removerEstoqueCompartilhadoGrupo(grupo.id, item.id);
      toast.success("Compartilhamento removido.");
      await Promise.all([buscarProdutos(), carregarCompartilhamentos()]);
    } catch (error) {
      toast.error(mensagemErro(error, "Não foi possível remover o compartilhamento."));
    } finally {
      setAcao("");
    }
  }

  if (!destinos.length) return null;

  return (
    <div className="mt-5 border-t border-slate-200 pt-5">
      <div className="flex items-start gap-3">
        <div className="rounded-lg bg-emerald-100 p-2 text-emerald-700">
          <FiPackage aria-hidden="true" />
        </div>
        <div>
          <h3 className="text-sm font-semibold text-slate-900">Estoque compartilhado</h3>
          <p className="mt-0.5 text-xs text-slate-600">
            O saldo continua nesta empresa. Uma venda no outro PDV baixa aqui e sincroniza com o
            Bling desta empresa.
          </p>
        </div>
      </div>

      <div className="mt-4 grid gap-3 md:grid-cols-[220px_1fr_auto]">
        <select
          value={destinoId}
          onChange={(event) => setDestinoId(event.target.value)}
          className="rounded-lg border border-slate-300 px-3 py-2 text-sm"
        >
          {destinos.map((membro) => (
            <option key={membro.empresa_id} value={membro.empresa_id}>
              Usar no PDV: {membro.empresa_nome}
            </option>
          ))}
        </select>
        <input
          value={busca}
          onChange={(event) => setBusca(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === "Enter") {
              event.preventDefault();
              buscarProdutos();
            }
          }}
          placeholder="Buscar N&D, Farmina, SKU ou código de barras"
          className="rounded-lg border border-slate-300 px-3 py-2 text-sm"
        />
        <ActionButton icon={FiSearch} tone="outline" loading={carregando} onClick={buscarProdutos}>
          Buscar
        </ActionButton>
      </div>

      <label className="mt-3 flex cursor-pointer items-start gap-2 rounded-lg border border-violet-200 bg-violet-50 px-3 py-2.5">
        <input
          type="checkbox"
          className="mt-0.5"
          checked={acessoCatalogoCompleto}
          onChange={(event) => {
            setAcessoCatalogoCompleto(event.target.checked);
            setSelecionados(new Set());
          }}
        />
        <span>
          <span className="block text-sm font-semibold text-violet-900">
            Acesso completo ao catálogo
          </span>
          <span className="block text-xs text-violet-700">
            O produto aparece na lista normal e a empresa selecionada pode editar cadastro e fotos.
            As opções “anunciar no app” e “anunciar no e-commerce” continuam sendo definidas no
            produto.
          </span>
        </span>
      </label>

      {produtos.length > 0 ? (
        <div className="mt-3 max-h-72 overflow-auto rounded-lg border border-slate-200">
          {produtos.map((produto) => (
            <label
              key={produto.id}
              className="flex cursor-pointer items-center gap-3 border-b border-slate-100 px-3 py-2.5 last:border-b-0 hover:bg-slate-50"
            >
              <input
                type="checkbox"
                checked={
                  produto.acesso_catalogo_completo ||
                  (!acessoCatalogoCompleto && produto.compartilhado) ||
                  selecionados.has(produto.id)
                }
                disabled={
                  produto.acesso_catalogo_completo ||
                  (!acessoCatalogoCompleto && produto.compartilhado)
                }
                onChange={() => alternarProduto(produto.id)}
              />
              <span className="min-w-0 flex-1">
                <span className="block truncate text-sm font-medium text-slate-900">
                  {produto.nome}
                </span>
                <span className="text-xs text-slate-500">
                  {produto.codigo || "Sem SKU"} · saldo {formatarEstoque(produto.estoque_atual)}
                </span>
              </span>
              {produto.acesso_catalogo_completo ? (
                <span className="rounded-full bg-violet-100 px-2 py-1 text-xs font-semibold text-violet-700">
                  Catálogo completo
                </span>
              ) : produto.compartilhado ? (
                <span className="rounded-full bg-emerald-100 px-2 py-1 text-xs font-semibold text-emerald-700">
                  Saldo compartilhado
                </span>
              ) : null}
            </label>
          ))}
        </div>
      ) : null}

      <div className="mt-3 flex justify-end">
        <ActionButton
          icon={FiShare2}
          intent="success"
          loading={acao === "compartilhar"}
          disabled={!selecionados.size}
          onClick={compartilharSelecionados}
        >
          Compartilhar selecionados ({selecionados.size})
        </ActionButton>
      </div>

      {compartilhamentos.length > 0 ? (
        <div className="mt-5">
          <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">
            Autorizações ativas
          </div>
          <div className="mt-2 divide-y divide-slate-100 rounded-lg border border-slate-200">
            {compartilhamentos.map((item) => (
              <div key={item.id} className="flex items-center gap-3 px-3 py-2.5">
                <div className="min-w-0 flex-1">
                  <div className="truncate text-sm font-medium text-slate-900">
                    {item.produto_nome}
                  </div>
                  <div className="text-xs text-slate-500">
                    {item.empresa_origem_nome} → {item.empresa_consumidora_nome} · saldo{" "}
                    {formatarEstoque(item.estoque_atual)}
                  </div>
                  <button
                    type="button"
                    className="mt-1 text-xs font-semibold text-violet-700 hover:text-violet-900 disabled:opacity-50"
                    disabled={!item.pode_remover || acao === `catalogo-${item.id}`}
                    onClick={() => alternarAcessoCatalogo(item)}
                  >
                    {acao === `catalogo-${item.id}`
                      ? "Atualizando..."
                      : item.acesso_catalogo_completo
                        ? "Retirar acesso ao cadastro (manter saldo)"
                        : "Liberar cadastro, fotos, app e e-commerce"}
                  </button>
                </div>
                {item.pode_remover ? (
                  <ActionButton
                    icon={FiTrash2}
                    intent="danger"
                    tone="ghost"
                    size="xs"
                    loading={acao === `remover-${item.id}`}
                    onClick={() => remover(item)}
                  >
                    Remover
                  </ActionButton>
                ) : null}
              </div>
            ))}
          </div>
        </div>
      ) : null}
    </div>
  );
}
