import { useEffect, useState } from "react";
import toast from "react-hot-toast";
import {
  AlertTriangle,
  Camera,
  CheckCircle2,
  ClipboardList,
  ExternalLink,
  PackagePlus,
  Receipt,
  RefreshCw,
  Trash2,
  X,
} from "lucide-react";
import ActionButton from "../../../components/ui/ActionButton";
import { CheckboxField, SelectField, TextField } from "../../../components/ui/FormField";
import PetAvatar from "../../../components/ui/PetAvatar";
import { formatMoneyBRL } from "../../../utils/formatters";
import { resolveMediaUrl } from "../../../utils/mediaUrl";
import { banhoTosaApi } from "../banhoTosaApi";
import { formatNumber, getApiErrorMessage, toApiDecimal } from "../banhoTosaUtils";

const ABAS = [
  { id: "resumo", label: "Resumo" },
  { id: "consumo", label: "Consumo" },
  { id: "ocorrencias", label: "Ocorrências" },
  { id: "fotos", label: "Fotos" },
  { id: "fechamento", label: "Fechamento" },
];

export default function BanhoTosaAtendimentoPanel({
  atendimentoId,
  funcionarios = [],
  initialTab = "resumo",
  onChanged,
  onClose,
}) {
  const [aba, setAba] = useState(initialTab);
  const [dados, setDados] = useState(null);
  const [insumos, setInsumos] = useState([]);
  const [ocorrencias, setOcorrencias] = useState([]);
  const [fotos, setFotos] = useState([]);
  const [custo, setCusto] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState("");

  useEffect(() => {
    setAba(initialTab);
  }, [atendimentoId, initialTab]);

  useEffect(() => {
    carregarFicha();
  }, [atendimentoId]);

  async function carregarFicha(silent = false) {
    if (!silent) setLoading(true);
    try {
      const [atendimentoRes, insumosRes, ocorrenciasRes, fotosRes, custoRes] = await Promise.all([
        banhoTosaApi.obterAtendimento(atendimentoId),
        banhoTosaApi.listarInsumosAtendimento(atendimentoId),
        banhoTosaApi.listarOcorrenciasAtendimento(atendimentoId),
        banhoTosaApi.listarFotosAtendimento(atendimentoId),
        banhoTosaApi.obterCustoAtendimento(atendimentoId),
      ]);
      setDados(atendimentoRes.data || null);
      setInsumos(Array.isArray(insumosRes.data) ? insumosRes.data : []);
      setOcorrencias(Array.isArray(ocorrenciasRes.data) ? ocorrenciasRes.data : []);
      setFotos(Array.isArray(fotosRes.data) ? fotosRes.data : []);
      setCusto(custoRes.data || null);
    } catch (error) {
      toast.error(getApiErrorMessage(error, "Não foi possível carregar a ficha operacional."));
    } finally {
      setLoading(false);
    }
  }

  async function executar(chave, operacao, mensagem) {
    setSaving(chave);
    try {
      await operacao();
      toast.success(mensagem);
      await carregarFicha(true);
      await onChanged?.();
    } catch (error) {
      toast.error(getApiErrorMessage(error, "Não foi possível concluir a operação."));
    } finally {
      setSaving("");
    }
  }

  if (!atendimentoId) return null;

  return (
    <div className="fixed inset-0 z-50 bg-slate-950/40 backdrop-blur-[1px]">
      <aside
        aria-label="Ficha operacional do atendimento"
        aria-modal="true"
        className="ml-auto flex h-full w-full max-w-3xl flex-col bg-slate-50 shadow-2xl"
        role="dialog"
      >
        <header className="border-b border-slate-200 bg-white px-4 py-3 sm:px-6">
          <div className="flex items-start justify-between gap-3">
            <div className="flex min-w-0 items-center gap-3">
              <PetAvatar name={dados?.pet_nome} size="lg" url={dados?.pet_foto_url} />
              <div className="min-w-0">
                <p className="text-xs font-semibold uppercase tracking-wide text-blue-700">
                  Ficha operacional #{atendimentoId}
                </p>
                <h2 className="truncate text-lg font-semibold text-slate-950">
                  {dados?.pet_nome || "Carregando pet..."}
                </h2>
                <p className="truncate text-sm text-slate-500">
                  Tutor: {dados?.cliente_nome || `#${dados?.cliente_id || "-"}`}
                </p>
              </div>
            </div>
            <div className="flex gap-1">
              <button
                aria-label="Atualizar ficha"
                className="rounded-lg p-2 text-slate-500 transition hover:bg-slate-100"
                type="button"
                onClick={() => carregarFicha()}
              >
                <RefreshCw size={19} className={loading ? "animate-spin" : ""} />
              </button>
              <button
                aria-label="Fechar ficha"
                className="rounded-lg p-2 text-slate-500 transition hover:bg-slate-100"
                type="button"
                onClick={onClose}
              >
                <X size={20} />
              </button>
            </div>
          </div>

          <nav className="-mx-1 mt-3 flex gap-1 overflow-x-auto px-1 pb-1">
            {ABAS.map((item) => (
              <button
                key={item.id}
                className={[
                  "whitespace-nowrap rounded-lg px-3 py-2 text-sm font-semibold transition",
                  aba === item.id ? "bg-blue-600 text-white" : "text-slate-600 hover:bg-slate-100",
                ].join(" ")}
                type="button"
                onClick={() => setAba(item.id)}
              >
                {item.label}
              </button>
            ))}
          </nav>
        </header>

        <div className="flex-1 overflow-y-auto p-4 sm:p-6">
          {loading && !dados ? (
            <div className="py-16 text-center text-sm font-medium text-slate-500">
              Carregando ficha...
            </div>
          ) : (
            <>
              {aba === "resumo" && <Resumo dados={dados} custo={custo} />}
              {aba === "consumo" && (
                <Consumo
                  atendimentoId={atendimentoId}
                  funcionarios={funcionarios}
                  insumos={insumos}
                  saving={saving}
                  executar={executar}
                />
              )}
              {aba === "ocorrencias" && (
                <Ocorrencias
                  atendimentoId={atendimentoId}
                  funcionarios={funcionarios}
                  ocorrencias={ocorrencias}
                  saving={saving}
                  executar={executar}
                />
              )}
              {aba === "fotos" && (
                <Fotos
                  atendimentoId={atendimentoId}
                  fotos={fotos}
                  saving={saving}
                  executar={executar}
                />
              )}
              {aba === "fechamento" && (
                <Fechamento
                  atendimento={dados}
                  custo={custo}
                  saving={saving}
                  executar={executar}
                  onDelivered={() => setAba("resumo")}
                />
              )}
            </>
          )}
        </div>
      </aside>
    </div>
  );
}

function Resumo({ dados, custo }) {
  const etapas = dados?.etapas || [];
  return (
    <div className="space-y-4">
      <div className="grid gap-3 sm:grid-cols-3">
        <ResumoCard label="Etapa atual" value={dados?.etapa_atual_label || dados?.status || "-"} />
        <ResumoCard
          label="Tempo"
          value={formatarDuracao(dados?.tempo_decorrido_segundos)}
          alerta={dados?.atrasado}
        />
        <ResumoCard
          label="Margem prevista"
          value={formatMoneyBRL(custo?.margem_valor || 0)}
          subtitle={`${formatNumber(custo?.margem_percentual || 0, 1)}%`}
        />
      </div>

      {(dados?.restricoes_veterinarias_snapshot &&
        Object.keys(dados.restricoes_veterinarias_snapshot).length > 0) ||
      (dados?.perfil_comportamental_snapshot &&
        Object.keys(dados.perfil_comportamental_snapshot).length > 0) ? (
        <div className="rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900">
          <div className="flex items-center gap-2 font-semibold">
            <AlertTriangle size={18} />
            Atenções do pet
          </div>
          <p className="mt-2 text-xs">
            Consulte as restrições veterinárias e o perfil comportamental antes de avançar.
          </p>
        </div>
      ) : null}

      <section className="rounded-xl border border-slate-200 bg-white p-4">
        <h3 className="font-semibold text-slate-950">Linha do tempo</h3>
        <div className="mt-3 space-y-2">
          {etapas.length ? (
            etapas.map((etapa) => (
              <div
                key={etapa.id}
                className="flex flex-col gap-1 rounded-lg bg-slate-50 px-3 py-2 sm:flex-row sm:items-center sm:justify-between"
              >
                <div>
                  <p className="text-sm font-semibold text-slate-800">{labelEtapa(etapa.tipo)}</p>
                  <p className="text-xs text-slate-500">
                    {etapa.responsavel_nome || "Sem responsável"}
                    {etapa.recurso_nome ? ` · ${etapa.recurso_nome}` : ""}
                  </p>
                </div>
                <p
                  className={
                    etapa.atrasado ? "text-sm font-semibold text-red-600" : "text-sm text-slate-600"
                  }
                >
                  {etapa.fim_em
                    ? formatarDuracao(etapa.duracao_segundos)
                    : `${formatarDuracao(etapa.tempo_decorrido_segundos)} em andamento`}
                </p>
              </div>
            ))
          ) : (
            <p className="text-sm text-slate-500">Nenhuma etapa cronometrada ainda.</p>
          )}
        </div>
      </section>

      <section className="rounded-xl border border-slate-200 bg-white p-4">
        <h3 className="font-semibold text-slate-950">Observações</h3>
        <p className="mt-2 whitespace-pre-wrap text-sm text-slate-600">
          {dados?.observacoes_entrada || "Sem observações de entrada."}
        </p>
      </section>
    </div>
  );
}

function Consumo({ atendimentoId, funcionarios, insumos, saving, executar }) {
  const [busca, setBusca] = useState("");
  const [produtos, setProdutos] = useState([]);
  const [produtoId, setProdutoId] = useState("");
  const [quantidade, setQuantidade] = useState("");
  const [desperdicio, setDesperdicio] = useState("");
  const [responsavelId, setResponsavelId] = useState("");
  const [baixarEstoque, setBaixarEstoque] = useState(false);

  async function buscar() {
    if (busca.trim().length < 2) {
      toast.error("Digite ao menos 2 caracteres para buscar.");
      return;
    }
    try {
      const response = await banhoTosaApi.listarProdutosEstoque(busca.trim());
      setProdutos(Array.isArray(response.data) ? response.data : []);
    } catch (error) {
      toast.error(getApiErrorMessage(error, "Não foi possível buscar produtos."));
    }
  }

  async function registrar(event) {
    event.preventDefault();
    if (!produtoId || Number(quantidade || 0) + Number(desperdicio || 0) <= 0) {
      toast.error("Selecione o produto e informe a quantidade.");
      return;
    }
    await executar(
      "insumo",
      () =>
        banhoTosaApi.registrarInsumoAtendimento(atendimentoId, {
          produto_id: Number(produtoId),
          quantidade_usada: toApiDecimal(quantidade),
          quantidade_desperdicio: toApiDecimal(desperdicio),
          responsavel_id: responsavelId ? Number(responsavelId) : null,
          baixar_estoque: baixarEstoque,
        }),
      "Consumo registrado.",
    );
    setQuantidade("");
    setDesperdicio("");
  }

  return (
    <div className="space-y-4">
      <form className="rounded-xl border border-slate-200 bg-white p-4" onSubmit={registrar}>
        <div className="flex items-center gap-2">
          <PackagePlus size={19} className="text-blue-600" />
          <h3 className="font-semibold text-slate-950">Registrar consumo</h3>
        </div>
        <div className="mt-4 flex gap-2">
          <TextField
            className="flex-1"
            label="Buscar produto"
            placeholder="Shampoo, condicionador..."
            value={busca}
            onChange={setBusca}
          />
          <ActionButton className="mt-6" intent="neutral" tone="soft" onClick={buscar}>
            Buscar
          </ActionButton>
        </div>
        <SelectField className="mt-3" label="Produto" value={produtoId} onChange={setProdutoId}>
          <option value="">Selecione</option>
          {produtos.map((produto) => (
            <option key={produto.id} value={produto.id}>
              {produto.nome} {produto.unidade ? `(${produto.unidade})` : ""}
            </option>
          ))}
        </SelectField>
        <div className="mt-3 grid gap-3 sm:grid-cols-2">
          <TextField
            label="Quantidade usada"
            type="number"
            value={quantidade}
            onChange={setQuantidade}
          />
          <TextField
            label="Desperdício"
            type="number"
            value={desperdicio}
            onChange={setDesperdicio}
          />
          <SelectField label="Responsável" value={responsavelId} onChange={setResponsavelId}>
            <option value="">Sem responsável</option>
            {funcionarios.map((item) => (
              <option key={item.id} value={item.id}>
                {item.nome}
              </option>
            ))}
          </SelectField>
          <CheckboxField
            className="mt-6"
            checked={baixarEstoque}
            label="Dar baixa no estoque"
            onChange={setBaixarEstoque}
          />
        </div>
        <ActionButton
          className="mt-4 w-full justify-center"
          icon={PackagePlus}
          intent="create"
          loading={saving === "insumo"}
          type="submit"
        >
          Registrar consumo
        </ActionButton>
      </form>

      <section className="rounded-xl border border-slate-200 bg-white p-4">
        <h3 className="font-semibold text-slate-950">Itens usados</h3>
        <div className="mt-3 divide-y divide-slate-100">
          {insumos.length ? (
            insumos.map((item) => (
              <div key={item.id} className="flex items-center justify-between gap-3 py-3">
                <div>
                  <p className="text-sm font-semibold text-slate-800">{item.produto_nome}</p>
                  <p className="text-xs text-slate-500">
                    Usado: {formatNumber(item.quantidade_usada, 3)} · Desperdício:{" "}
                    {formatNumber(item.quantidade_desperdicio, 3)}
                  </p>
                </div>
                <p className="text-sm font-semibold text-slate-700">
                  {formatMoneyBRL(item.custo_total)}
                </p>
              </div>
            ))
          ) : (
            <p className="py-3 text-sm text-slate-500">Nenhum consumo registrado.</p>
          )}
        </div>
      </section>
    </div>
  );
}

function Ocorrencias({ atendimentoId, funcionarios, ocorrencias, saving, executar }) {
  const [tipo, setTipo] = useState("observacao");
  const [gravidade, setGravidade] = useState("baixa");
  const [descricao, setDescricao] = useState("");
  const [responsavelId, setResponsavelId] = useState("");

  async function registrar(event) {
    event.preventDefault();
    if (!descricao.trim()) {
      toast.error("Descreva a ocorrência.");
      return;
    }
    await executar(
      "ocorrencia",
      () =>
        banhoTosaApi.registrarOcorrenciaAtendimento(atendimentoId, {
          tipo,
          gravidade,
          descricao: descricao.trim(),
          responsavel_id: responsavelId ? Number(responsavelId) : null,
        }),
      "Ocorrência registrada.",
    );
    setDescricao("");
  }

  return (
    <div className="space-y-4">
      <form className="rounded-xl border border-slate-200 bg-white p-4" onSubmit={registrar}>
        <div className="flex items-center gap-2">
          <ClipboardList size={19} className="text-blue-600" />
          <h3 className="font-semibold text-slate-950">Nova ocorrência</h3>
        </div>
        <div className="mt-4 grid gap-3 sm:grid-cols-2">
          <SelectField label="Tipo" value={tipo} onChange={setTipo}>
            <option value="observacao">Observação</option>
            <option value="comportamento">Comportamento</option>
            <option value="saude">Saúde</option>
            <option value="acidente">Acidente</option>
          </SelectField>
          <SelectField label="Gravidade" value={gravidade} onChange={setGravidade}>
            <option value="baixa">Baixa</option>
            <option value="media">Média</option>
            <option value="alta">Alta</option>
          </SelectField>
          <SelectField label="Responsável" value={responsavelId} onChange={setResponsavelId}>
            <option value="">Sem responsável</option>
            {funcionarios.map((item) => (
              <option key={item.id} value={item.id}>
                {item.nome}
              </option>
            ))}
          </SelectField>
          <TextField label="Descrição" value={descricao} onChange={setDescricao} />
        </div>
        <ActionButton
          className="mt-4 w-full justify-center"
          icon={ClipboardList}
          intent="create"
          loading={saving === "ocorrencia"}
          type="submit"
        >
          Registrar ocorrência
        </ActionButton>
      </form>

      <section className="rounded-xl border border-slate-200 bg-white p-4">
        <h3 className="font-semibold text-slate-950">Histórico</h3>
        <div className="mt-3 space-y-2">
          {ocorrencias.length ? (
            ocorrencias
              .slice()
              .reverse()
              .map((item) => (
                <div
                  key={item.id}
                  className={[
                    "rounded-lg border p-3",
                    item.gravidade === "alta"
                      ? "border-red-200 bg-red-50"
                      : "border-slate-200 bg-slate-50",
                  ].join(" ")}
                >
                  <div className="flex justify-between gap-3">
                    <p className="text-sm font-semibold text-slate-800">
                      {item.tipo} · {item.gravidade}
                    </p>
                    <button
                      aria-label="Remover ocorrência"
                      className="text-slate-400 hover:text-red-600"
                      type="button"
                      onClick={() =>
                        executar(
                          `ocorrencia-${item.id}`,
                          () => banhoTosaApi.removerOcorrenciaAtendimento(atendimentoId, item.id),
                          "Ocorrência removida.",
                        )
                      }
                    >
                      <Trash2 size={16} />
                    </button>
                  </div>
                  <p className="mt-1 text-sm text-slate-600">{item.descricao}</p>
                  {item.responsavel_nome && (
                    <p className="mt-1 text-xs text-slate-500">{item.responsavel_nome}</p>
                  )}
                </div>
              ))
          ) : (
            <p className="text-sm text-slate-500">Nenhuma ocorrência registrada.</p>
          )}
        </div>
      </section>
    </div>
  );
}

function Fotos({ atendimentoId, fotos, saving, executar }) {
  const [arquivo, setArquivo] = useState(null);
  const [tipo, setTipo] = useState("entrada");
  const [descricao, setDescricao] = useState("");

  async function enviar(event) {
    event.preventDefault();
    if (!arquivo) {
      toast.error("Selecione uma imagem.");
      return;
    }
    const formData = new FormData();
    formData.append("arquivo", arquivo);
    formData.append("tipo", tipo);
    if (descricao.trim()) formData.append("descricao", descricao.trim());
    await executar(
      "foto",
      () => banhoTosaApi.uploadFotoAtendimento(atendimentoId, formData),
      "Foto adicionada.",
    );
    setArquivo(null);
    setDescricao("");
  }

  return (
    <div className="space-y-4">
      <form className="rounded-xl border border-slate-200 bg-white p-4" onSubmit={enviar}>
        <div className="flex items-center gap-2">
          <Camera size={19} className="text-blue-600" />
          <h3 className="font-semibold text-slate-950">Adicionar foto</h3>
        </div>
        <div className="mt-4 grid gap-3 sm:grid-cols-2">
          <SelectField label="Momento" value={tipo} onChange={setTipo}>
            <option value="entrada">Entrada</option>
            <option value="durante">Durante</option>
            <option value="saida">Saída</option>
          </SelectField>
          <TextField label="Descrição" value={descricao} onChange={setDescricao} />
        </div>
        <label className="mt-3 block text-xs font-medium text-slate-600">
          Imagem
          <input
            accept="image/jpeg,image/png,image/webp"
            className="mt-1 block w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm"
            type="file"
            onChange={(event) => setArquivo(event.target.files?.[0] || null)}
          />
        </label>
        <ActionButton
          className="mt-4 w-full justify-center"
          icon={Camera}
          intent="create"
          loading={saving === "foto"}
          type="submit"
        >
          Enviar foto
        </ActionButton>
      </form>

      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
        {fotos.map((foto) => (
          <figure
            key={foto.id}
            className="overflow-hidden rounded-xl border border-slate-200 bg-white"
          >
            <img
              alt={foto.descricao || `Foto de ${foto.tipo}`}
              className="aspect-square w-full object-cover"
              src={resolveMediaUrl(foto.thumbnail_url || foto.url)}
            />
            <figcaption className="flex items-center justify-between gap-2 p-2">
              <div className="min-w-0">
                <p className="truncate text-xs font-semibold text-slate-700">{foto.tipo}</p>
                <p className="truncate text-[11px] text-slate-500">
                  {foto.descricao || "Sem descrição"}
                </p>
              </div>
              <button
                aria-label="Remover foto"
                className="text-slate-400 hover:text-red-600"
                type="button"
                onClick={() =>
                  executar(
                    `foto-${foto.id}`,
                    () => banhoTosaApi.removerFotoAtendimento(atendimentoId, foto.id),
                    "Foto removida.",
                  )
                }
              >
                <Trash2 size={16} />
              </button>
            </figcaption>
          </figure>
        ))}
      </div>
      {!fotos.length && <p className="text-sm text-slate-500">Nenhuma foto registrada.</p>}
    </div>
  );
}

function Fechamento({ atendimento, custo, saving, executar, onDelivered }) {
  const [confirmado, setConfirmado] = useState(false);
  const [observacoesSaida, setObservacoesSaida] = useState(atendimento?.observacoes_saida || "");
  const quitadoPorPacote = Boolean(atendimento?.pacote_credito_id);
  const temVenda = Boolean(atendimento?.venda_id);
  const podeEntregar = quitadoPorPacote || temVenda;

  async function gerarVenda() {
    let pdvUrl = null;
    await executar(
      "venda",
      async () => {
        const response = await banhoTosaApi.gerarVendaAtendimento(atendimento.id);
        pdvUrl = response.data?.pdv_url;
      },
      "Cobrança enviada ao PDV.",
    );
    if (pdvUrl) window.open(pdvUrl, "_blank", "noopener,noreferrer");
  }

  async function entregar() {
    await executar(
      "entrega",
      () =>
        banhoTosaApi.moverEtapaAtendimento(atendimento.id, {
          tipo: "entregue",
          iniciar_timer: false,
          observacoes_saida: observacoesSaida.trim() || null,
        }),
      "Entrega confirmada e atendimento encerrado.",
    );
    setConfirmado(false);
    onDelivered?.();
  }

  return (
    <div className="space-y-4">
      <div className="grid gap-3 sm:grid-cols-3">
        <ResumoCard
          label="Valor"
          value={formatMoneyBRL(atendimento?.venda_total || custo?.valor_cobrado || 0)}
        />
        <ResumoCard label="Custo" value={formatMoneyBRL(custo?.custo_total || 0)} />
        <ResumoCard
          label="Margem"
          value={formatMoneyBRL(custo?.margem_valor || 0)}
          subtitle={`${formatNumber(custo?.margem_percentual || 0, 1)}%`}
        />
      </div>

      <section className="rounded-xl border border-slate-200 bg-white p-4">
        <div className="flex items-center gap-2">
          <Receipt size={19} className="text-blue-600" />
          <h3 className="font-semibold text-slate-950">Cobrança</h3>
        </div>
        {quitadoPorPacote ? (
          <div className="mt-3 rounded-lg border border-emerald-200 bg-emerald-50 p-3 text-sm font-semibold text-emerald-800">
            Quitado pelo pacote {atendimento.pacote_nome || ""}.
          </div>
        ) : temVenda ? (
          <div className="mt-3">
            <p className="text-sm font-semibold text-slate-800">
              Venda {atendimento.venda_numero || `#${atendimento.venda_id}`} ·{" "}
              {labelPagamento(atendimento.venda_status_pagamento)}
            </p>
            <p className="mt-1 text-sm text-slate-500">
              Pago: {formatMoneyBRL(atendimento.venda_total_pago || 0)} · Restante:{" "}
              {formatMoneyBRL(atendimento.venda_valor_restante || 0)}
            </p>
            <div className="mt-3 flex flex-wrap gap-2">
              <ActionButton
                icon={ExternalLink}
                intent="info"
                onClick={() => window.open(atendimento.pdv_url, "_blank", "noopener,noreferrer")}
              >
                Abrir no PDV
              </ActionButton>
              <ActionButton
                icon={RefreshCw}
                intent="neutral"
                loading={saving === "sync"}
                tone="soft"
                onClick={() =>
                  executar(
                    "sync",
                    () => banhoTosaApi.sincronizarFechamentoAtendimento(atendimento.id),
                    "Fechamento sincronizado.",
                  )
                }
              >
                Sincronizar
              </ActionButton>
            </div>
          </div>
        ) : (
          <div className="mt-3">
            <p className="text-sm text-slate-600">
              Gere a venda antes de confirmar a entrega. O PDV abrirá com os serviços do
              atendimento.
            </p>
            <ActionButton
              className="mt-3"
              icon={Receipt}
              intent="create"
              loading={saving === "venda"}
              onClick={gerarVenda}
            >
              Gerar cobrança no PDV
            </ActionButton>
          </div>
        )}
      </section>

      <section className="rounded-xl border border-slate-200 bg-white p-4">
        <div className="flex items-center gap-2">
          <CheckCircle2 size={19} className="text-emerald-600" />
          <h3 className="font-semibold text-slate-950">Entrega do pet</h3>
        </div>
        {atendimento?.status === "entregue" ? (
          <p className="mt-3 rounded-lg bg-emerald-50 p-3 text-sm font-semibold text-emerald-800">
            Atendimento já entregue e encerrado.
          </p>
        ) : (
          <>
            <TextField
              className="mt-3"
              label="Observações de saída"
              placeholder="Orientações passadas ao tutor"
              value={observacoesSaida}
              onChange={setObservacoesSaida}
            />
            <CheckboxField
              className="mt-3"
              checked={confirmado}
              disabled={!podeEntregar}
              label="Confirmo que o pet foi entregue ao tutor e a cobrança foi orientada"
              onChange={setConfirmado}
            />
            {!podeEntregar && (
              <p className="mt-2 text-xs font-medium text-amber-700">
                Gere a cobrança ou vincule um pacote antes da entrega.
              </p>
            )}
            <ActionButton
              className="mt-4 w-full justify-center"
              disabled={!confirmado || !podeEntregar}
              icon={CheckCircle2}
              intent="create"
              loading={saving === "entrega"}
              size="md"
              onClick={entregar}
            >
              Confirmar entrega e encerrar
            </ActionButton>
          </>
        )}
      </section>
    </div>
  );
}

function ResumoCard({ alerta = false, label, subtitle, value }) {
  return (
    <div
      className={[
        "rounded-xl border bg-white p-4",
        alerta ? "border-red-200" : "border-slate-200",
      ].join(" ")}
    >
      <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">{label}</p>
      <p
        className={["mt-1 text-lg font-semibold", alerta ? "text-red-600" : "text-slate-950"].join(
          " ",
        )}
      >
        {value}
      </p>
      {subtitle && <p className="text-xs text-slate-500">{subtitle}</p>}
    </div>
  );
}

function formatarDuracao(segundos) {
  const total = Math.max(0, Number(segundos || 0));
  const horas = Math.floor(total / 3600);
  const minutos = Math.floor((total % 3600) / 60);
  if (horas) return `${horas}h ${minutos}min`;
  return `${minutos} min`;
}

function labelEtapa(etapa) {
  return String(etapa || "")
    .replaceAll("_", " ")
    .replace(/\b\w/g, (letra) => letra.toUpperCase());
}

function labelPagamento(status) {
  return (
    {
      pago: "Pago",
      parcial: "Pagamento parcial",
      pendente: "Pagamento pendente",
      quitado_pacote: "Quitado por pacote",
    }[status] || "Aguardando pagamento"
  );
}
