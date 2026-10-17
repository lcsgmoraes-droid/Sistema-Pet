import {
  AlertTriangle,
  Clock,
  Copy,
  Eye,
  MessageCircle,
  RefreshCw,
  Search,
  User,
} from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import toast from "react-hot-toast";
import { useNavigate } from "react-router-dom";

import api from "../../api";
import DataTable from "../../components/ui/DataTable";
import PaginationControls from "../../components/ui/PaginationControls";
import BotaoInteracao from "../../components/v2/BotaoInteracao/BotaoInteracao";
import BotaoMenuAcoes from "../../components/v2/BotaoMenuAcoes/BotaoMenuAcoes";
import CartaoIndicador from "../../components/v2/CartaoIndicador/CartaoIndicador";
import Etiqueta from "../../components/v2/Etiqueta/Etiqueta";
import FaixaAviso from "../../components/v2/FaixaAviso/FaixaAviso";
import InputTexto from "../../components/v2/InputTexto/InputTexto";
import SeletorOpcoes from "../../components/v2/SeletorOpcoes/SeletorOpcoes";
import { formatMoneyBRL } from "../../utils/formatters";
import { whatsappUrl } from "./lembretesUtils";

const POR_PAGINA = 25;
const OPCOES_INATIVIDADE = [30, 60, 90].map((prazo) => ({
  valor: prazo,
  rotulo: `${prazo}+ dias`,
}));

function dataCurta(valor) {
  if (!valor) return "Sem data";
  return new Date(valor).toLocaleDateString("pt-BR", {
    timeZone: "America/Sao_Paulo",
  });
}

function telefoneValido(valor) {
  return String(valor || "").replace(/\D/g, "").length >= 10;
}

export default function LembretesClientesInativos() {
  const navigate = useNavigate();
  const [dias, setDias] = useState(30);
  const [busca, setBusca] = useState("");
  const [buscaAplicada, setBuscaAplicada] = useState("");
  const [pagina, setPagina] = useState(1);
  const [resultado, setResultado] = useState(null);
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState("");

  const carregar = useCallback(async () => {
    setCarregando(true);
    setErro("");
    try {
      const response = await api.get("/clientes/inativos", {
        params: {
          dias_sem_compra: dias,
          busca: buscaAplicada || undefined,
          pagina,
          por_pagina: POR_PAGINA,
        },
      });
      setResultado(response.data);
    } catch (error) {
      console.error("Erro ao carregar clientes inativos:", error);
      setErro(error?.response?.data?.detail || "Não foi possível carregar os clientes inativos.");
    } finally {
      setCarregando(false);
    }
  }, [buscaAplicada, dias, pagina]);

  useEffect(() => {
    void carregar();
  }, [carregar]);

  const aplicarBusca = (event) => {
    event.preventDefault();
    setPagina(1);
    setBuscaAplicada(busca.trim());
  };

  const mudarPrazo = (novoPrazo) => {
    setDias(novoPrazo);
    setPagina(1);
  };

  const abrirWhatsApp = (cliente) => {
    const url = whatsappUrl(cliente.telefone, cliente.mensagem_sugerida);
    if (!url || !telefoneValido(cliente.telefone)) {
      toast.error("Cliente sem telefone válido para WhatsApp");
      return;
    }
    const popup = window.open("about:blank", "_blank");
    if (!popup) {
      toast.error("O navegador bloqueou a nova aba do WhatsApp");
      return;
    }
    popup.opener = null;
    popup.location.replace(url);
    toast.success("Conversa preparada no WhatsApp");
  };

  const copiarMensagem = async (cliente) => {
    try {
      await navigator.clipboard.writeText(cliente.mensagem_sugerida);
      toast.success("Mensagem copiada");
    } catch {
      toast.error("Não foi possível copiar a mensagem");
    }
  };

  const resumo = resultado?.resumo || {};
  const clientes = resultado?.clientes || [];
  const paginacao = resultado?.paginacao || {
    pagina: 1,
    total_paginas: 1,
    total: 0,
  };

  const colunas = [
    {
      key: "acoes",
      header: "Ações",
      render: (cliente) => (
        <BotaoMenuAcoes
          acoes={[
            {
              icon: MessageCircle,
              label: "Abrir WhatsApp",
              disabled: !telefoneValido(cliente.telefone),
              title: telefoneValido(cliente.telefone)
                ? "Abrir conversa com mensagem pronta"
                : "Cliente sem telefone válido",
              onClick: () => abrirWhatsApp(cliente),
            },
            {
              icon: Copy,
              label: "Copiar mensagem",
              onClick: () => void copiarMensagem(cliente),
            },
            {
              icon: Eye,
              label: "Ver cliente",
              onClick: () => navigate(`/clientes/${cliente.cliente_id}/financeiro`),
            },
          ]}
          rotulo={`Mais ações para ${cliente.nome}`}
        />
      ),
    },
    {
      key: "cliente",
      header: "Cliente",
      render: (cliente) => (
        <div>
          <p className="m-0 font-semibold text-slate-900 dark:text-slate-100">{cliente.nome}</p>
          <p className="v2-texto-ajuda mt-0.5">
            {cliente.codigo ? `Código ${cliente.codigo}` : `ID ${cliente.cliente_id}`}
            {cliente.telefone ? ` · ${cliente.telefone}` : " · Sem telefone"}
          </p>
        </div>
      ),
    },
    {
      key: "inatividade",
      header: "Inatividade",
      align: "center",
      render: (cliente) => <Etiqueta tom="atencao">{cliente.dias_sem_comprar} dias</Etiqueta>,
    },
    {
      key: "ultima_compra",
      header: "Última compra",
      align: "right",
      render: (cliente) => dataCurta(cliente.ultima_compra),
    },
    {
      key: "compras",
      header: "Compras",
      align: "center",
      render: (cliente) => Number(cliente.total_compras || 0).toLocaleString("pt-BR"),
    },
    {
      key: "total",
      header: "Total comprado",
      align: "right",
      render: (cliente) => (
        <span className="font-semibold text-slate-900 dark:text-slate-100">
          {formatMoneyBRL(cliente.total_gasto)}
        </span>
      ),
    },
  ];

  return (
    <section className="grid gap-4">
      <div>
        <h3 className="m-0 text-base font-semibold text-slate-900 dark:text-slate-100">
          Clientes inativos
        </h3>
        <p className="v2-texto-ajuda mt-1 max-w-2xl">
          Clientes que já compraram, mas não voltaram no período escolhido. Nenhuma mensagem é
          enviada automaticamente.
        </p>
      </div>

      <div className="flex flex-wrap items-end justify-between gap-3">
        <SeletorOpcoes
          aoSelecionar={mudarPrazo}
          opcoes={OPCOES_INATIVIDADE}
          rotulo="Sem compra há"
          valorSelecionado={dias}
        />
        <form className="flex w-full max-w-xl items-end gap-2" onSubmit={aplicarBusca}>
          <InputTexto
            id="clientes-inativos-busca"
            left={<Search className="h-4 w-4 text-slate-400" aria-hidden="true" />}
            onChange={setBusca}
            placeholder="Buscar por nome, código, telefone ou e-mail"
            type="search"
            value={busca}
          />
          <BotaoInteracao type="submit">Buscar</BotaoInteracao>
          <BotaoInteracao disabled={carregando} icon={RefreshCw} onClick={() => void carregar()}>
            Atualizar
          </BotaoInteracao>
        </form>
      </div>

      {!carregando && !erro && (
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
          <CartaoIndicador icone={Clock} titulo={`Sem comprar há ${dias}+ dias`} tom="neutro">
            <p className="text-2xl font-bold text-slate-950 dark:text-white">
              {Number(resumo.total_inativos || 0).toLocaleString("pt-BR")}
            </p>
          </CartaoIndicador>
          <CartaoIndicador icone={MessageCircle} titulo="Com WhatsApp" tom="sucesso">
            <p className="text-2xl font-bold text-slate-950 dark:text-white">
              {Number(resumo.com_whatsapp || 0).toLocaleString("pt-BR")}
            </p>
          </CartaoIndicador>
          <CartaoIndicador icone={User} titulo="Sem telefone válido" tom="atencao">
            <p className="text-2xl font-bold text-slate-950 dark:text-white">
              {Number(resumo.sem_whatsapp || 0).toLocaleString("pt-BR")}
            </p>
          </CartaoIndicador>
        </div>
      )}

      {erro ? (
        <FaixaAviso
          acoes={
            <BotaoInteracao icon={RefreshCw} onClick={() => void carregar()}>
              Tentar novamente
            </BotaoInteracao>
          }
          icone={AlertTriangle}
          titulo="Não foi possível carregar"
          tom="perigo"
        >
          {erro}
        </FaixaAviso>
      ) : (
        <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm dark:border-slate-700 dark:bg-slate-900">
          <DataTable
            columns={colunas}
            data={clientes}
            emptyMessage="Nenhum cliente inativo encontrado com esses filtros."
            getRowKey={(cliente) => cliente.cliente_id}
            loading={carregando}
            loadingMessage="Carregando clientes inativos..."
          />
          <PaginationControls
            currentPage={paginacao.pagina}
            itemName="cliente(s)"
            itemsPerPage={POR_PAGINA}
            loading={carregando}
            onPageChange={setPagina}
            pageSizeOptions={[POR_PAGINA]}
            totalItems={paginacao.total}
            totalPages={paginacao.total_paginas}
            variant="bottom"
          />
        </div>
      )}
    </section>
  );
}
