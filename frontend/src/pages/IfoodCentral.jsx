import { useEffect, useRef, useState } from "react";
import {
  AlertTriangle,
  Calculator,
  CheckSquare,
  ChevronLeft,
  ChevronRight,
  ListFilter,
  Package,
  Pencil,
  RefreshCw,
  Search,
  Settings,
  ShoppingBag,
  Square,
} from "lucide-react";
import { useNavigate } from "react-router-dom";
import { getIfoodCatalogo } from "../api/ifood";
import { updateProduto } from "../api/produtos";
import { useAuth } from "../contexts/AuthContext";
import { isAdminRole } from "../auth/userRole";
import useIfoodPromotionRefresh from "../hooks/useIfoodPromotionRefresh";
import DataTable from "../components/ui/DataTable";
import AbasNavegacao from "../components/v2/AbasNavegacao/AbasNavegacao";
import BotaoInteracao from "../components/v2/BotaoInteracao/BotaoInteracao";
import BotaoMenuAcoes from "../components/v2/BotaoMenuAcoes/BotaoMenuAcoes";
import CartaoIndicador from "../components/v2/CartaoIndicador/CartaoIndicador";
import InputCheckbox from "../components/v2/InputCheckbox/InputCheckbox";
import InputCombobox from "../components/v2/InputCombobox/InputCombobox";
import InputTexto from "../components/v2/InputTexto/InputTexto";
import SeletorOpcoes from "../components/v2/SeletorOpcoes/SeletorOpcoes";
import IfoodConfiguracao from "../components/ifood/IfoodConfiguracao";
import IfoodProdutoDetalhes from "../components/ifood/IfoodProdutoDetalhes";
import IfoodStatus from "../components/ifood/IfoodStatus";
import {
  IFOOD_FILTROS,
  IFOOD_MODALIDADES,
  mensagemErroIfood,
  moedaIfood,
  percentualIfood,
  valorConhecido,
} from "../components/ifood/ifoodPresentation";

const POR_PAGINA = 30;
const SEM_RESUMO = { total: 0, selected: 0, issues: 0, out_of_stock: 0 };

export default function IfoodCentral() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const podeEditar =
    isAdminRole(user) ||
    Boolean(
      user?.permissions?.some(
        (permission) => permission === "*" || permission === "produtos.editar",
      ),
    );
  const [podeConfigurar, setPodeConfigurar] = useState(false);
  const [aba, setAba] = useState("catalogo");
  const [busca, setBusca] = useState("");
  const [buscaAplicada, setBuscaAplicada] = useState("");
  const [filtro, setFiltro] = useState("todos");
  const [modalidade, setModalidade] = useState("MERCHANT");
  const [pagina, setPagina] = useState(1);
  const [items, setItems] = useState([]);
  const [resumo, setResumo] = useState(SEM_RESUMO);
  const [total, setTotal] = useState(0);
  const [config, setConfig] = useState(null);
  const [carregando, setCarregando] = useState(true);
  const [inicializado, setInicializado] = useState(false);
  const [erro, setErro] = useState("");
  const [mensagem, setMensagem] = useState("");
  const [revisao, setRevisao] = useState(0);
  const [ocupado, setOcupado] = useState(null);
  const [detalhe, setDetalhe] = useState(null);
  const [salvandoPreco, setSalvandoPreco] = useState(false);
  const [tempoCatalogo, setTempoCatalogo] = useState(null);
  const inicializadoRef = useRef(false);
  const consultaChave = `${buscaAplicada}:${filtro}:${pagina}`;

  useIfoodPromotionRefresh(tempoCatalogo, () => setRevisao((atual) => atual + 1), {
    enabled: !ocupado && !salvandoPreco && !carregando,
    scopeKey: consultaChave,
  });

  useEffect(() => {
    const timer = window.setTimeout(() => {
      setBuscaAplicada(busca.trim());
      setPagina(1);
    }, 350);
    return () => window.clearTimeout(timer);
  }, [busca]);

  useEffect(() => {
    // Uma leitura iniciada antes do PUT nao pode substituir a selecao/preco
    // recem-salvos. Ao liberar a escrita, esta consulta e retomada.
    if (ocupado || salvandoPreco) {
      setCarregando(false);
      return undefined;
    }
    let ativo = true;
    const abort = new AbortController();
    setCarregando(true);
    setErro("");
    (async () => {
      try {
        const response = await getIfoodCatalogo(
          {
            q: buscaAplicada || undefined,
            filtro,
            limit: POR_PAGINA,
            offset: (pagina - 1) * POR_PAGINA,
          },
          { signal: abort.signal },
        );
        if (!ativo) return;
        const ultimaPagina = Math.max(1, Math.ceil((response.data.total || 0) / POR_PAGINA));
        if (pagina > ultimaPagina) {
          setPagina(ultimaPagina);
          return;
        }
        setItems(response.data.items || []);
        setTempoCatalogo({
          evaluated_at: response.data.evaluated_at,
          next_price_change_at: response.data.next_price_change_at,
        });
        setDetalhe((atual) =>
          atual
            ? response.data.items?.find((produto) => produto.product_id === atual.product_id) ||
              atual
            : null,
        );
        setResumo(response.data.summary || SEM_RESUMO);
        setTotal(response.data.total || 0);
        setConfig(response.data.config || null);
        setPodeConfigurar(Boolean(response.data.can_configure));
      } catch (error) {
        if (ativo) {
          setErro(
            mensagemErroIfood(error, "Não foi possível atualizar a central do iFood.") +
              (inicializadoRef.current ? " Os últimos dados exibidos foram mantidos." : ""),
          );
        }
      } finally {
        if (ativo) {
          setCarregando(false);
          setInicializado(true);
          inicializadoRef.current = true;
        }
      }
    })();
    return () => {
      ativo = false;
      abort.abort();
    };
  }, [buscaAplicada, filtro, pagina, revisao, ocupado, salvandoPreco]);

  function filtrar(valor) {
    setFiltro(valor);
    setPagina(1);
    setAba("catalogo");
  }

  async function selecionar(item, checked) {
    if (ocupado || !podeEditar) return;
    setOcupado(item.product_id);
    setErro("");
    setMensagem("");
    try {
      await updateProduto(item.product_id, { anunciar_ifood: checked });
      setMensagem(
        checked
          ? "Produto selecionado. Confira as pendências antes do envio ao iFood."
          : "Produto removido da seleção local do iFood.",
      );
      setRevisao((atual) => atual + 1);
    } catch (error) {
      setErro(mensagemErroIfood(error, "Não foi possível alterar a seleção do produto."));
    } finally {
      setOcupado(null);
    }
  }

  const editar = (item) => navigate(`/produtos/${item.product_id}/editar`);
  const columns = [
    {
      key: "acoes",
      header: "Ações",
      render: (item) => (
        <BotaoMenuAcoes
          rotulo={`Ações de ${item.name}`}
          acoes={[
            // Calculator segue o icone das calculadoras existentes do sistema.
            { icon: Calculator, label: "Simular preço e margem", onClick: () => setDetalhe(item) },
            podeEditar && {
              icon: Pencil,
              label: "Editar no cadastro",
              onClick: () => editar(item),
            },
            podeEditar && {
              icon: item.selected ? Square : CheckSquare,
              label: item.selected ? "Remover da seleção" : "Selecionar para iFood",
              disabled: Boolean(ocupado),
              onClick: () => selecionar(item, !item.selected),
            },
          ]}
        />
      ),
    },
    {
      key: "selected",
      header: "iFood",
      align: "center",
      render: (item) => (
        <InputCheckbox
          checked={Boolean(item.selected)}
          disabled={!podeEditar || Boolean(ocupado)}
          rotulo={`Vender ${item.name} no iFood`}
          onChange={(event) => selecionar(item, event.target.checked)}
        />
      ),
    },
    {
      key: "name",
      header: "Produto",
      render: (item) => (
        <div className="min-w-48">
          <p className="font-medium text-slate-900 dark:text-slate-100">
            {item.name || "Sem nome"}
          </p>
          <p className="v2-texto-ajuda mt-1">SKU {item.sku || "não informado"}</p>
        </div>
      ),
    },
    {
      key: "price",
      header: "Preço iFood",
      align: "right",
      render: (item) => (
        <div className="whitespace-nowrap">
          <p className="font-semibold">{moedaIfood(item.effective_price)}</p>
          <p className="v2-texto-ajuda mt-1">
            {item.promotion_active
              ? "Promoção vigente"
              : item.price_source === "especifico"
                ? "Preço específico"
                : "Regra da loja"}
          </p>
        </div>
      ),
    },
    {
      key: "margin",
      header: "Contribuição estimada",
      align: "right",
      render: (item) => {
        const margem = item.margins?.[modalidade];
        if (!margem) return <span className="v2-texto-ajuda">Acesso restrito</span>;
        if (!margem.calculated) return <span className="v2-texto-ajuda">Não calculada</span>;
        const negativa = Number(margem.contribution) < 0;
        return (
          <div
            className={
              margem.below_target || negativa
                ? "text-amber-700 dark:text-amber-300"
                : "text-emerald-700 dark:text-emerald-300"
            }
          >
            <p className="whitespace-nowrap font-semibold">
              {moedaIfood(margem.contribution)} · {percentualIfood(margem.percent)}
            </p>
            {negativa || margem.below_target ? (
              <p className="mt-1 text-xs">
                {negativa ? "Contribuição negativa" : "Abaixo da meta"}
              </p>
            ) : null}
          </div>
        );
      },
    },
    {
      key: "stock",
      header: "Estoque disponível",
      align: "right",
      render: (item) =>
        valorConhecido(item.available_stock)
          ? Number(item.available_stock).toLocaleString("pt-BR", { maximumFractionDigits: 3 })
          : "A conferir",
    },
    {
      key: "status",
      header: "Situação",
      render: (item) => (
        <div>
          <IfoodStatus status={item.status} />
          {item.pending?.length ? (
            <p className="v2-texto-ajuda mt-1">{item.pending.length} orientação(ões)</p>
          ) : null}
        </div>
      ),
    },
  ];
  const paginas = Math.max(1, Math.ceil(total / POR_PAGINA));

  if (!inicializado && carregando) {
    return (
      <div role="status" className="p-8 text-sm text-slate-500 dark:text-slate-300">
        Carregando a central do iFood…
      </div>
    );
  }

  return (
    <div className="space-y-5 p-4 md:p-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="v2-titulo-pagina">Central do iFood</h1>
          <p className="v2-subtitulo mt-1">
            Prepare o catálogo da loja, confira os preços e resolva as pendências.
          </p>
        </div>
        <BotaoInteracao
          icon={RefreshCw}
          loading={carregando}
          onClick={() => setRevisao((atual) => atual + 1)}
        >
          Atualizar
        </BotaoInteracao>
      </div>
      <div className="rounded-xl border border-blue-200 bg-blue-50 px-4 py-3 text-sm text-blue-900 dark:border-blue-500/30 dark:bg-blue-500/10 dark:text-blue-200">
        Preparação local: o envio real ao iFood permanece desativado nesta etapa. A seleção não
        confirma a publicação do anúncio.
      </div>
      {erro ? (
        <p
          role="alert"
          className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-800 dark:border-red-500/30 dark:bg-red-500/10 dark:text-red-200"
        >
          {erro}
        </p>
      ) : null}
      {mensagem ? (
        <p role="status" className="text-sm text-emerald-700 dark:text-emerald-300">
          {mensagem}
        </p>
      ) : null}
      <div className="grid grid-cols-2 gap-3 xl:grid-cols-4">
        {[
          {
            titulo: "Produtos",
            valor: resumo.total,
            icone: Package,
            filtro: "todos",
            tom: "neutro",
          },
          {
            titulo: "Selecionados",
            valor: resumo.selected,
            icone: ShoppingBag,
            filtro: "selecionados",
            tom: "informativo",
          },
          {
            titulo: "Com pendências",
            valor: resumo.issues,
            icone: AlertTriangle,
            filtro: "pendencias",
            tom: "atencao",
          },
          {
            titulo: "Sem estoque",
            valor: resumo.out_of_stock,
            icone: ListFilter,
            filtro: "sem_estoque",
            tom: "atencao",
          },
        ].map((card) => (
          <CartaoIndicador
            key={card.filtro}
            titulo={card.titulo}
            icone={card.icone}
            tom={card.tom}
            aoClicar={() => filtrar(card.filtro)}
          >
            <p className="text-2xl font-semibold text-slate-900 dark:text-slate-100">
              {Number(card.valor || 0).toLocaleString("pt-BR")}
            </p>
          </CartaoIndicador>
        ))}
      </div>
      <AbasNavegacao
        ariaLabel="Central do iFood"
        ativa={aba}
        onChange={setAba}
        abas={[
          { id: "catalogo", label: "Catálogo e pendências", icon: Package },
          { id: "configuracao", label: "Preços e custos da loja", icon: Settings },
        ]}
      />
      {aba === "configuracao" ? (
        <div className="rounded-xl border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-900 md:p-6">
          {config ? (
            <IfoodConfiguracao
              config={config}
              podeConfigurar={podeConfigurar}
              onSalvo={(novaConfig) => {
                if (novaConfig) setConfig(novaConfig);
                setRevisao((atual) => atual + 1);
              }}
            />
          ) : (
            <p className="v2-texto-ajuda">
              Não foi possível carregar as regras da loja. Atualize para tentar novamente.
            </p>
          )}
        </div>
      ) : (
        <div className="space-y-4 rounded-xl border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-900">
          <div className="grid items-start gap-3 md:grid-cols-[minmax(220px,1fr)_minmax(220px,0.65fr)]">
            <InputTexto
              id="ifood-busca"
              label="Buscar produto existente"
              placeholder="Nome, SKU ou EAN"
              value={busca}
              onChange={setBusca}
              left={<Search className="h-4 w-4 text-slate-400" aria-hidden="true" />}
            />
            <InputCombobox
              id="ifood-filtro"
              label="Mostrar"
              value={filtro}
              opcoes={IFOOD_FILTROS}
              permitirLimpar={false}
              onChange={filtrar}
            />
          </div>
          <SeletorOpcoes
            rotulo="Simular custos"
            opcoes={IFOOD_MODALIDADES}
            valorSelecionado={modalidade}
            aoSelecionar={setModalidade}
          />
          <p className="v2-texto-ajuda">
            Use "Simular preço e margem" nas ações para experimentar valores e aplicar o preço ao
            mesmo cadastro. O cenário de custos não altera a modalidade de entrega de pedidos.
          </p>
          <DataTable
            columns={columns}
            data={items}
            getRowKey={(item) => item.product_id}
            loading={carregando && !inicializado}
            loadingMessage="Consultando o catálogo…"
            emptyMessage="Nenhum produto encontrado com estes filtros."
          />
          {carregando && inicializado ? (
            <p role="status" className="v2-texto-ajuda">
              Atualizando preço, margem e pendências…
            </p>
          ) : null}
          <div className="flex flex-wrap items-center justify-between gap-3">
            <p className="v2-texto-ajuda">
              {total.toLocaleString("pt-BR")} produto(s) · página {pagina} de {paginas}
            </p>
            <div className="flex gap-2">
              <BotaoInteracao
                icon={ChevronLeft}
                tamanho="pequeno"
                disabled={pagina <= 1 || carregando}
                onClick={() => setPagina((atual) => atual - 1)}
              >
                Anterior
              </BotaoInteracao>
              <BotaoInteracao
                icon={ChevronRight}
                tamanho="pequeno"
                disabled={pagina >= paginas || carregando}
                onClick={() => setPagina((atual) => atual + 1)}
              >
                Próxima
              </BotaoInteracao>
            </div>
          </div>
        </div>
      )}
      {detalhe ? (
        <IfoodProdutoDetalhes
          key={detalhe.product_id}
          item={detalhe}
          modalidade={modalidade}
          onModalidade={setModalidade}
          onFechar={() => setDetalhe(null)}
          onEditar={() => editar(detalhe)}
          podeEditar={podeEditar}
          podeConfigurar={podeConfigurar}
          onSalvandoPreco={setSalvandoPreco}
          onPrecoAplicado={(atualizado) => {
            setDetalhe(atualizado);
            setItems((atuais) =>
              atuais.map((produto) =>
                produto.product_id === atualizado.product_id ? atualizado : produto,
              ),
            );
            setMensagem("Preço do iFood atualizado no cadastro do produto.");
            setRevisao((atual) => atual + 1);
          }}
          onConfigurar={() => {
            setDetalhe(null);
            setAba("configuracao");
          }}
        />
      ) : null}
    </div>
  );
}
