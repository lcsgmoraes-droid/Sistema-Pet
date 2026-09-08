export default function ProdutosFusaoOpcoes({
  estrategia,
  onEstrategiaChange,
  aliasesTexto,
  onAliasesChange,
  preview,
  preservarBling,
  onPreservarBlingChange,
  disabled,
}) {
  return (
    <section className="mb-4 space-y-3" aria-label="Estoque e identidades da fusão">
      <fieldset disabled={disabled} className="rounded-lg border border-slate-200 p-3 space-y-2">
        <legend className="px-1 font-semibold text-slate-900">Como tratar o estoque?</legend>
        <label className="flex items-start gap-2 text-sm text-slate-700">
          <input
            type="radio"
            name="estrategia-estoque"
            value="somar"
            checked={estrategia === "somar"}
            onChange={() => onEstrategiaChange("somar")}
            className="mt-1"
          />
          <span>As quantidades se somam: os dois cadastros representam unidades diferentes.</span>
        </label>
        <label className="flex items-start gap-2 text-sm text-slate-700">
          <input
            type="radio"
            name="estrategia-estoque"
            value="manter_principal"
            checked={estrategia === "manter_principal"}
            onChange={() => onEstrategiaChange("manter_principal")}
            className="mt-1"
          />
          <span>
            O duplicado já está incluído no principal: manter as quantidades do principal.
          </span>
        </label>
        {estrategia === "manter_principal" && (
          <p className="text-xs text-slate-600">
            SKU, nome, unidade, códigos de barras, custos, preços e promoções do principal serão
            preservados.
          </p>
        )}
      </fieldset>
      <label className="block text-sm text-slate-700">
        <span className="font-semibold">SKUs alternativos adicionais (opcional)</span>
        <textarea
          value={aliasesTexto}
          onChange={(event) => onAliasesChange(event.target.value)}
          disabled={disabled}
          className="mt-1 min-h-16 w-full rounded-lg border border-slate-300 px-3 py-2"
        />
        <span className="text-xs text-slate-500">
          O SKU do duplicado será mantido automaticamente como identidade do principal. Adicione até
          20 SKUs de pedidos ou anúncios cuja identidade foi conferida, separados por linha ou
          vírgula. Códigos de barras são campos próprios do cadastro.
        </span>
      </label>
      {preview && (
        <>
          <div className="rounded-lg border border-emerald-200 bg-emerald-50 p-3">
            <h3 className="mb-2 text-sm font-semibold text-emerald-900">
              Estoque final no principal
            </h3>
            <div className="grid gap-2 text-sm text-emerald-900 sm:grid-cols-3">
              {Object.entries(preview.estoque_final || {}).map(([campo, valor]) => (
                <div key={campo} className="rounded-md bg-white/70 p-2">
                  <span className="block">
                    {{
                      estoque_atual: "Atual",
                      estoque_fisico: "Físico",
                      estoque_ecommerce: "E-commerce",
                    }[campo] || campo}
                  </span>
                  <strong>
                    {valor == null ? "Indisponível" : Number(valor).toLocaleString("pt-BR")}
                  </strong>
                </div>
              ))}
            </div>
          </div>
          {Number(preview.filas_pendentes || 0) > 0 && (
            <p role="alert" className="rounded-lg bg-amber-50 p-3 text-sm text-amber-900">
              Há {preview.filas_pendentes} sincronizações Bling pendentes. Aguarde a conclusão e
              revise a fusão novamente.
            </p>
          )}
          {preview.conflito_bling && (
            <div className="rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900">
              <p className="font-semibold">Os produtos possuem vínculos Bling diferentes.</p>
              <ul className="my-2 space-y-1">
                {(preview.vinculos_bling || []).map((item) => (
                  <li key={item.produto_id}>
                    Produto {item.produto_id}: Bling {item.bling_produto_id}
                  </li>
                ))}
              </ul>
              <label className="flex items-start gap-2">
                <input
                  type="checkbox"
                  checked={preservarBling}
                  onChange={(event) => onPreservarBlingChange(event.target.checked)}
                  disabled={disabled}
                  className="mt-1"
                />
                <span>
                  Confirmo manter o vínculo Bling do principal e retirar o vínculo do duplicado. O
                  vínculo retirado servirá apenas ao histórico dos pedidos, sem atualizar estoque,
                  custo ou cadastro.
                </span>
              </label>
            </div>
          )}
        </>
      )}
    </section>
  );
}
