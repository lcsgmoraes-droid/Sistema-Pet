const CONFIANCA = {
  alta: {
    rotulo: "Alta confiança",
    classe: "bg-emerald-100 text-emerald-800 dark:bg-emerald-500/15 dark:text-emerald-200",
  },
  media: {
    rotulo: "Média confiança",
    classe: "bg-amber-100 text-amber-800 dark:bg-amber-500/15 dark:text-amber-200",
  },
  baixa: {
    rotulo: "Baixa confiança",
    classe: "bg-rose-100 text-rose-800 dark:bg-rose-500/15 dark:text-rose-200",
  },
};

const FONTES_SUGESTAO = {
  referencia_oficial_luvas_de_procedimento:
    "consulta tributária da SEFAZ-SP sobre luvas de procedimento",
  catalogo_fiscal: "catálogo fiscal do CorePet",
  configuracao_fiscal_da_empresa: "configuração fiscal da empresa",
  xml_ou_cadastro_do_produto_e_regime_da_empresa: "XML/cadastro do produto e regime da empresa",
  regime_da_empresa_sem_historico_do_produto: "regime da empresa; sem histórico deste produto",
  regime_da_empresa_sem_padrao_configurado: "regime da empresa; sem padrão fiscal configurado",
  historico_de_produtos_semelhantes: "produtos semelhantes já cadastrados",
  palavras_da_descricao: "descrição do produto",
  correcao_de_codigo_incompleto: "correção de código fiscal incompleto",
  padrao_operacional_sem_origem_informada: "padrão operacional; origem não comprovada",
};

function fonteLegivel(fonte) {
  return FONTES_SUGESTAO[fonte] || String(fonte || "fonte não identificada").replaceAll("_", " ");
}

export default function FiscalCorrectionField({
  produto,
  item,
  fiscal,
  contextoFiscal,
  campo,
  opcoesPisCofins,
  correcaoDaNota,
  salvando,
  onChange,
}) {
  const opcoesBase = campo.tipo === "pis-cofins" ? opcoesPisCofins : campo.opcoes;
  const opcoes =
    item.campo === "cst_icms" &&
    contextoFiscal.regime_tributario &&
    typeof contextoFiscal.simples_nacional === "boolean"
      ? opcoesBase.filter(([valor]) =>
          contextoFiscal.simples_nacional ? valor.length === 3 : valor.length === 2,
        )
      : opcoesBase;
  const confianca = CONFIANCA[item.confianca];
  const campoId = `fiscal-${produto.chave}-${item.campo}`;
  const fonteFiscal =
    fiscal.fontesFiscais?.[
      item.campo === "pis_cst" ? "cst_pis" : item.campo === "cofins_cst" ? "cst_cofins" : item.campo
    ];
  const valorAtual = String(fiscal[item.campo] ?? "");
  const valorForaDaLista =
    valorAtual && Array.isArray(opcoes) && !opcoes.some(([valor]) => valor === valorAtual);
  const aplicadoNaConsulta = item.aplicado_na_consulta === true;
  const classeCampo = `w-full rounded-xl border-2 px-3 py-2.5 text-sm text-slate-900 outline-none dark:bg-slate-950 dark:text-slate-100 ${aplicadoNaConsulta ? "border-cyan-400 bg-cyan-50 focus:border-cyan-600 focus:ring-2 focus:ring-cyan-600/20" : "border-red-400 bg-red-50 focus:border-red-600 focus:ring-2 focus:ring-red-600/20"}`;
  return (
    <div key={item.campo} className="block">
      <label
        htmlFor={campoId}
        className={`mb-1.5 flex flex-wrap items-center gap-2 text-sm font-semibold ${aplicadoNaConsulta ? "text-cyan-800 dark:text-cyan-300" : "text-red-800 dark:text-red-300"}`}
      >
        {campo.rotulo}
        {confianca && (
          <span
            className={`rounded-full px-2 py-0.5 text-[11px] font-semibold ${confianca.classe}`}
          >
            {confianca.rotulo}
            {item.confianca_percentual ? ` · ${item.confianca_percentual}%` : ""}
          </span>
        )}
      </label>
      {campo.tipo === "select" || campo.tipo === "pis-cofins" ? (
        <select
          id={campoId}
          disabled={salvando}
          value={valorAtual}
          onChange={(event) => onChange(event.target.value)}
          aria-invalid={!aplicadoNaConsulta}
          aria-describedby={`${campoId}-erro`}
          className={classeCampo}
        >
          <option value="">Selecione...</option>
          {valorForaDaLista && (
            <option value={valorAtual}>{valorAtual} — valor atual inválido</option>
          )}
          {opcoes.map(([valor, rotulo]) => (
            <option key={valor} value={valor}>
              {rotulo}
            </option>
          ))}
        </select>
      ) : (
        <input
          id={campoId}
          disabled={salvando}
          value={valorAtual}
          inputMode="numeric"
          maxLength={campo.tamanho}
          placeholder={campo.placeholder}
          onChange={(event) => onChange(event.target.value.replace(/\D/g, ""))}
          aria-invalid={!aplicadoNaConsulta}
          aria-describedby={`${campoId}-erro`}
          className={classeCampo}
        />
      )}
      <p
        id={`${campoId}-erro`}
        className={`mt-1.5 text-xs font-medium leading-5 ${aplicadoNaConsulta ? "text-cyan-700" : "text-red-700"}`}
      >
        {item.mensagem || item.motivo || "Confira este campo antes de emitir."}
      </p>
      {fonteFiscal?.tipo === "lote" && (
        <p className="mt-1.5 text-xs text-slate-600 dark:text-slate-300">
          O valor vem do lote {fonteFiscal.id}. A correção será aplicada ao lote usado nesta venda e
          ao cadastro do produto.
        </p>
      )}
      {item.valor_atual && valorAtual !== String(item.valor_atual) && (
        <p className="mt-1.5 text-xs font-semibold text-amber-800">
          {correcaoDaNota ? (
            <>Valor atual antes da correção: {item.valor_atual}.</>
          ) : (
            <>
              Valor que seria usado na nota: {item.valor_atual}. O cadastro, lote ou regra de
              ICMS-ST pode prevalecer sobre o valor mostrado no campo.
            </>
          )}
        </p>
      )}
      {item.valor_sugerido ? (
        <div className="mt-2 rounded-lg border border-slate-200 bg-slate-50 p-2.5 text-xs leading-5 text-slate-600 dark:border-slate-700 dark:bg-slate-800/60 dark:text-slate-300">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <p>
              Sugestão: <strong>{item.valor_sugerido}</strong>
            </p>
            <button
              type="button"
              disabled={salvando}
              onClick={() => onChange(item.valor_sugerido)}
              className="rounded-lg border border-cyan-300 bg-white px-2.5 py-1 font-semibold text-cyan-800 hover:bg-cyan-50 dark:border-cyan-700 dark:bg-slate-900 dark:text-cyan-200"
            >
              Usar esta sugestão
            </button>
          </div>
          <p className="mt-1">{item.motivo_sugestao || item.motivo}</p>
          <p className="mt-1 font-medium text-slate-500 dark:text-slate-400">
            Fonte: {fonteLegivel(item.fonte_sugestao)}.
          </p>
          {/^https?:\/\//.test(item.fonte_url || "") && (
            <a
              href={item.fonte_url}
              target="_blank"
              rel="noopener noreferrer"
              className="mt-1 inline-block font-semibold text-cyan-800 underline dark:text-cyan-200"
            >
              Conferir a fonte da sugestão
            </a>
          )}
        </div>
      ) : null}
    </div>
  );
}
