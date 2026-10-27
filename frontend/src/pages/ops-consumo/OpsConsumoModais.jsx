import { useState } from "react";
import api from "../../platformApi";
import BotaoCancelar from "../../components/v2/BotaoCancelar/BotaoCancelar";
import BotaoSalva from "../../components/v2/BotaoSalva/BotaoSalva";
import InputCombobox from "../../components/v2/InputCombobox/InputCombobox";
import InputData from "../../components/v2/InputData/InputData";
import InputMoeda from "../../components/v2/InputMoeda/InputMoeda";
import InputPercentual from "../../components/v2/InputPercentual/InputPercentual";
import InputTextoLongo from "../../components/v2/InputTextoLongo/InputTextoLongo";
import ModalPadrao from "../../components/v2/ModalPadrao/ModalPadrao";
import {
  ROTULO_DA_CATEGORIA,
  formatarReais,
  leituraDaDivergencia,
} from "../../utils/consumoWhatsapp";

function mensagemDeErro(error, padrao) {
  const detalhe = error?.response?.data?.detail;
  return typeof detalhe === "string" ? detalhe : padrao;
}

const CATEGORIAS = [
  "marketing",
  "utility",
  "authentication",
  "authentication_international",
  "service",
];
const OPCOES_DE_CATEGORIA = CATEGORIAS.map((value) => ({
  value,
  label: ROTULO_DA_CATEGORIA[value],
}));

// Tarifas da Meta (reais por mensagem). Uma tarifa nova vale a partir da data e nunca apaga a antiga.
export function TarifasModal({ tarifas, onFechar, onAtualizado }) {
  const [categoria, setCategoria] = useState("marketing");
  const [valor, setValor] = useState(0);
  const [vigente, setVigente] = useState("");
  const [tentou, setTentou] = useState(false);
  const [enviando, setEnviando] = useState(false);
  const [erro, setErro] = useState("");

  const erros = {
    valor: valor > 0 ? "" : "Informe o valor por mensagem.",
    vigente: vigente ? "" : "Informe a partir de quando vale.",
  };

  const salvar = async (evento) => {
    evento.preventDefault();
    setTentou(true);
    setErro("");
    if (erros.valor || erros.vigente) return;
    setEnviando(true);
    try {
      const { data } = await api.post("/admin/whatsapp-consumo/tarifas", {
        categoria,
        valor,
        vigente_desde: vigente,
      });
      onAtualizado(data.items);
      setValor(0);
      setVigente("");
      setTentou(false);
    } catch (error) {
      setErro(mensagemDeErro(error, "Não foi possível salvar a tarifa."));
    } finally {
      setEnviando(false);
    }
  };

  return (
    <ModalPadrao
      titulo="Tarifas da Meta"
      tamanho="grande"
      onFechar={onFechar}
      rodape={<BotaoCancelar onClick={onFechar}>Fechar</BotaoCancelar>}
    >
      <p className="mb-4 text-sm text-slate-600 dark:text-slate-300">
        Cadastre o preço por mensagem (em reais) da tabela oficial da Meta. O custo estimado de cada
        mensagem usa a tarifa vigente no dia do envio. Para mudar um preço, cadastre uma tarifa nova
        com a data em que ela passa a valer.
      </p>

      <form noValidate onSubmit={salvar} className="grid gap-3 sm:grid-cols-4 sm:items-end">
        <InputCombobox
          id="tarifa-categoria"
          label="Categoria"
          value={categoria}
          opcoes={OPCOES_DE_CATEGORIA}
          onChange={setCategoria}
        />
        <InputMoeda
          id="tarifa-valor"
          label="Valor por mensagem"
          value={valor}
          onChange={setValor}
          error={tentou ? erros.valor : ""}
          required
        />
        <InputData
          id="tarifa-vigente"
          label="Vale a partir de"
          value={vigente}
          onChange={setVigente}
          error={tentou ? erros.vigente : ""}
          required
        />
        <BotaoSalva type="submit" loading={enviando}>
          Cadastrar
        </BotaoSalva>
      </form>
      {erro ? (
        <p role="alert" className="mt-2 text-sm font-medium text-red-700 dark:text-red-300">
          {erro}
        </p>
      ) : null}

      {tarifas.length === 0 ? (
        <p className="mt-4 text-sm text-slate-500 dark:text-slate-400">
          Nenhuma tarifa cadastrada. Sem tarifa, o custo estimado fica zerado.
        </p>
      ) : (
        <table className="mt-4 w-full text-left text-sm">
          <thead>
            <tr className="border-b border-slate-200 text-xs text-slate-500 dark:border-slate-700 dark:text-slate-400">
              <th className="py-2 pr-3 font-semibold">Categoria</th>
              <th className="py-2 pr-3 font-semibold">Valor</th>
              <th className="py-2 pr-3 font-semibold">Vale desde</th>
              <th className="py-2 font-semibold">Cadastrada por</th>
            </tr>
          </thead>
          <tbody>
            {tarifas.map((tarifa) => (
              <tr key={tarifa.id} className="border-b border-slate-100 dark:border-slate-800">
                <td className="py-2 pr-3">
                  {ROTULO_DA_CATEGORIA[tarifa.categoria] || tarifa.categoria}
                </td>
                <td className="py-2 pr-3">
                  {tarifa.valor.toLocaleString("pt-BR", {
                    style: "currency",
                    currency: "BRL",
                    minimumFractionDigits: 4,
                  })}
                </td>
                <td className="py-2 pr-3">
                  {new Date(`${tarifa.vigente_desde}T12:00:00`).toLocaleDateString("pt-BR")}
                </td>
                <td className="py-2">{tarifa.criado_por}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </ModalPadrao>
  );
}

// Fecha o mês de todas as lojas com movimento: guarda uma fotografia do consumo e o repasse.
export function FecharMesModal({ mes, margemPadrao, onFechar, onFechado }) {
  const [margem, setMargem] = useState(margemPadrao || 0);
  const [enviando, setEnviando] = useState(false);
  const [erro, setErro] = useState("");

  const fechar = async (evento) => {
    evento.preventDefault();
    setEnviando(true);
    setErro("");
    try {
      const { data } = await api.post("/admin/whatsapp-consumo/fechar", {
        mes,
        margem_percentual: margem,
      });
      onFechado(data);
    } catch (error) {
      setErro(mensagemDeErro(error, "Não foi possível fechar o mês."));
    } finally {
      setEnviando(false);
    }
  };

  return (
    <ModalPadrao
      titulo={`Fechar ${mes}`}
      tamanho="pequena"
      onFechar={onFechar}
      rodape={
        <>
          <BotaoCancelar onClick={onFechar} disabled={enviando} />
          <BotaoSalva type="submit" form="fechar-mes" loading={enviando}>
            Fechar o mês
          </BotaoSalva>
        </>
      }
    >
      <form id="fechar-mes" noValidate onSubmit={fechar} className="space-y-4">
        <p className="text-sm text-slate-600 dark:text-slate-300">
          O fechamento guarda, para cada loja, o consumo do mês, o custo estimado e o valor de
          repasse. Depois de fechado, os números daquele mês não mudam. Lojas já fechadas são
          mantidas como estão.
        </p>
        <InputPercentual
          id="margem-repasse"
          label="Margem sobre o custo da Meta"
          maxValue={1000}
          value={margem}
          onChange={setMargem}
          help="0% repassa exatamente o custo estimado."
        />
        {erro ? (
          <p role="alert" className="text-sm font-medium text-red-700 dark:text-red-300">
            {erro}
          </p>
        ) : null}
      </form>
    </ModalPadrao>
  );
}

// Registra a fatura real da Meta de uma loja e mostra a diferença para o estimado.
export function FaturaModal({ loja, onFechar, onSalvo }) {
  const fechamento = loja.fechamento;
  const [valor, setValor] = useState(fechamento.fatura_meta || 0);
  const [observacao, setObservacao] = useState(fechamento.observacao || "");
  const [enviando, setEnviando] = useState(false);
  const [erro, setErro] = useState("");

  const salvar = async (evento) => {
    evento.preventDefault();
    setEnviando(true);
    setErro("");
    try {
      await api.patch(`/admin/whatsapp-consumo/fechamentos/${fechamento.id}/fatura`, {
        fatura_meta: valor,
        observacao: observacao || null,
      });
      onSalvo();
    } catch (error) {
      setErro(mensagemDeErro(error, "Não foi possível salvar a fatura."));
    } finally {
      setEnviando(false);
    }
  };

  const leitura = leituraDaDivergencia(valor - fechamento.custo_estimado);

  return (
    <ModalPadrao
      titulo={`Fatura da Meta · ${loja.loja_nome}`}
      tamanho="pequena"
      onFechar={onFechar}
      rodape={
        <>
          <BotaoCancelar onClick={onFechar} disabled={enviando} />
          <BotaoSalva type="submit" form="fatura-meta" loading={enviando}>
            Salvar
          </BotaoSalva>
        </>
      }
    >
      <form id="fatura-meta" noValidate onSubmit={salvar} className="space-y-4">
        <p className="text-sm text-slate-600 dark:text-slate-300">
          Mês {fechamento.mes} · custo estimado {formatarReais(fechamento.custo_estimado)} · repasse{" "}
          {formatarReais(fechamento.valor_repasse)}.
        </p>
        <InputMoeda
          id="fatura-valor"
          label="Valor da fatura da Meta"
          value={valor}
          onChange={setValor}
        />
        <p className="text-sm font-medium text-slate-700 dark:text-slate-200">{leitura.texto}</p>
        <InputTextoLongo
          id="fatura-observacao"
          label="Observação (opcional)"
          value={observacao}
          maxLength={1000}
          onChange={setObservacao}
        />
        {erro ? (
          <p role="alert" className="text-sm font-medium text-red-700 dark:text-red-300">
            {erro}
          </p>
        ) : null}
      </form>
    </ModalPadrao>
  );
}
