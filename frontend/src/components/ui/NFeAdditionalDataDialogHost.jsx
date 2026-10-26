import { FileText, RefreshCw } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import api from "../../api";
import {
  assinarDadosAdicionaisNota,
  resolverDadosAdicionaisNota,
} from "../../services/nfeAdditionalDataDialog";
import {
  CANAIS_DADOS_NOTA,
  DADOS_ADICIONAIS_NOTA_INICIAIS,
  validarDadosAdicionaisNota,
} from "../../utils/nfeAdditionalData.mjs";
import { textoRespostaFiscal } from "../../utils/pdvFiscalStatus";
import BotaoCancelar from "../v2/BotaoCancelar/BotaoCancelar";
import BotaoInteracao from "../v2/BotaoInteracao/BotaoInteracao";
import BotaoSalva from "../v2/BotaoSalva/BotaoSalva";
import InputCombobox from "../v2/InputCombobox/InputCombobox";
import InputCpfCnpj from "../v2/InputCpfCnpj/InputCpfCnpj";
import InputTexto from "../v2/InputTexto/InputTexto";
import InputTextoLongo from "../v2/InputTextoLongo/InputTextoLongo";

function mensagemErro(error) {
  const detalhes = error.response?.data?.detail;
  if (Array.isArray(detalhes)) {
    const mensagens = detalhes
      .map((item) =>
        typeof item?.msg === "string" ? item.msg.replace(/^Value error,\s*/i, "") : "",
      )
      .filter(Boolean);
    if (mensagens.length) return mensagens.join(" ");
  }
  return (
    textoRespostaFiscal(error.response?.data || error.message) ||
    "Não foi possível carregar os dados adicionais da nota."
  );
}

export function NFeAdditionalDataDialog({ dialogo }) {
  const [dados, setDados] = useState(null);
  const [podeEditar, setPodeEditar] = useState(false);
  const [carregando, setCarregando] = useState(true);
  const [salvando, setSalvando] = useState(false);
  const [erro, setErro] = useState("");
  const [versao, setVersao] = useState(0);
  const salvandoRef = useRef(false);

  useEffect(() => {
    let ativo = true;
    setCarregando(true);
    setDados(null);
    setErro("");
    api
      .get(`/nfe/vendas/${dialogo.vendaId}/dados-adicionais`)
      .then(({ data }) => {
        if (!ativo) return;
        setDados({ ...DADOS_ADICIONAIS_NOTA_INICIAIS, ...data.dados });
        setPodeEditar(data.pode_editar === true);
      })
      .catch((error) => {
        if (ativo) setErro(mensagemErro(error));
      })
      .finally(() => {
        if (ativo) setCarregando(false);
      });
    return () => {
      ativo = false;
    };
  }, [dialogo.vendaId, versao]);

  useEffect(() => {
    function aoPressionarTecla(evento) {
      if (evento.key === "Escape" && !salvandoRef.current)
        resolverDadosAdicionaisNota(dialogo.id, false);
    }
    window.addEventListener("keydown", aoPressionarTecla);
    return () => window.removeEventListener("keydown", aoPressionarTecla);
  }, [dialogo.id]);

  function alterar(campo, valor) {
    if (!podeEditar || salvandoRef.current) return;
    setDados((atual) => ({
      ...atual,
      [campo]: valor,
      ...(campo === "canal" && valor !== "amazon"
        ? { intermediador_cnpj: "", intermediador_identificacao: "" }
        : {}),
    }));
    setErro("");
  }

  async function salvar() {
    if (!podeEditar || salvandoRef.current || !dados) return;
    const pendencia = validarDadosAdicionaisNota(dados);
    if (pendencia) {
      setErro(pendencia);
      return;
    }
    salvandoRef.current = true;
    setSalvando(true);
    setErro("");
    try {
      await api.put(`/nfe/vendas/${dialogo.vendaId}/dados-adicionais`, { dados });
      resolverDadosAdicionaisNota(dialogo.id, true);
    } catch (error) {
      setErro(mensagemErro(error));
    } finally {
      salvandoRef.current = false;
      setSalvando(false);
    }
  }

  const disabled = salvando || !podeEditar;
  const amazon = dados?.canal === "amazon";
  return (
    <div className="fixed inset-0 z-[110] flex items-center justify-center bg-slate-950/50 p-4">
      <section
        role="dialog"
        aria-modal="true"
        aria-labelledby="dados-adicionais-nota-titulo"
        className="flex max-h-[92dvh] w-full max-w-2xl flex-col rounded-xl bg-white text-slate-900 shadow-xl dark:bg-slate-900 dark:text-slate-100"
      >
        <div className="border-b border-slate-200 p-5 dark:border-slate-700">
          <h2
            id="dados-adicionais-nota-titulo"
            className="flex items-center gap-2 text-xl font-semibold"
          >
            <FileText className="h-5 w-5" />
            Dados adicionais da NF-e
          </h2>
          <p className="mt-2 text-sm text-slate-600 dark:text-slate-300">
            Confira o canal desta operação e as informações que acompanharão a nota. Depois de
            salvar, você revisará o resumo antes de confirmar a emissão.
          </p>
        </div>
        <div className="space-y-4 overflow-y-auto p-5">
          {carregando ? (
            <p role="status">Carregando os dados da nota...</p>
          ) : (
            dados && (
              <>
                {!podeEditar && (
                  <p
                    role="alert"
                    className="rounded-lg bg-amber-50 p-3 text-sm text-amber-900 dark:bg-amber-950 dark:text-amber-100"
                  >
                    Os dados fiscais desta venda estão protegidos e não podem ser alterados por esta
                    revisão. Confira a situação da venda e da nota em NF de Saída antes de
                    continuar.
                  </p>
                )}
                <InputCombobox
                  id="nota-canal-operacao"
                  label="Canal desta operação"
                  value={dados.canal}
                  onChange={(valor) => alterar("canal", valor)}
                  opcoes={CANAIS_DADOS_NOTA}
                  permitirLimpar={false}
                  disabled={disabled}
                />
                <div className="grid gap-4 sm:grid-cols-2">
                  <InputTexto
                    label={amazon ? "Número do pedido da Amazon" : "Número do pedido (opcional)"}
                    value={dados.numero_pedido}
                    onChange={(valor) => alterar("numero_pedido", valor)}
                    disabled={disabled}
                    required={amazon}
                    maxLength={100}
                  />
                  <InputTexto
                    label="Código de rastreamento (opcional)"
                    value={dados.codigo_rastreamento}
                    onChange={(valor) => alterar("codigo_rastreamento", valor)}
                    disabled={disabled}
                    maxLength={100}
                  />
                </div>
                {amazon && (
                  <div className="space-y-4 rounded-lg border border-slate-200 p-4 dark:border-slate-700">
                    <h3 className="text-sm font-semibold">Intermediador da operação</h3>
                    <InputCpfCnpj
                      label="CNPJ do intermediador"
                      value={dados.intermediador_cnpj}
                      onChange={(valor) => alterar("intermediador_cnpj", valor)}
                      disabled={disabled}
                      required
                      help="Informe o CNPJ correspondente ao intermediador desta operação."
                    />
                    <InputTexto
                      label="Identificação da sua loja ou vendedor na Amazon"
                      value={dados.intermediador_identificacao}
                      onChange={(valor) => alterar("intermediador_identificacao", valor)}
                      disabled={disabled}
                      required
                      maxLength={60}
                      help="Use o código de cadastro da sua loja ou vendedor na Amazon. Esse dado é diferente do número do pedido."
                    />
                  </div>
                )}
                <InputTextoLongo
                  label="Informações complementares"
                  value={dados.informacoes_complementares}
                  onChange={(valor) => alterar("informacoes_complementares", valor)}
                  disabled={disabled}
                  linhas={4}
                  maxLength={4000}
                  help="Serão incluídas nas informações adicionais da nota, junto dos dados fiscais automáticos."
                />
              </>
            )
          )}
          {erro && (
            <p
              role="alert"
              className="rounded-lg bg-red-50 p-3 text-sm text-red-800 dark:bg-red-950 dark:text-red-100"
            >
              {erro}
            </p>
          )}
        </div>
        <div className="flex flex-wrap justify-end gap-2 border-t border-slate-200 p-5 dark:border-slate-700">
          <BotaoCancelar
            onClick={() => resolverDadosAdicionaisNota(dialogo.id, false)}
            disabled={salvando}
          >
            {podeEditar ? "Voltar" : "Fechar"}
          </BotaoCancelar>
          {!carregando && !dados && (
            <BotaoInteracao icon={RefreshCw} onClick={() => setVersao((atual) => atual + 1)}>
              Tentar carregar novamente
            </BotaoInteracao>
          )}
          {dados && podeEditar && (
            <BotaoSalva onClick={salvar} disabled={carregando || salvando} loading={salvando}>
              Salvar e revisar nota
            </BotaoSalva>
          )}
        </div>
      </section>
    </div>
  );
}

export default function NFeAdditionalDataDialogHost() {
  const [dialogo, setDialogo] = useState(null);
  useEffect(() => assinarDadosAdicionaisNota(setDialogo), []);
  return dialogo ? <NFeAdditionalDataDialog key={dialogo.id} dialogo={dialogo} /> : null;
}
