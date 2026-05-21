import { X } from "lucide-react";
import ActionButton from "../ui/ActionButton";

const TIPO_LANCAMENTO = {
  entrada: {
    label: "Entrada",
    activeClass: "bg-green-600 text-white",
    idleClass: "bg-slate-100 text-slate-700 hover:bg-slate-200",
  },
  saida: {
    label: "Saida",
    activeClass: "bg-red-600 text-white",
    idleClass: "bg-slate-100 text-slate-700 hover:bg-slate-200",
  },
  balanco: {
    label: "Balanco",
    activeClass: "bg-blue-600 text-white",
    idleClass: "bg-slate-100 text-slate-700 hover:bg-slate-200",
  },
};

const MOTIVOS_SAIDA = [
  { value: "saida_manual", label: "Saida manual" },
  { value: "uso_interno", label: "Uso interno" },
  { value: "perda", label: "Perda" },
  { value: "avaria", label: "Avaria" },
  { value: "amostra", label: "Amostra" },
  { value: "devolucao_fornecedor", label: "Devolucao ao fornecedor" },
  { value: "ajuste", label: "Ajuste" },
];

function TipoButton({ active, disabled = false, onClick, tipo }) {
  const config = TIPO_LANCAMENTO[tipo];
  const className = disabled
    ? "cursor-not-allowed bg-slate-100 text-slate-400"
    : active
      ? config.activeClass
      : config.idleClass;

  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      className={`rounded-lg px-4 py-2 text-sm font-medium transition-colors ${className}`}
    >
      {config.label}
    </button>
  );
}

export default function EstoqueLancamentoModal({
  editingMovimentacao,
  estoqueAtual,
  formData,
  onClose,
  onSubmit,
  produto,
  produtoEhGranel,
  setFormData,
  setTipoLancamento,
  tipoLancamento,
}) {
  const updateFormData = (campo, valor) => {
    setFormData({ ...formData, [campo]: valor });
  };

  const handleMotivoSaidaChange = (valor) => {
    setFormData({
      ...formData,
      motivo_saida: valor,
      gerar_despesa_uso_interno:
        valor === "uso_interno" ? true : formData.gerar_despesa_uso_interno,
      descricao_despesa:
        valor === "uso_interno" && !formData.descricao_despesa
          ? `Material de uso interno - ${produto?.nome || "Produto"}`
          : formData.descricao_despesa,
    });
  };

  const produtoEhKitFisico = produto?.tipo_produto === "KIT" && produto?.tipo_kit === "FISICO";

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
      <div className="w-full max-w-md overflow-hidden rounded-lg bg-white shadow-xl">
        <div className="flex items-center justify-between border-b border-slate-200 px-6 py-4">
          <h3 className="text-lg font-semibold text-slate-900">
            {editingMovimentacao ? "Editar lancamento" : "Novo lancamento"}
          </h3>
          <button
            type="button"
            onClick={onClose}
            className="rounded-full p-1 text-slate-400 transition hover:bg-slate-100 hover:text-slate-700"
            aria-label="Fechar"
          >
            <X size={20} aria-hidden="true" />
          </button>
        </div>

        <form onSubmit={onSubmit} className="max-h-[82vh] space-y-4 overflow-y-auto p-6">
          {!editingMovimentacao && (
            <div>
              <label className="mb-2 block text-sm font-medium text-slate-700">Tipo *</label>
              <div className="grid grid-cols-3 gap-2">
                <TipoButton
                  active={tipoLancamento === "entrada"}
                  disabled={produtoEhGranel}
                  onClick={() => {
                    if (!produtoEhGranel) {
                      setTipoLancamento("entrada");
                    }
                  }}
                  tipo="entrada"
                />
                <TipoButton
                  active={tipoLancamento === "saida"}
                  onClick={() => setTipoLancamento("saida")}
                  tipo="saida"
                />
                <TipoButton
                  active={tipoLancamento === "balanco"}
                  onClick={() => setTipoLancamento("balanco")}
                  tipo="balanco"
                />
              </div>
            </div>
          )}

          <div>
            <label className="mb-1 block text-sm font-medium text-slate-700">
              {tipoLancamento === "balanco" ? "Saldo total *" : "Quantidade *"}
            </label>
            <input
              type="number"
              step="0.01"
              value={formData.quantidade}
              onChange={(event) => updateFormData("quantidade", event.target.value)}
              className="w-full rounded-lg border border-slate-300 px-4 py-2 focus:border-transparent focus:ring-2 focus:ring-blue-500"
              required
            />
            {tipoLancamento === "balanco" ? (
              <p className="mt-1 text-xs text-slate-500">
                Estoque atual: {estoqueAtual}. Digite o novo saldo total.
              </p>
            ) : null}
            {produtoEhGranel && tipoLancamento === "entrada" ? (
              <p className="mt-1 text-xs text-cyan-700">
                Para abastecer granel, abra o produto fechado e use Lancar granel.
              </p>
            ) : null}
            {produtoEhGranel && tipoLancamento === "balanco" ? (
              <p className="mt-1 text-xs text-cyan-700">
                Balanco manual permitido para ajuste de inventario. Para abastecer por pacote aberto,
                use Lancar granel no produto fechado.
              </p>
            ) : null}
          </div>

          {tipoLancamento === "entrada" && !produtoEhGranel ? (
            <>
              <div>
                <label className="mb-1 block text-sm font-medium text-slate-700">Preco de compra</label>
                <input
                  type="number"
                  step="0.01"
                  value={formData.custo_unitario}
                  onChange={(event) => updateFormData("custo_unitario", event.target.value)}
                  className="w-full rounded-lg border border-slate-300 px-4 py-2 focus:border-transparent focus:ring-2 focus:ring-blue-500"
                  placeholder="0.00"
                />
              </div>

              <div>
                <label className="mb-1 block text-sm font-medium text-slate-700">
                  Numero do lote <span className="text-slate-400">(opcional)</span>
                </label>
                <input
                  type="text"
                  value={formData.lote}
                  onChange={(event) => updateFormData("lote", event.target.value)}
                  className="w-full rounded-lg border border-slate-300 px-4 py-2 focus:border-transparent focus:ring-2 focus:ring-blue-500"
                  placeholder="Ex: LOTE-001"
                />
              </div>

              <div>
                <label className="mb-1 block text-sm font-medium text-slate-700">
                  Data de validade <span className="text-slate-400">(opcional)</span>
                </label>
                <input
                  type="date"
                  value={formData.data_validade}
                  onChange={(event) => updateFormData("data_validade", event.target.value)}
                  className="w-full rounded-lg border border-slate-300 px-4 py-2 focus:border-transparent focus:ring-2 focus:ring-blue-500"
                />
              </div>

              <div>
                <label className="mb-1 block text-sm font-medium text-slate-700">
                  Data de fabricacao <span className="text-slate-400">(opcional)</span>
                </label>
                <input
                  type="date"
                  value={formData.data_fabricacao}
                  onChange={(event) => updateFormData("data_fabricacao", event.target.value)}
                  className="w-full rounded-lg border border-slate-300 px-4 py-2 focus:border-transparent focus:ring-2 focus:ring-blue-500"
                />
              </div>
            </>
          ) : null}

          {tipoLancamento === "saida" ? (
            <>
              <div>
                <label className="mb-1 block text-sm font-medium text-slate-700">Motivo da saida *</label>
                <select
                  value={formData.motivo_saida || "saida_manual"}
                  onChange={(event) => handleMotivoSaidaChange(event.target.value)}
                  className="w-full rounded-lg border border-slate-300 px-4 py-2 focus:border-transparent focus:ring-2 focus:ring-blue-500"
                  required
                >
                  {MOTIVOS_SAIDA.map((motivo) => (
                    <option key={motivo.value} value={motivo.value}>
                      {motivo.label}
                    </option>
                  ))}
                </select>
              </div>

              {formData.motivo_saida === "uso_interno" ? (
                <div className="space-y-3 rounded-lg border border-amber-200 bg-amber-50 p-4">
                  <label className="flex cursor-pointer items-start gap-3 text-sm font-semibold text-slate-900">
                    <input
                      type="checkbox"
                      checked={formData.gerar_despesa_uso_interno === true}
                      onChange={(event) => updateFormData("gerar_despesa_uso_interno", event.target.checked)}
                      className="mt-1 h-4 w-4 rounded border-slate-300 text-amber-600 focus:ring-amber-500"
                    />
                    <span>Lancar custo no financeiro/DRE</span>
                  </label>

                  {formData.gerar_despesa_uso_interno === true ? (
                    <>
                      <div>
                        <label className="mb-1 block text-sm font-medium text-slate-700">Data de competencia</label>
                        <input
                          type="date"
                          value={formData.data_competencia || ""}
                          onChange={(event) => updateFormData("data_competencia", event.target.value)}
                          className="w-full rounded-lg border border-slate-300 px-4 py-2 focus:border-transparent focus:ring-2 focus:ring-blue-500"
                        />
                      </div>

                      <div>
                        <label className="mb-1 block text-sm font-medium text-slate-700">Descricao da despesa</label>
                        <input
                          type="text"
                          value={formData.descricao_despesa || ""}
                          onChange={(event) => updateFormData("descricao_despesa", event.target.value)}
                          className="w-full rounded-lg border border-slate-300 px-4 py-2 focus:border-transparent focus:ring-2 focus:ring-blue-500"
                          placeholder="Material de uso interno"
                        />
                      </div>
                    </>
                  ) : null}
                </div>
              ) : null}

              {produtoEhKitFisico ? (
                <div className="rounded-lg border-2 border-yellow-300 bg-yellow-50 p-4">
                  <div className="flex items-start gap-3">
                    <input
                      type="checkbox"
                      id="retornar_componentes"
                      checked={formData.retornar_componentes === true}
                      onChange={(event) => updateFormData("retornar_componentes", event.target.checked)}
                      className="mt-1 h-5 w-5 rounded border-slate-300 text-green-600 focus:ring-green-500"
                    />
                    <div className="flex-1">
                      <label
                        htmlFor="retornar_componentes"
                        className="block cursor-pointer text-sm font-semibold text-slate-900"
                      >
                        Desmontar kit e retornar componentes ao estoque
                      </label>
                      <p className="mt-1 text-xs text-slate-700">
                        Marque se desmontou o kit e quer devolver os produtos unitarios ao estoque.
                      </p>
                      <p className="mt-1 text-xs text-slate-600">
                        Deixe desmarcado quando houve perda, roubo ou venda do kit montado.
                      </p>
                    </div>
                  </div>
                </div>
              ) : null}

              <div>
                <label className="mb-1 block text-sm font-medium text-slate-700">
                  Numero do lote <span className="text-slate-400">(opcional)</span>
                </label>
                <input
                  type="text"
                  value={formData.lote}
                  onChange={(event) => updateFormData("lote", event.target.value)}
                  className="w-full rounded-lg border border-slate-300 px-4 py-2 focus:border-transparent focus:ring-2 focus:ring-blue-500"
                  placeholder="Ex: LOTE-001"
                />
                <p className="mt-1 text-xs text-slate-500">Deixe vazio para usar FIFO automatico</p>
              </div>

              <div>
                <label className="mb-1 block text-sm font-medium text-slate-700">
                  Data de validade <span className="text-slate-400">(opcional)</span>
                </label>
                <input
                  type="date"
                  value={formData.data_validade}
                  onChange={(event) => updateFormData("data_validade", event.target.value)}
                  className="w-full rounded-lg border border-slate-300 px-4 py-2 focus:border-transparent focus:ring-2 focus:ring-blue-500"
                />
              </div>
            </>
          ) : null}

          <div>
            <label className="mb-1 block text-sm font-medium text-slate-700">Observacao</label>
            <textarea
              value={formData.observacao}
              onChange={(event) => updateFormData("observacao", event.target.value)}
              rows={3}
              className="w-full rounded-lg border border-slate-300 px-4 py-2 focus:border-transparent focus:ring-2 focus:ring-blue-500"
              placeholder="Observacoes sobre este lancamento..."
            />
          </div>

          <div className="flex gap-3 pt-4">
            <ActionButton className="flex-1 justify-center" onClick={onClose} tone="soft">
              Cancelar
            </ActionButton>
            <ActionButton className="flex-1 justify-center" intent="create" type="submit">
              {editingMovimentacao ? "Salvar" : "Incluir"}
            </ActionButton>
          </div>
        </form>
      </div>
    </div>
  );
}
