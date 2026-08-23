import { useCallback, useEffect, useMemo, useState } from "react";
import toast from "react-hot-toast";
import { FiLink, FiSearch, FiTrash2 } from "react-icons/fi";
import ActionButton from "../../../components/ui/ActionButton";
import EmptyState from "../../../components/ui/EmptyState";
import Panel from "../../../components/ui/Panel";
import ProductIdentity from "../../../components/ui/ProductIdentity";
import StatusBadge from "../../../components/ui/StatusBadge";
import { confirmarCorePet } from "../../../services/corepetDialog";
import {
  buscarProdutosGrupo,
  obterVinculosProdutosGrupo,
  removerVinculoProdutosGrupo,
  vincularProdutosGrupo,
} from "../../../services/gruposEmpresas";
import { campoClasses } from "./GrupoAnaliseFiltros";

function ProdutoResultado({ produto, selecionado, onSelect }) {
  return (
    <div
      className={[
        "flex w-full items-start gap-3 rounded-lg border p-3 text-left transition-colors",
        selecionado
          ? "border-blue-500 bg-blue-50 ring-2 ring-blue-100"
          : "border-slate-200 bg-white",
      ].join(" ")}
    >
      <div className="min-w-0 flex-1">
        <ProductIdentity
          name={produto.produto_nome}
          code={produto.sku}
          nameClassName="font-semibold text-slate-900"
        />
        <div className="mt-1 flex flex-wrap gap-x-3 text-xs text-slate-500">
          <span>{produto.empresa_nome}</span>
          <span>EAN {produto.ean || "não informado"}</span>
          <span>Estoque {produto.estoque}</span>
        </div>
      </div>
      <ActionButton
        type="button"
        intent={selecionado ? "create" : "info"}
        tone={selecionado ? "solid" : "soft"}
        onClick={() => onSelect(produto)}
      >
        {selecionado ? "Selecionado" : "Selecionar"}
      </ActionButton>
    </div>
  );
}

function ProdutoBusca({
  empresaId,
  empresas,
  label,
  onEmpresaChange,
  onSelect,
  selecionado,
  grupoId,
}) {
  const [busca, setBusca] = useState("");
  const [resultados, setResultados] = useState([]);
  const [carregando, setCarregando] = useState(false);

  async function pesquisar(event) {
    event.preventDefault();
    if (busca.trim().length < 2) {
      toast.error("Digite ao menos 2 caracteres do nome, SKU ou código de barras.");
      return;
    }
    setCarregando(true);
    try {
      const dados = await buscarProdutosGrupo(grupoId, {
        empresa_id: empresaId,
        busca: busca.trim(),
      });
      setResultados(dados.itens || []);
    } catch (error) {
      toast.error(error?.response?.data?.detail || "Não foi possível pesquisar os produtos.");
    } finally {
      setCarregando(false);
    }
  }

  return (
    <Panel title={label} subtitle="Pesquise e escolha um cadastro desta empresa.">
      <form className="space-y-3" onSubmit={pesquisar}>
        <select
          value={empresaId}
          onChange={(event) => {
            onEmpresaChange(event.target.value);
            onSelect(null);
            setResultados([]);
          }}
          className={`w-full ${campoClasses}`}
        >
          {empresas.map((empresa) => (
            <option key={empresa.empresa_id} value={empresa.empresa_id}>
              {empresa.empresa_nome}
            </option>
          ))}
        </select>
        <div className="flex gap-2">
          <input
            value={busca}
            onChange={(event) => setBusca(event.target.value)}
            placeholder="Nome, SKU ou EAN"
            className={`min-w-0 flex-1 ${campoClasses}`}
          />
          <ActionButton type="submit" icon={FiSearch} intent="info" loading={carregando}>
            Buscar
          </ActionButton>
        </div>
      </form>
      <div className="mt-3 max-h-72 space-y-2 overflow-y-auto">
        {resultados.map((produto) => (
          <ProdutoResultado
            key={`${produto.empresa_id}-${produto.produto_id}`}
            produto={produto}
            selecionado={selecionado?.produto_id === produto.produto_id}
            onSelect={onSelect}
          />
        ))}
      </div>
    </Panel>
  );
}

export default function GrupoVinculosProdutosTab({ empresas, grupoId }) {
  const [empresaA, setEmpresaA] = useState(empresas[0]?.empresa_id || "");
  const [empresaB, setEmpresaB] = useState(empresas[1]?.empresa_id || "");
  const [produtoA, setProdutoA] = useState(null);
  const [produtoB, setProdutoB] = useState(null);
  const [dados, setDados] = useState(null);
  const [carregando, setCarregando] = useState(true);
  const [salvando, setSalvando] = useState(false);

  const carregar = useCallback(async () => {
    setCarregando(true);
    try {
      setDados(await obterVinculosProdutosGrupo(grupoId));
    } catch (error) {
      toast.error(error?.response?.data?.detail || "Não foi possível carregar os vínculos.");
    } finally {
      setCarregando(false);
    }
  }, [grupoId]);

  useEffect(() => {
    carregar();
  }, [carregar]);

  useEffect(() => {
    if (!empresaA && empresas[0]) setEmpresaA(empresas[0].empresa_id);
    if (!empresaB && empresas[1]) setEmpresaB(empresas[1].empresa_id);
  }, [empresaA, empresaB, empresas]);

  const empresasA = useMemo(
    () => empresas.filter((empresa) => empresa.empresa_id !== empresaB),
    [empresaB, empresas],
  );
  const empresasB = useMemo(
    () => empresas.filter((empresa) => empresa.empresa_id !== empresaA),
    [empresaA, empresas],
  );

  async function salvarVinculo() {
    if (!produtoA || !produtoB) {
      toast.error("Escolha os dois produtos que representam o mesmo item.");
      return;
    }
    setSalvando(true);
    try {
      await vincularProdutosGrupo(
        grupoId,
        { empresa_id: produtoA.empresa_id, produto_id: produtoA.produto_id },
        { empresa_id: produtoB.empresa_id, produto_id: produtoB.produto_id },
      );
      toast.success("Produtos vinculados. As análises passam a somar os dois cadastros.");
      setProdutoA(null);
      setProdutoB(null);
      await carregar();
    } catch (error) {
      toast.error(error?.response?.data?.detail || "Não foi possível criar o vínculo.");
    } finally {
      setSalvando(false);
    }
  }

  async function remover(vinculo) {
    const confirmado = await confirmarCorePet(
      `Remover o vínculo entre ${vinculo.produto_a.produto_nome} e ${vinculo.produto_b.produto_nome}? As vendas deixarão de ser somadas como o mesmo produto.`,
    );
    if (!confirmado) return;
    try {
      await removerVinculoProdutosGrupo(grupoId, vinculo.id);
      toast.success("Vínculo removido.");
      await carregar();
    } catch (error) {
      toast.error(error?.response?.data?.detail || "Não foi possível remover o vínculo.");
    }
  }

  return (
    <div className="space-y-4">
      <Panel
        title="Como funciona o vínculo"
        subtitle="Produtos com o mesmo EAN já são reconhecidos automaticamente. Use o vínculo manual quando SKU, EAN ou nome forem diferentes entre as empresas."
      >
        <div className="flex flex-wrap gap-2 text-sm text-slate-600 dark:text-slate-300">
          <StatusBadge intent="success">Mesmo EAN: automático</StatusBadge>
          <StatusBadge intent="purple">Cadastros diferentes: vínculo manual</StatusBadge>
          <span>O vínculo altera somente as análises do grupo; não muda estoque nem cadastro.</span>
        </div>
      </Panel>

      {dados?.pode_gerenciar ? (
        <>
          <div className="grid gap-4 lg:grid-cols-2">
            <ProdutoBusca
              empresaId={empresaA}
              empresas={empresasA}
              label="1. Produto de uma empresa"
              onEmpresaChange={setEmpresaA}
              onSelect={setProdutoA}
              selecionado={produtoA}
              grupoId={grupoId}
            />
            <ProdutoBusca
              empresaId={empresaB}
              empresas={empresasB}
              label="2. Produto correspondente"
              onEmpresaChange={setEmpresaB}
              onSelect={setProdutoB}
              selecionado={produtoB}
              grupoId={grupoId}
            />
          </div>
          <div className="flex justify-end">
            <ActionButton
              icon={FiLink}
              intent="info"
              loading={salvando}
              disabled={!produtoA || !produtoB}
              onClick={salvarVinculo}
            >
              Vincular como o mesmo produto
            </ActionButton>
          </div>
        </>
      ) : (
        <Panel className="border-amber-200 bg-amber-50/40">
          <p className="text-sm text-amber-900">
            Você pode consultar os vínculos. Somente a empresa responsável pelo grupo pode criá-los
            ou removê-los.
          </p>
        </Panel>
      )}

      {!carregando && (dados?.itens || []).length === 0 ? (
        <EmptyState
          icon={FiLink}
          title="Nenhum vínculo manual criado"
          description="Produtos com EAN igual continuam sendo agrupados automaticamente."
        />
      ) : (
        <Panel
          title="Vínculos confirmados"
          subtitle={`${dados?.itens?.length || 0} equivalência(s) cadastrada(s)`}
        >
          <div className="space-y-3">
            {(dados?.itens || []).map((vinculo) => (
              <div
                key={vinculo.id}
                className="flex flex-col gap-3 rounded-lg border border-slate-200 p-4 lg:flex-row lg:items-center"
              >
                <div className="grid min-w-0 flex-1 gap-3 md:grid-cols-[1fr_auto_1fr] md:items-center">
                  <div>
                    <div className="text-xs font-semibold uppercase text-slate-500">
                      {vinculo.produto_a.empresa_nome}
                    </div>
                    <ProductIdentity
                      name={vinculo.produto_a.produto_nome}
                      code={vinculo.produto_a.sku}
                    />
                  </div>
                  <FiLink className="hidden text-blue-500 md:block" aria-hidden="true" />
                  <div>
                    <div className="text-xs font-semibold uppercase text-slate-500">
                      {vinculo.produto_b.empresa_nome}
                    </div>
                    <ProductIdentity
                      name={vinculo.produto_b.produto_nome}
                      code={vinculo.produto_b.sku}
                    />
                  </div>
                </div>
                {dados?.pode_gerenciar ? (
                  <ActionButton
                    icon={FiTrash2}
                    intent="delete"
                    tone="soft"
                    onClick={() => remover(vinculo)}
                  >
                    Remover vínculo
                  </ActionButton>
                ) : null}
              </div>
            ))}
          </div>
        </Panel>
      )}
    </div>
  );
}
