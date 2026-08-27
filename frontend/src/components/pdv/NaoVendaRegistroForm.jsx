import { Link2, Plus, Save, UserRoundSearch } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import toast from "react-hot-toast";

import api from "../../api";
import { buscarClientes } from "../../api/clientes";
import useProdutosCatalogos from "../../hooks/useProdutosCatalogos";
import PessoaSelector from "../clientes/PessoaSelector";
import ActionButton from "../ui/ActionButton";
import { MOTIVOS_NAO_VENDA } from "./naoVendaConstants";
import NaoVendaItemEditor from "./NaoVendaItemEditor";

let sequenciaItem = 0;

function novoItem() {
  sequenciaItem += 1;
  return {
    chave: `nao-venda-item-${sequenciaItem}`,
    produto_id: null,
    produto_nome: "",
    sku: "",
    marca_id: null,
    marca_nome: "",
    fornecedor_id: null,
    fornecedor_nome: "",
    quantidade: 1,
    valor_unitario_estimado: 0,
  };
}

function telefoneCliente(cliente) {
  return cliente?.celular || cliente?.telefone || "";
}

export default function NaoVendaRegistroForm({ clienteInicial, onSaved }) {
  const [clienteId, setClienteId] = useState(clienteInicial?.id || null);
  const [clienteNome, setClienteNome] = useState(clienteInicial?.nome || "");
  const [clienteTelefone, setClienteTelefone] = useState(telefoneCliente(clienteInicial));
  const [clientesSugeridos, setClientesSugeridos] = useState([]);
  const [mostrarClientes, setMostrarClientes] = useState(false);
  const [motivo, setMotivo] = useState("produto_sem_estoque");
  const [observacoes, setObservacoes] = useState("");
  const [itens, setItens] = useState([novoItem()]);
  const [adicionarListaEspera, setAdicionarListaEspera] = useState(false);
  const [salvando, setSalvando] = useState(false);
  const { marcas, fornecedores } = useProdutosCatalogos();

  useEffect(() => {
    setClienteId(clienteInicial?.id || null);
    setClienteNome(clienteInicial?.nome || "");
    setClienteTelefone(telefoneCliente(clienteInicial));
  }, [clienteInicial]);

  useEffect(() => {
    const termo = String(clienteNome || "").trim();
    if (clienteId || termo.length < 2) {
      setClientesSugeridos([]);
      return undefined;
    }

    const timer = setTimeout(async () => {
      try {
        const encontrados = await buscarClientes({ search: termo, limit: 8 });
        setClientesSugeridos(
          (encontrados || []).filter((cliente) => cliente.tipo_cadastro !== "fornecedor"),
        );
        setMostrarClientes(true);
      } catch {
        setClientesSugeridos([]);
      }
    }, 300);
    return () => clearTimeout(timer);
  }, [clienteId, clienteNome]);

  const possuiProdutoVinculado = useMemo(
    () => itens.some((item) => Boolean(item.produto_id)),
    [itens],
  );
  const podeListaEspera = Boolean(clienteId && possuiProdutoVinculado);

  useEffect(() => {
    if (!podeListaEspera) setAdicionarListaEspera(false);
  }, [podeListaEspera]);

  const selecionarCliente = (cliente) => {
    setClienteId(cliente.id);
    setClienteNome(cliente.nome || "");
    setClienteTelefone(telefoneCliente(cliente));
    setClientesSugeridos([]);
    setMostrarClientes(false);
  };

  const alterarNomeCliente = (valor) => {
    setClienteNome(valor);
    if (clienteId) setClienteId(null);
    setMostrarClientes(true);
  };

  const atualizarItem = (chave, alteracoes) => {
    setItens((atuais) =>
      atuais.map((item) => (item.chave === chave ? { ...item, ...alteracoes } : item)),
    );
  };

  const removerItem = (chave) => {
    setItens((atuais) => {
      const restantes = atuais.filter((item) => item.chave !== chave);
      return restantes.length > 0 ? restantes : [novoItem()];
    });
  };

  const salvar = async (event) => {
    event.preventDefault();
    const itensValidos = itens.filter(
      (item) => item.produto_id || String(item.produto_nome || "").trim(),
    );
    if (itensValidos.some((item) => Number(item.quantidade) <= 0)) {
      toast.error("A quantidade dos produtos precisa ser maior que zero");
      return;
    }

    try {
      setSalvando(true);
      const response = await api.post("/nao-vendas/", {
        cliente_id: clienteId || null,
        cliente_nome: clienteNome.trim() || null,
        cliente_telefone: clienteTelefone.trim() || null,
        motivo,
        observacoes: observacoes.trim() || null,
        adicionar_lista_espera: adicionarListaEspera,
        itens: itensValidos.map(({ chave: _chave, ...item }) => ({
          ...item,
          produto_nome: item.produto_nome.trim() || null,
          sku: item.sku.trim() || null,
          marca_nome: item.marca_nome.trim() || null,
          fornecedor_nome: item.fornecedor_nome.trim() || null,
          valor_unitario_estimado: Number(item.valor_unitario_estimado) || null,
        })),
      });
      const adicionados = response.data?.lista_espera_adicionados || 0;
      toast.success(
        adicionados > 0
          ? `Não venda registrada e ${adicionados} item(ns) incluído(s) na lista de espera`
          : "Atendimento sem venda registrado",
      );
      onSaved?.();
    } catch (error) {
      toast.error(error.response?.data?.detail || "Não foi possível registrar o atendimento");
    } finally {
      setSalvando(false);
    }
  };

  return (
    <form onSubmit={salvar} className="space-y-5">
      <section className="rounded-xl border border-slate-200 bg-white p-4">
        <div className="mb-3 flex items-center gap-2">
          <UserRoundSearch className="h-5 w-5 text-blue-600" />
          <div>
            <h3 className="font-semibold text-slate-900">Cliente opcional</h3>
            <p className="text-xs text-slate-500">
              Pode ficar anônimo, ser vinculado ao cadastro ou ter apenas nome e telefone.
            </p>
          </div>
        </div>
        <div className="grid gap-3 md:grid-cols-2">
          <label>
            <span className="mb-1 block text-xs font-medium text-slate-600">Nome ou busca</span>
            <PessoaSelector
              value={clienteNome}
              onChange={alterarNomeCliente}
              onFocus={() => setMostrarClientes(true)}
              onSelect={selecionarCliente}
              suggestions={clientesSugeridos}
              showSuggestions={mostrarClientes}
              placeholder="Nome, CPF ou telefone"
              inputClassName="h-10"
            />
          </label>
          <label>
            <span className="mb-1 block text-xs font-medium text-slate-600">Telefone</span>
            <input
              value={clienteTelefone}
              onChange={(event) => setClienteTelefone(event.target.value)}
              placeholder="Telefone opcional"
              className="h-10 w-full rounded-lg border border-slate-300 px-3 text-sm focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-100"
            />
          </label>
        </div>
        {clienteId && (
          <div className="mt-3 flex items-center justify-between rounded-lg bg-emerald-50 px-3 py-2 text-sm text-emerald-800">
            <span className="inline-flex items-center gap-2">
              <Link2 className="h-4 w-4" /> Vinculado ao cliente cadastrado #{clienteId}
            </span>
            <button
              type="button"
              onClick={() => setClienteId(null)}
              className="text-xs font-semibold hover:underline"
            >
              Desvincular
            </button>
          </div>
        )}
      </section>

      <section className="space-y-3">
        <div className="flex items-center justify-between gap-3">
          <div>
            <h3 className="font-semibold text-slate-900">Produtos procurados</h3>
            <p className="text-xs text-slate-500">
              Opcional. Use o catálogo ou anote um produto que a loja ainda não possui.
            </p>
          </div>
          <button
            type="button"
            onClick={() => setItens((atuais) => [...atuais, novoItem()])}
            className="inline-flex items-center gap-1 rounded-lg border border-blue-200 bg-blue-50 px-3 py-2 text-sm font-medium text-blue-700 hover:bg-blue-100"
          >
            <Plus className="h-4 w-4" /> Outro produto
          </button>
        </div>
        {itens.map((item) => (
          <NaoVendaItemEditor
            key={item.chave}
            item={item}
            marcas={marcas}
            fornecedores={fornecedores}
            podeRemover={itens.length > 1 || Boolean(item.produto_nome)}
            onChange={(alteracoes) => atualizarItem(item.chave, alteracoes)}
            onRemove={() => removerItem(item.chave)}
          />
        ))}
      </section>

      <section className="grid gap-3 rounded-xl border border-slate-200 bg-white p-4 md:grid-cols-2">
        <label>
          <span className="mb-1 block text-sm font-semibold text-slate-800">
            Por que não comprou? <span className="text-red-500">*</span>
          </span>
          <select
            value={motivo}
            onChange={(event) => setMotivo(event.target.value)}
            className="h-10 w-full rounded-lg border border-slate-300 bg-white px-3 text-sm focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-100"
          >
            {MOTIVOS_NAO_VENDA.map((opcao) => (
              <option key={opcao.value} value={opcao.value}>
                {opcao.label}
              </option>
            ))}
          </select>
        </label>
        <label>
          <span className="mb-1 block text-sm font-semibold text-slate-800">Observação</span>
          <input
            value={observacoes}
            onChange={(event) => setObservacoes(event.target.value)}
            maxLength={2000}
            placeholder="Ex.: achou mais barato, queria embalagem de 15 kg..."
            className="h-10 w-full rounded-lg border border-slate-300 px-3 text-sm focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-100"
          />
        </label>

        <label
          className={`md:col-span-2 flex items-start gap-3 rounded-lg border px-3 py-3 ${
            podeListaEspera
              ? "cursor-pointer border-amber-200 bg-amber-50"
              : "border-slate-200 bg-slate-50 opacity-70"
          }`}
        >
          <input
            type="checkbox"
            checked={adicionarListaEspera}
            disabled={!podeListaEspera}
            onChange={(event) => setAdicionarListaEspera(event.target.checked)}
            className="mt-0.5 h-4 w-4 rounded border-slate-300 text-amber-600"
          />
          <span>
            <span className="block text-sm font-semibold text-slate-800">
              Também colocar os produtos cadastrados na lista de espera
            </span>
            <span className="block text-xs text-slate-500">
              Exige cliente e produto selecionados do cadastro. Produtos livres continuam apenas
              neste relatório.
            </span>
          </span>
        </label>
      </section>

      <div className="flex justify-end">
        <ActionButton type="submit" icon={Save} intent="create" size="lg" loading={salvando}>
          Registrar não venda
        </ActionButton>
      </div>
    </form>
  );
}
