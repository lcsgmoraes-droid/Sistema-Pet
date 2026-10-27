import { AlertTriangle, Coins, ShoppingCart } from "lucide-react";
import { useEffect, useState } from "react";
import toast from "react-hot-toast";
import api from "../../api";
import BotaoInteracao from "../../components/v2/BotaoInteracao/BotaoInteracao";
import CartaoIndicador from "../../components/v2/CartaoIndicador/CartaoIndicador";
import {
  ROTULO_DA_COMPRA,
  ROTULO_DO_NIVEL,
  avisoDoSaldo,
  formatarCreditos,
  formatarQuando,
  formatarReais,
} from "../../utils/consumoWhatsapp";

function mensagemDeErro(error, padrao) {
  const detalhe = error?.response?.data?.detail;
  return typeof detalhe === "string" ? detalhe : padrao;
}

const TOM_DO_AVISO = {
  erro: "text-red-700 dark:text-red-300",
  atencao: "text-amber-800 dark:text-amber-300",
};

// Saldo de créditos da loja, pacotes avulsos para comprar e pedidos em andamento.
export default function CreditosSecao() {
  const [estado, setEstado] = useState(null);
  const [erro, setErro] = useState("");
  const [comprando, setComprando] = useState(null);

  useEffect(() => {
    let ativo = true;
    (async () => {
      try {
        const { data } = await api.get("/whatsapp/creditos");
        if (ativo) setEstado(data);
      } catch (error) {
        if (ativo) setErro(mensagemDeErro(error, "Não foi possível carregar os créditos."));
      }
    })();
    return () => {
      ativo = false;
    };
  }, []);

  const executar = async (chave, chamada, sucesso) => {
    setComprando(chave);
    try {
      const { data } = await chamada();
      setEstado(data);
      toast.success(sucesso);
    } catch (error) {
      toast.error(mensagemDeErro(error, "Não foi possível concluir."));
    } finally {
      setComprando(null);
    }
  };

  if (erro) {
    return (
      <p role="alert" className="text-sm font-medium text-red-700 dark:text-red-300">
        {erro}
      </p>
    );
  }
  if (!estado) {
    return (
      <div
        className="h-28 animate-pulse rounded-2xl bg-slate-100 dark:bg-slate-900"
        role="status"
        aria-label="Carregando os créditos"
      />
    );
  }

  const { saldo } = estado;
  const aviso = avisoDoSaldo(saldo);
  const pendentes = estado.compras.filter((compra) => compra.status === "pendente");

  return (
    <section aria-labelledby="creditos-titulo" className="space-y-3">
      <h2 id="creditos-titulo" className="text-base font-bold text-slate-950 dark:text-slate-100">
        Créditos de WhatsApp
      </h2>

      <div className="grid gap-3 sm:grid-cols-3">
        <CartaoIndicador
          titulo="Disponível agora"
          icone={Coins}
          tom={
            saldo.nivel === "esgotado"
              ? "perigo"
              : saldo.nivel === "baixo"
                ? "atencao"
                : "informativo"
          }
          detalhe={ROTULO_DO_NIVEL[saldo.nivel]}
        >
          <p className="m-0 text-2xl font-bold">
            {saldo.controle_ativo ? formatarCreditos(saldo.disponivel) : "Sem limite"}
          </p>
        </CartaoIndicador>
        <CartaoIndicador
          titulo="Franquia do mês"
          icone={Coins}
          tom="neutro"
          detalhe="Renova todo mês e não acumula."
        >
          <p className="m-0 text-2xl font-bold">
            {saldo.franquia_restante} de {saldo.franquia_mensal}
          </p>
        </CartaoIndicador>
        <CartaoIndicador
          titulo="Créditos avulsos"
          icone={ShoppingCart}
          tom="neutro"
          detalhe="Comprados em pacotes. Não vencem."
        >
          <p className="m-0 text-2xl font-bold">{formatarCreditos(saldo.avulso)}</p>
        </CartaoIndicador>
      </div>

      {aviso ? (
        <p className={`flex items-start gap-2 text-sm font-semibold ${TOM_DO_AVISO[aviso.tom]}`}>
          <AlertTriangle className="mt-0.5 h-4 w-4 flex-none" aria-hidden="true" />
          {aviso.texto}
        </p>
      ) : null}

      <div className="grid gap-3 md:grid-cols-2">
        <div className="rounded-2xl border border-slate-200 bg-white p-4 dark:border-slate-700 dark:bg-slate-900">
          <h3 className="text-sm font-bold text-slate-950 dark:text-slate-100">
            Comprar pacote avulso
          </h3>
          {estado.pacotes.length === 0 ? (
            <p className="mt-2 text-sm text-slate-500 dark:text-slate-400">
              Nenhum pacote disponível no momento.
            </p>
          ) : (
            <ul className="mt-2 space-y-2">
              {estado.pacotes.map((pacote) => (
                <li key={pacote.id} className="flex items-center justify-between gap-3 text-sm">
                  <span>
                    <strong>{pacote.nome}</strong> · {formatarCreditos(pacote.creditos)} ·{" "}
                    {formatarReais(pacote.preco)}
                  </span>
                  <BotaoInteracao
                    icon={ShoppingCart}
                    tamanho="pequeno"
                    loading={comprando === `comprar-${pacote.id}`}
                    onClick={() =>
                      executar(
                        `comprar-${pacote.id}`,
                        () => api.post("/whatsapp/creditos/comprar", { pacote_id: pacote.id }),
                        "Pedido enviado. Veja as instruções abaixo.",
                      )
                    }
                  >
                    Comprar
                  </BotaoInteracao>
                </li>
              ))}
            </ul>
          )}
          <p className="mt-3 text-xs text-slate-500 dark:text-slate-400">
            {estado.instrucoes_de_pagamento}
          </p>
        </div>

        <div className="rounded-2xl border border-slate-200 bg-white p-4 dark:border-slate-700 dark:bg-slate-900">
          <h3 className="text-sm font-bold text-slate-950 dark:text-slate-100">
            Quanto cada envio consome
          </h3>
          <ul className="mt-2 space-y-1 text-sm text-slate-800 dark:text-slate-200">
            {estado.custos.map((custo) => (
              <li key={custo.chave} className="flex justify-between gap-3">
                <span>{custo.rotulo}</span>
                <span className="font-semibold">{custo.creditos}</span>
              </li>
            ))}
          </ul>
        </div>
      </div>

      {estado.compras.length > 0 ? (
        <div className="rounded-2xl border border-slate-200 bg-white p-4 dark:border-slate-700 dark:bg-slate-900">
          <h3 className="text-sm font-bold text-slate-950 dark:text-slate-100">Seus pedidos</h3>
          <ul className="mt-2 space-y-2 text-sm">
            {estado.compras.map((compra) => (
              <li key={compra.id} className="flex flex-wrap items-center justify-between gap-2">
                <span>
                  {formatarQuando(compra.solicitado_em)} · {compra.pacote_nome} ·{" "}
                  {formatarCreditos(compra.creditos)} · {formatarReais(compra.preco)} ·{" "}
                  <strong>{ROTULO_DA_COMPRA[compra.status] || compra.status}</strong>
                </span>
                {compra.status === "pendente" ? (
                  <BotaoInteracao
                    tamanho="pequeno"
                    loading={comprando === `cancelar-${compra.id}`}
                    onClick={() =>
                      executar(
                        `cancelar-${compra.id}`,
                        () => api.post(`/whatsapp/creditos/compras/${compra.id}/cancelar`),
                        "Pedido cancelado.",
                      )
                    }
                  >
                    Cancelar pedido
                  </BotaoInteracao>
                ) : null}
              </li>
            ))}
          </ul>
          {pendentes.length > 0 ? (
            <p className="mt-2 text-xs text-slate-500 dark:text-slate-400">
              Os créditos são liberados assim que o pagamento é confirmado.
            </p>
          ) : null}
        </div>
      ) : null}
    </section>
  );
}
