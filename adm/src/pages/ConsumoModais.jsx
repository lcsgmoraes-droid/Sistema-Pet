import { useState } from "react";
import { alterar, enviar } from "../api/cliente";
import { Aviso, Botao, Campo } from "../components/ui";
import { Janela, Selecao } from "../components/formulario";
import { ROTULO_DA_CATEGORIA, formatarReais, lerNumero, leituraDaDivergencia } from "../lib/whatsapp";

const OPCOES_DE_CATEGORIA = ["marketing", "utility", "authentication", "authentication_international", "service"].map(
  (value) => ({ value, label: ROTULO_DA_CATEGORIA[value] }),
);

// Tarifas da Meta (reais por mensagem). Uma tarifa nova vale a partir da data e nunca apaga a antiga.
export function TarifasModal({ tarifas, aoFechar, aoAtualizar }) {
  const [categoria, setCategoria] = useState("marketing");
  const [valor, setValor] = useState("");
  const [vigente, setVigente] = useState("");
  const [tentou, setTentou] = useState(false);
  const [enviando, setEnviando] = useState(false);
  const [erro, setErro] = useState("");

  const erros = {
    valor: lerNumero(valor) > 0 ? "" : "Informe o valor por mensagem.",
    vigente: vigente ? "" : "Informe a partir de quando vale.",
  };

  const salvar = async () => {
    setTentou(true);
    setErro("");
    if (erros.valor || erros.vigente) return;
    setEnviando(true);
    try {
      const dados = await enviar("/admin/whatsapp-consumo/tarifas", {
        categoria,
        valor: lerNumero(valor),
        vigente_desde: vigente,
      });
      aoAtualizar(dados.items);
      setValor("");
      setVigente("");
      setTentou(false);
    } catch (falha) {
      setErro(falha.message || "Não foi possível salvar a tarifa.");
    } finally {
      setEnviando(false);
    }
  };

  return (
    <Janela titulo="Tarifas da Meta" formId="tarifas" soFechar aoFechar={aoFechar} aoSalvar={salvar}>
      <p className="text-sm text-slate-600 dark:text-slate-300">
        Cadastre o preço por mensagem (em reais) da tabela oficial da Meta. O custo estimado de cada mensagem usa a
        tarifa vigente no dia do envio. Para mudar um preço, cadastre uma tarifa nova com a data em que ela passa a
        valer.
      </p>
      <div className="grid gap-3 sm:grid-cols-2">
        <Selecao
          rotulo="Categoria"
          opcoes={OPCOES_DE_CATEGORIA}
          value={categoria}
          onChange={(e) => setCategoria(e.target.value)}
        />
        <Campo
          rotulo="Valor por mensagem (R$)"
          inputMode="decimal"
          value={valor}
          onChange={(e) => setValor(e.target.value)}
          erro={tentou ? erros.valor : ""}
        />
        <Campo
          rotulo="Vale a partir de"
          type="date"
          value={vigente}
          onChange={(e) => setVigente(e.target.value)}
          erro={tentou ? erros.vigente : ""}
        />
      </div>
      <Botao type="submit" carregando={enviando}>
        Cadastrar tarifa
      </Botao>
      {erro ? <Aviso tom="erro">{erro}</Aviso> : null}

      {tarifas.length === 0 ? (
        <p className="text-sm text-slate-600 dark:text-slate-400">
          Nenhuma tarifa cadastrada. Sem tarifa, o custo estimado fica zerado.
        </p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="border-b border-slate-200 text-xs text-slate-600 dark:border-slate-700 dark:text-slate-400">
                <th className="py-2 pr-3 font-semibold">Categoria</th>
                <th className="py-2 pr-3 font-semibold">Valor</th>
                <th className="py-2 pr-3 font-semibold">Vale desde</th>
                <th className="py-2 font-semibold">Cadastrada por</th>
              </tr>
            </thead>
            <tbody>
              {tarifas.map((tarifa) => (
                <tr key={tarifa.id} className="border-b border-slate-100 dark:border-slate-800">
                  <td className="py-2 pr-3">{ROTULO_DA_CATEGORIA[tarifa.categoria] || tarifa.categoria}</td>
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
        </div>
      )}
    </Janela>
  );
}

// Fecha o mês de todas as lojas com movimento: guarda uma fotografia do consumo e o repasse.
export function FecharMesModal({ mes, margemPadrao, aoFechar, aoFechado }) {
  const [margem, setMargem] = useState(String(margemPadrao ?? 0));
  const [enviando, setEnviando] = useState(false);
  const [erro, setErro] = useState("");

  const fechar = async () => {
    setEnviando(true);
    setErro("");
    try {
      aoFechado(await enviar("/admin/whatsapp-consumo/fechar", { mes, margem_percentual: lerNumero(margem) }));
    } catch (falha) {
      setErro(falha.message || "Não foi possível fechar o mês.");
    } finally {
      setEnviando(false);
    }
  };

  return (
    <Janela
      titulo={`Fechar ${mes}`}
      formId="fechar-mes"
      rotuloSalvar="Fechar o mês"
      enviando={enviando}
      aoFechar={aoFechar}
      aoSalvar={fechar}
    >
      <p className="text-sm text-slate-600 dark:text-slate-300">
        O fechamento guarda, para cada loja, o consumo do mês, o custo estimado e o valor de repasse. Depois de
        fechado, os números daquele mês não mudam. Lojas já fechadas são mantidas como estão.
      </p>
      <Campo
        rotulo="Margem sobre o custo da Meta (%)"
        inputMode="decimal"
        value={margem}
        onChange={(e) => setMargem(e.target.value)}
        ajuda="0% repassa exatamente o custo estimado."
      />
      {erro ? <Aviso tom="erro">{erro}</Aviso> : null}
    </Janela>
  );
}

// Registra a fatura real da Meta de uma loja e mostra a diferença para o estimado.
export function FaturaModal({ loja, aoFechar, aoSalvo }) {
  const fechamento = loja.fechamento;
  const [valor, setValor] = useState(fechamento.fatura_meta ? String(fechamento.fatura_meta) : "");
  const [observacao, setObservacao] = useState(fechamento.observacao || "");
  const [enviando, setEnviando] = useState(false);
  const [erro, setErro] = useState("");

  const salvar = async () => {
    setEnviando(true);
    setErro("");
    try {
      await alterar(`/admin/whatsapp-consumo/fechamentos/${fechamento.id}/fatura`, {
        fatura_meta: lerNumero(valor),
        observacao: observacao || null,
      });
      aoSalvo();
    } catch (falha) {
      setErro(falha.message || "Não foi possível salvar a fatura.");
    } finally {
      setEnviando(false);
    }
  };

  const leitura = leituraDaDivergencia(lerNumero(valor) - fechamento.custo_estimado);

  return (
    <Janela
      titulo={`Fatura da Meta · ${loja.loja_nome}`}
      formId="fatura-meta"
      rotuloSalvar="Salvar"
      enviando={enviando}
      aoFechar={aoFechar}
      aoSalvar={salvar}
    >
      <p className="text-sm text-slate-600 dark:text-slate-300">
        Mês {fechamento.mes} · custo estimado {formatarReais(fechamento.custo_estimado)} · repasse{" "}
        {formatarReais(fechamento.valor_repasse)}.
      </p>
      <Campo
        rotulo="Valor da fatura da Meta (R$)"
        inputMode="decimal"
        value={valor}
        onChange={(e) => setValor(e.target.value)}
      />
      <p className="text-sm font-medium">{leitura.texto}</p>
      <div>
        <label htmlFor="fatura-obs" className="block text-sm font-medium">
          Observação (opcional)
        </label>
        <textarea
          id="fatura-obs"
          rows={3}
          maxLength={1000}
          value={observacao}
          onChange={(e) => setObservacao(e.target.value)}
          className="mt-1 w-full rounded-lg border border-slate-300 bg-white p-3 text-base dark:border-slate-600 dark:bg-slate-900"
        />
      </div>
      {erro ? <Aviso tom="erro">{erro}</Aviso> : null}
    </Janela>
  );
}
