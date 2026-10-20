import { useEffect, useMemo, useRef, useState } from "react";
import { ChevronLeft, ChevronRight, RefreshCw } from "lucide-react";
import api from "../../api";
import ModalPadrao from "../../components/v2/ModalPadrao/ModalPadrao";
import BotaoCancelar from "../../components/v2/BotaoCancelar/BotaoCancelar";
import BotaoInteracao from "../../components/v2/BotaoInteracao/BotaoInteracao";
import InputCombobox from "../../components/v2/InputCombobox/InputCombobox";
import InputTexto from "../../components/v2/InputTexto/InputTexto";
import LinkPadrao from "../../components/v2/LinkPadrao/LinkPadrao";
import { formatarDataContabilidade, mensagemErroContabilidade } from "./xmlContabilidadeUtils.mjs";
import {
  filtrarDocumentosRelatorio,
  linkNotaRelatorio,
  quantidadeRelatorio,
  RESULTADOS_RELATORIO,
  valorRelatorio,
} from "./xmlContabilidadeRelatorioUtils.mjs";

const POR_PAGINA = 25;
const FILTROS = [
  { value: "todas", label: "Todos os documentos" },
  { value: "pendentes", label: "Notas pendentes" },
  { value: "nao_enviadas", label: "Não enviadas" },
  { value: "enviadas", label: "Enviadas" },
];
const ESTADOS = {
  pendente: "Aguardando confirmação fiscal",
  preparada: "XML preparado",
  nao_preparada: "XML não preparado",
  somente_eventos: "Somente eventos — fora do total de notas",
};

function Campo({ titulo, children }) {
  return (
    <div className="min-w-0">
      <dt className="text-xs text-slate-500 dark:text-slate-400">{titulo}</dt>
      <dd className="mt-1 break-words text-sm text-slate-800 dark:text-slate-200">{children}</dd>
    </div>
  );
}

function Resumo({ relatorio }) {
  const contagens = relatorio.contagens || {};
  const valores = relatorio.valores || {};
  const temPendencias = Number(contagens.notas_pendentes) > 0;
  const enviado = ["enviado", "enviado_com_pendencias"].includes(relatorio.resultado);
  const indicadores = [
    ["Notas encontradas", contagens.notas_encontradas],
    ["Notas preparadas", contagens.notas_preparadas],
    ["Notas enviadas", contagens.notas_enviadas],
    ["Notas não enviadas", contagens.notas_nao_enviadas],
    ["Notas pendentes", contagens.notas_pendentes],
    ["Canceladas (dentro do total)", contagens.notas_canceladas],
    ["Eventos encontrados", contagens.eventos_encontrados],
    ["Eventos preparados", contagens.eventos_preparados],
    ["Eventos enviados", contagens.eventos_enviados],
  ];
  return (
    <div className="space-y-5">
      <div className="rounded-lg bg-slate-100 p-4 dark:bg-slate-800">
        <p className="font-semibold text-slate-900 dark:text-slate-100">
          {RESULTADOS_RELATORIO[relatorio.resultado] || relatorio.resultado || "Indisponível"}
        </p>
        {relatorio.motivo ? <p className="mt-2 text-sm">{relatorio.motivo}</p> : null}
        {relatorio.acao_recomendada ? (
          <p className="mt-2 text-sm">Como resolver: {relatorio.acao_recomendada}</p>
        ) : null}
        {relatorio.resultado === "bloqueado" ? (
          <p className="mt-2 text-sm font-semibold">
            O lote inteiro foi bloqueado. XML preparado não significa XML enviado.
          </p>
        ) : null}
        {enviado ? (
          <p className="mt-2 text-xs text-slate-600 dark:text-slate-300">
            Enviado significa aceito pelo servidor de e-mail. O relatório não confirma leitura nem
            entrega na caixa de entrada do contador.
          </p>
        ) : null}
      </div>
      {temPendencias ? (
        <p
          role="alert"
          className="rounded-lg bg-amber-50 p-4 text-sm text-amber-900 dark:bg-amber-950/40 dark:text-amber-200"
        >
          {quantidadeRelatorio(contagens.notas_pendentes)} nota(s) pendente(s) não foram enviadas.
          Elas precisam de confirmação fiscal. Confira o motivo e o atalho em cada documento abaixo.
          As notas autorizadas com XML válido podem ser enviadas sem esperar essas pendências.
        </p>
      ) : null}
      <dl className="grid grid-cols-2 gap-3 sm:grid-cols-3">
        {indicadores.map(([titulo, valor]) => (
          <div
            key={titulo}
            className="rounded-lg border border-slate-200 p-3 dark:border-slate-700"
          >
            <dt className="text-xs text-slate-600 dark:text-slate-400">{titulo}</dt>
            <dd className="mt-1 break-words text-lg font-semibold">{quantidadeRelatorio(valor)}</dd>
          </div>
        ))}
      </dl>
      <p className="text-xs text-slate-500 dark:text-slate-400">
        Canceladas fazem parte do total de notas. Eventos são contados separadamente. Documentos de
        notas antigas incluídos somente pelos eventos não aumentam o total de notas.
      </p>
      <div>
        <h4 className="mb-3 font-semibold">Valores das notas</h4>
        <dl className="grid grid-cols-2 gap-4 sm:grid-cols-3">
          <Campo titulo="Total encontrado">{valorRelatorio(valores.total_notas)}</Campo>
          <Campo titulo="Canceladas encontradas">{valorRelatorio(valores.total_canceladas)}</Campo>
          <Campo titulo="Total menos canceladas">{valorRelatorio(valores.total_liquido)}</Campo>
          <Campo titulo="Valor das notas enviadas">{valorRelatorio(valores.total_enviadas)}</Campo>
          <Campo titulo="Canceladas enviadas">
            {valorRelatorio(valores.total_canceladas_enviadas)}
          </Campo>
          <Campo titulo="Total não enviado">{valorRelatorio(valores.total_nao_enviadas)}</Campo>
        </dl>
        <p className="mt-3 text-xs text-slate-500 dark:text-slate-400">
          Notas com valor disponível: {quantidadeRelatorio(valores.notas_com_valor)}. Sem valor:{" "}
          {quantidadeRelatorio(valores.notas_sem_valor)}. Valores desconhecidos aparecem como
          indisponíveis, sem serem convertidos em zero.
        </p>
      </div>
      {(contagens.eventos_por_tipo || []).length ? (
        <div className="overflow-x-auto">
          <h4 className="mb-2 font-semibold">Eventos por tipo</h4>
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="border-b border-slate-200 dark:border-slate-700">
                <th className="p-2">Tipo</th>
                <th className="p-2">Encontrados</th>
                <th className="p-2">Preparados</th>
                <th className="p-2">Enviados</th>
              </tr>
            </thead>
            <tbody>
              {contagens.eventos_por_tipo.map((evento) => (
                <tr key={evento.tipo} className="border-b border-slate-100 dark:border-slate-800">
                  <td className="p-2">
                    {evento.nome || evento.tipo} ({evento.tipo})
                  </td>
                  <td className="p-2">{quantidadeRelatorio(evento.encontrados)}</td>
                  <td className="p-2">{quantidadeRelatorio(evento.preparados)}</td>
                  <td className="p-2">{quantidadeRelatorio(evento.enviados)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}
    </div>
  );
}

function Documentos({ documentos }) {
  const [busca, setBusca] = useState("");
  const [situacao, setSituacao] = useState("todas");
  const [pagina, setPagina] = useState(1);
  const filtrados = useMemo(
    () => filtrarDocumentosRelatorio(documentos, busca, situacao),
    [documentos, busca, situacao],
  );
  const paginas = Math.max(1, Math.ceil(filtrados.length / POR_PAGINA));
  const atuais = filtrados.slice((pagina - 1) * POR_PAGINA, pagina * POR_PAGINA);
  return (
    <section className="space-y-4">
      <h4 className="font-semibold">Documentos desta tentativa</h4>
      <div className="grid gap-3 sm:grid-cols-2">
        <InputTexto
          id="relatorio-busca"
          label="Buscar número, chave ou motivo"
          value={busca}
          onChange={(valor) => {
            setBusca(valor);
            setPagina(1);
          }}
        />
        <InputCombobox
          id="relatorio-situacao"
          label="Situação do envio"
          value={situacao}
          opcoes={FILTROS}
          permitirLimpar={false}
          onChange={(valor) => {
            setSituacao(valor);
            setPagina(1);
          }}
        />
      </div>
      <p className="text-xs text-slate-500 dark:text-slate-400">
        {quantidadeRelatorio(filtrados.length)} de {quantidadeRelatorio(documentos.length)}{" "}
        documento(s). Os totais acima se referem à tentativa inteira.
      </p>
      {atuais.map((doc, indice) => (
        <article
          key={`${doc.documento_id}-${doc.chave}-${indice}`}
          className="space-y-3 rounded-lg border border-slate-200 p-4 dark:border-slate-700"
        >
          <h5 className="font-semibold">
            {String(doc.modelo) === "65"
              ? "NFC-e"
              : String(doc.modelo) === "55"
                ? "NF-e"
                : "Nota fiscal"}{" "}
            {doc.numero ? `nº ${doc.numero}` : "sem número disponível"}
          </h5>
          <dl className="grid grid-cols-2 gap-3">
            <Campo titulo="Situação fiscal">{doc.status_fiscal || "Indisponível"}</Campo>
            <Campo titulo="Processamento">
              {ESTADOS[doc.estado] || doc.estado || "Indisponível"}
            </Campo>
            <Campo titulo="Enviado por e-mail">
              {doc.enviada == null ? "Indisponível" : doc.enviada ? "Sim" : "Não"}
            </Campo>
            <Campo titulo="Valor da nota">{valorRelatorio(doc.valor_nf)}</Campo>
            <Campo titulo="Data de emissão">{formatarDataContabilidade(doc.data_emissao)}</Campo>
            <Campo titulo="Identificador">{doc.documento_id || "Indisponível"}</Campo>
          </dl>
          <p className="break-all text-xs text-slate-500 dark:text-slate-400">
            Chave: {doc.chave || "Indisponível"}
          </p>
          {doc.motivo ? <p className="text-sm">Motivo: {doc.motivo}</p> : null}
          {doc.acao_recomendada ? (
            <p className="text-sm">Como resolver: {doc.acao_recomendada}</p>
          ) : null}
          {doc.eventos?.length ? (
            <ul className="space-y-2 border-t border-slate-100 pt-3 text-xs dark:border-slate-800">
              {doc.eventos.map((evento, index) => (
                <li key={`${evento.tipo}-${evento.sequencia}-${index}`} className="break-words">
                  {evento.nome || evento.tipo} · sequência {evento.sequencia ?? "indisponível"} ·{" "}
                  {formatarDataContabilidade(
                    evento.data_hora_registro || evento.data_registro,
                    Boolean(evento.data_hora_registro),
                  )}{" "}
                  · preparado: {evento.preparado ? "sim" : "não"} · enviado:{" "}
                  {evento.enviado ? "sim" : "não"}
                  <span className="mt-1 block">
                    Protocolo: {evento.protocolo || "Indisponível"}
                  </span>
                </li>
              ))}
            </ul>
          ) : null}
          <LinkPadrao to={linkNotaRelatorio(doc)} novaJanela>
            Conferir na Central de NF
          </LinkPadrao>
        </article>
      ))}
      {!atuais.length ? (
        <p className="text-sm">Nenhum documento corresponde a esse filtro.</p>
      ) : null}
      {paginas > 1 ? (
        <div className="flex flex-wrap items-center gap-2">
          <BotaoInteracao
            icon={ChevronLeft}
            tamanho="pequeno"
            disabled={pagina <= 1}
            onClick={() => setPagina(pagina - 1)}
          >
            Anterior
          </BotaoInteracao>
          <span className="text-sm">
            Página {pagina} de {paginas}
          </span>
          <BotaoInteracao
            icon={ChevronRight}
            tamanho="pequeno"
            disabled={pagina >= paginas}
            onClick={() => setPagina(pagina + 1)}
          >
            Próxima
          </BotaoInteracao>
        </div>
      ) : null}
    </section>
  );
}

export default function XmlContabilidadeRelatorio({ envio, onFechar }) {
  const [lista, setLista] = useState(null);
  const [selecionado, setSelecionado] = useState(null);
  const [relatorio, setRelatorio] = useState(null);
  const [carregandoLista, setCarregandoLista] = useState(true);
  const [carregandoDetalhe, setCarregandoDetalhe] = useState(true);
  const [erro, setErro] = useState("");
  const [versao, setVersao] = useState(0);
  const modalRef = useRef(null);
  const base = `/contabilidade/xml/envios/${encodeURIComponent(envio.id)}/relatorios`;

  useEffect(() => {
    const anterior = document.activeElement;
    modalRef.current?.querySelector("button")?.focus();
    return () => anterior?.focus?.();
  }, []);

  useEffect(() => {
    let ativo = true;
    const controller = new AbortController();
    void (async () => {
      try {
        const { data } = await api.get(base, { signal: controller.signal });
        if (!ativo) return;
        const resumos = [...(data.relatorios || [])].sort(
          (a, b) => b.numero_tentativa - a.numero_tentativa,
        );
        setLista({ ...data, relatorios: resumos });
        if (resumos.length) setSelecionado(resumos[0].id);
        else setCarregandoDetalhe(false);
      } catch (error_) {
        const mensagem = await mensagemErroContabilidade(
          error_,
          "Não foi possível carregar os relatórios.",
        );
        if (ativo) {
          setErro(mensagem);
          setCarregandoDetalhe(false);
        }
      } finally {
        if (ativo) setCarregandoLista(false);
      }
    })();
    return () => {
      ativo = false;
      controller.abort();
    };
  }, [base, versao]);

  useEffect(() => {
    if (selecionado == null) return undefined;
    let ativo = true;
    const controller = new AbortController();
    void (async () => {
      try {
        const { data } = await api.get(`${base}/${encodeURIComponent(selecionado)}`, {
          signal: controller.signal,
        });
        if (ativo) setRelatorio(data);
      } catch (error_) {
        const mensagem = await mensagemErroContabilidade(
          error_,
          "Não foi possível carregar esta tentativa.",
        );
        if (ativo) setErro(mensagem);
      } finally {
        if (ativo) setCarregandoDetalhe(false);
      }
    })();
    return () => {
      ativo = false;
      controller.abort();
    };
  }, [base, selecionado]);

  const carregando = carregandoLista || carregandoDetalhe;
  function tentarNovamente() {
    setCarregandoLista(true);
    setCarregandoDetalhe(true);
    setErro("");
    setRelatorio(null);
    setSelecionado(null);
    setLista(null);
    setVersao(versao + 1);
  }
  return (
    <div
      ref={modalRef}
      role="dialog"
      aria-modal="true"
      aria-label="Relatório de tentativas do envio XML"
    >
      <ModalPadrao
        tamanho="grande"
        titulo={`Relatório do envio #${envio.id}`}
        onFechar={onFechar}
        rodape={<BotaoCancelar onClick={onFechar}>Fechar relatório</BotaoCancelar>}
      >
        <div className="space-y-5 text-slate-700 dark:text-slate-300">
          <p className="text-sm">
            Cada tentativa mantém seu relatório. Abrir esta tela consulta o registro salvo e não
            reenvia os XMLs.
          </p>
          {lista?.relatorios?.length ? (
            <InputCombobox
              id="xml-relatorio-tentativa"
              label="Tentativa"
              value={selecionado}
              permitirLimpar={false}
              opcoes={lista.relatorios.map((resumo) => ({
                value: resumo.id,
                label: `Tentativa ${resumo.numero_tentativa} · ${formatarDataContabilidade(resumo.iniciado_em, true)} · ${RESULTADOS_RELATORIO[resumo.resultado] || resumo.resultado}`,
              }))}
              onChange={(valor) => {
                if (String(valor) === String(selecionado)) return;
                setCarregandoDetalhe(true);
                setErro("");
                setRelatorio(null);
                setSelecionado(valor);
              }}
            />
          ) : null}
          {carregando ? (
            <output className="block py-10 text-center">
              Carregando relatório da tentativa...
            </output>
          ) : null}
          {!carregando && erro ? (
            <div>
              <p role="alert" className="mb-3 text-sm text-red-700 dark:text-red-300">
                {erro}
              </p>
              <BotaoInteracao icon={RefreshCw} onClick={tentarNovamente}>
                Tentar novamente
              </BotaoInteracao>
            </div>
          ) : null}
          {!carregando && !erro && !relatorio ? (
            <p className="rounded-lg bg-slate-100 p-4 text-sm dark:bg-slate-800">
              {lista?.mensagem ||
                "Nenhum relatório foi registrado para este envio. Aguarde a primeira tentativa de processamento e abra novamente."}
            </p>
          ) : null}
          {!carregando && !erro && relatorio ? (
            <>
              <dl className="grid grid-cols-2 gap-4">
                <Campo titulo="Destinatário desta tentativa">
                  {relatorio.email_destino || "Indisponível"}
                </Campo>
                <Campo titulo="Período">
                  {formatarDataContabilidade(relatorio.data_inicio)} a{" "}
                  {formatarDataContabilidade(relatorio.data_fim)}
                </Campo>
                <Campo titulo="Iniciada em">
                  {formatarDataContabilidade(relatorio.iniciado_em, true)}
                </Campo>
                <Campo titulo="Concluída em">
                  {formatarDataContabilidade(relatorio.concluido_em, true)}
                </Campo>
              </dl>
              <Resumo relatorio={relatorio} />
              {relatorio.pendencias?.length ? (
                <section>
                  <h4 className="mb-2 font-semibold">Avisos e pendências da tentativa</h4>
                  <ul className="space-y-3 text-sm">
                    {relatorio.pendencias.map((pendencia, index) => (
                      <li
                        key={`${pendencia.codigo}-${index}`}
                        className="rounded-lg border border-amber-200 p-3 dark:border-amber-900"
                      >
                        <p>{pendencia.motivo}</p>
                        {pendencia.acao_recomendada ? (
                          <p className="mt-1">Como resolver: {pendencia.acao_recomendada}</p>
                        ) : null}
                      </li>
                    ))}
                  </ul>
                </section>
              ) : null}
              <Documentos key={relatorio.id} documentos={relatorio.documentos || []} />
              {relatorio.anexos?.length ? (
                <section>
                  <h4 className="mb-2 font-semibold">Arquivos preparados para esta tentativa</h4>
                  <ul className="space-y-2 text-xs">
                    {relatorio.anexos.map((anexo) => (
                      <li key={anexo.nome_arquivo} className="break-all">
                        {anexo.nome_arquivo} · {quantidadeRelatorio(anexo.quantidade_xml)} XML(s) ·{" "}
                        {quantidadeRelatorio(anexo.bytes)} bytes
                      </li>
                    ))}
                  </ul>
                </section>
              ) : null}
            </>
          ) : null}
        </div>
      </ModalPadrao>
    </div>
  );
}
