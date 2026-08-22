import { AlertCircle, CheckCircle2, CreditCard, ExternalLink, Unplug } from "lucide-react";

export default function EcommerceConfigView({
  loading,
  error,
  success,
  salvar,
  ativo,
  setAtivo,
  descricao,
  setDescricao,
  horarioAbertura,
  setHorarioAbertura,
  horarioFechamento,
  setHorarioFechamento,
  diasSelecionados,
  toggleDia,
  diasSemana,
  commerceConfig,
  setCommerceConfig,
  saving,
  mercadoPagoSectionRef,
  salvarPagamento,
  paymentLoading,
  oauthReturn,
  paymentConfig,
  paymentAccount,
  paymentAccountLoading,
  paymentAccountError,
  recarregarPaymentAccount,
  setPaymentConfig,
  desconectarMercadoPago,
  disconnectingPayment,
  conectarMercadoPago,
  connectingPayment,
  savingPayment,
  avisos,
  loadingAvisos,
}) {
  function updateCommerce(key, value) {
    setCommerceConfig((current) => ({ ...current, [key]: value }));
  }

  function ToggleSetting({ configKey, label, description }) {
    const enabled = Boolean(commerceConfig[configKey]);
    return (
      <div className="flex items-center justify-between gap-4 py-2">
        <div>
          <p className="font-medium text-gray-700">{label}</p>
          <p className="text-sm text-gray-500">{description}</p>
        </div>
        <button
          type="button"
          role="switch"
          aria-checked={enabled}
          aria-label={label}
          onClick={() => updateCommerce(configKey, !enabled)}
          className={`relative inline-flex h-7 w-12 shrink-0 items-center rounded-full transition-colors ${
            enabled ? "bg-indigo-500" : "bg-gray-300"
          }`}
        >
          <span
            className={`inline-block h-5 w-5 transform rounded-full bg-white shadow transition-transform ${
              enabled ? "translate-x-6" : "translate-x-1"
            }`}
          />
        </button>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[300px]">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-500" />
      </div>
    );
  }

  // Agrupar avisos por produto
  const avisosPorProduto = avisos.reduce((acc, aviso) => {
    const key = `${aviso.product_id}__${aviso.product_name || "Produto"}`;
    if (!acc[key])
      acc[key] = {
        product_id: aviso.product_id,
        product_name: aviso.product_name || "Produto",
        emails: [],
      };
    acc[key].emails.push(aviso.email);
    return acc;
  }, {});
  const hasPaymentCredential = Boolean(
    paymentConfig.oauth_connected || paymentConfig.access_token_configured,
  );

  return (
    <div className="max-w-2xl mx-auto p-6 space-y-8">
      <h1 className="text-2xl font-bold text-gray-900">⚙️ Configurações da Loja Virtual</h1>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 rounded-lg px-4 py-3 text-sm">
          {error}
        </div>
      )}
      {success && (
        <div className="bg-green-50 border border-green-200 text-green-700 rounded-lg px-4 py-3 text-sm">
          {success}
        </div>
      )}

      <form onSubmit={salvar} className="space-y-6">
        {/* Status da loja */}
        <div className="bg-white rounded-xl border border-gray-200 p-6 shadow-sm space-y-4">
          <h2 className="text-base font-semibold text-gray-800">Status da Loja</h2>

          <div className="flex items-center justify-between">
            <div>
              <p className="font-medium text-gray-700">Loja online</p>
              <p className="text-sm text-gray-500">
                {ativo
                  ? "Sua loja está visível e aceitando pedidos."
                  : "Sua loja está offline. Clientes não conseguem fazer pedidos."}
              </p>
            </div>
            <button
              type="button"
              role="switch"
              aria-checked={ativo}
              aria-label="Loja online"
              onClick={() => setAtivo((v) => !v)}
              className={`relative inline-flex h-7 w-12 items-center rounded-full transition-colors focus:outline-none ${
                ativo ? "bg-indigo-500" : "bg-gray-300"
              }`}
            >
              <span
                className={`inline-block h-5 w-5 transform rounded-full bg-white shadow transition-transform ${
                  ativo ? "translate-x-6" : "translate-x-1"
                }`}
              />
            </button>
          </div>
        </div>

        {/* Descrição */}
        <div className="bg-white rounded-xl border border-gray-200 p-6 shadow-sm space-y-3">
          <h2 className="text-base font-semibold text-gray-800">Descrição da Loja</h2>
          <textarea
            id="ecommerce-store-description"
            name="store_description"
            aria-label="Descrição da loja"
            value={descricao}
            onChange={(e) => setDescricao(e.target.value)}
            rows={3}
            maxLength={500}
            placeholder="Ex.: Petshop especializado em cães e gatos. Atendemos com carinho! 🐾"
            className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400 resize-none"
          />
          <p className="text-xs text-gray-400 text-right">{descricao.length}/500</p>
        </div>

        {/* Horário */}
        <div className="bg-white rounded-xl border border-gray-200 p-6 shadow-sm space-y-4">
          <h2 className="text-base font-semibold text-gray-800">Horário de Funcionamento</h2>
          <p className="text-sm text-gray-500">
            Exibido como informação na loja. Não bloqueia pedidos fora do horário.
          </p>
          <div className="flex gap-4 items-center">
            <div className="flex-1">
              <label
                htmlFor="ecommerce-opening-time"
                className="block text-xs font-medium text-gray-600 mb-1"
              >
                Abertura
              </label>
              <input
                id="ecommerce-opening-time"
                name="opening_time"
                type="time"
                value={horarioAbertura}
                onChange={(e) => setHorarioAbertura(e.target.value)}
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400"
              />
            </div>
            <span className="text-gray-400 mt-5">até</span>
            <div className="flex-1">
              <label
                htmlFor="ecommerce-closing-time"
                className="block text-xs font-medium text-gray-600 mb-1"
              >
                Fechamento
              </label>
              <input
                id="ecommerce-closing-time"
                name="closing_time"
                type="time"
                value={horarioFechamento}
                onChange={(e) => setHorarioFechamento(e.target.value)}
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400"
              />
            </div>
          </div>

          {/* Dias da semana */}
          <div>
            <p className="text-xs font-medium text-gray-600 mb-2">Dias de funcionamento</p>
            <div className="flex flex-wrap gap-2">
              {diasSemana.map((dia) => (
                <button
                  key={dia.key}
                  type="button"
                  onClick={() => toggleDia(dia.key)}
                  className={`px-3 py-1 rounded-full text-sm font-medium border transition-colors ${
                    diasSelecionados.includes(dia.key)
                      ? "bg-indigo-500 text-white border-indigo-500"
                      : "bg-white text-gray-600 border-gray-300 hover:border-indigo-400"
                  }`}
                >
                  {dia.label}
                </button>
              ))}
            </div>
          </div>
        </div>

        <div className="bg-white rounded-xl border border-gray-200 p-6 shadow-sm space-y-4">
          <div>
            <h2 className="text-base font-semibold text-gray-800">Entrega e retirada</h2>
            <p className="text-sm text-gray-500 mt-1">
              O aplicativo e o e-commerce agora usam exatamente a mesma regra de frete.
            </p>
          </div>
          <div className="rounded-lg border border-blue-100 bg-blue-50 p-4 text-sm text-blue-900">
            Configure taxa fixa ou preço por km, área máxima, frete grátis, pedido mínimo e prazo em
            um só lugar. A regra é recalculada pelo servidor antes de criar cada pedido.
          </div>
          <a
            href="/configuracoes/entregas"
            className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-700"
          >
            Abrir Configurações de Entregas
            <ExternalLink size={15} />
          </a>
        </div>

        <div className="bg-white rounded-xl border border-gray-200 p-6 shadow-sm space-y-3">
          <div>
            <h2 className="text-base font-semibold text-gray-800">Qualidade do catálogo</h2>
            <p className="text-sm text-gray-500 mt-1">
              Evite anunciar itens que o cliente não consegue comprar com confiança.
            </p>
          </div>
          <ToggleSetting
            configKey="ocultarSemEstoque"
            label="Ocultar produtos sem estoque"
            description="Recomendado para não mostrar milhares de itens indisponíveis."
          />
          <ToggleSetting
            configKey="ocultarSemImagem"
            label="Ocultar produtos sem imagem"
            description="Ative quando o catálogo visual estiver mais completo."
          />
          <ToggleSetting
            configKey="ocultarServicos"
            label="Ocultar serviços"
            description="Mantém banho, tosa e outros serviços fora da loja de produtos."
          />
          <ToggleSetting
            configKey="usarEstoqueCanal"
            label="Usar estoque reservado do e-commerce"
            description="Só ative depois de preencher o estoque do canal nos produtos."
          />
        </div>

        <div className="bg-white rounded-xl border border-gray-200 p-6 shadow-sm space-y-4">
          <div>
            <h2 className="text-base font-semibold text-gray-800">Cores da loja</h2>
            <p className="text-sm text-gray-500 mt-1">
              Aplicadas aos destaques, botões e mensagens comerciais.
            </p>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {[
              ["corPrimaria", "Cor principal"],
              ["corSecundaria", "Cor secundária"],
            ].map(([key, label]) => (
              <label key={key} className="text-xs font-medium text-gray-600">
                {label}
                <div className="mt-1 flex gap-2">
                  <input
                    id={`ecommerce-${key}-picker`}
                    name={`${key}_picker`}
                    aria-label={`${label}: seletor de cor`}
                    type="color"
                    value={commerceConfig[key]}
                    onChange={(event) => updateCommerce(key, event.target.value)}
                    className="h-10 w-12 rounded border border-gray-300"
                  />
                  <input
                    id={`ecommerce-${key}-value`}
                    name={`${key}_value`}
                    aria-label={`${label}: valor hexadecimal`}
                    value={commerceConfig[key]}
                    onChange={(event) => updateCommerce(key, event.target.value)}
                    pattern="^#[0-9A-Fa-f]{6}$"
                    className="flex-1 border border-gray-300 rounded-lg px-3 py-2 text-sm uppercase"
                  />
                </div>
              </label>
            ))}
          </div>
        </div>

        <button
          type="submit"
          disabled={saving}
          className="w-full bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white font-semibold py-2.5 rounded-xl transition-colors"
        >
          {saving ? "Salvando…" : "Salvar Configurações"}
        </button>
      </form>

      {/* Pagamentos online */}
      <form ref={mercadoPagoSectionRef} onSubmit={salvarPagamento} className="space-y-6">
        <div className="bg-white rounded-xl border border-gray-200 p-6 shadow-sm space-y-5">
          <div className="flex items-start gap-3">
            <div className="h-10 w-10 rounded-lg bg-emerald-50 text-emerald-700 flex items-center justify-center">
              <CreditCard size={20} />
            </div>
            <div>
              <h2 className="text-base font-semibold text-gray-800">Mercado Pago</h2>
              <p className="text-sm text-gray-500">
                Conta que recebe os pagamentos Pix, debito e credito desta loja.
              </p>
            </div>
          </div>

          {paymentLoading ? (
            <div className="animate-pulse h-24 bg-gray-100 rounded-lg" />
          ) : (
            <>
              {oauthReturn && (
                <div
                  className={`flex items-start gap-3 rounded-lg border px-4 py-3 text-sm ${
                    oauthReturn.status === "success"
                      ? "border-emerald-200 bg-emerald-50 text-emerald-800"
                      : "border-red-200 bg-red-50 text-red-700"
                  }`}
                >
                  <div className="mt-0.5">
                    {oauthReturn.status === "success" ? (
                      <CheckCircle2 size={18} />
                    ) : (
                      <AlertCircle size={18} />
                    )}
                  </div>
                  <div>
                    <p className="font-semibold">
                      {oauthReturn.status === "success"
                        ? "Conexao concluida"
                        : "Conexao nao concluida"}
                    </p>
                    <p>{oauthReturn.message}</p>
                  </div>
                </div>
              )}

              <div className="flex items-center justify-between gap-4 border border-gray-100 rounded-lg p-4">
                <div>
                  <p className="font-medium text-gray-700">Pagamento online</p>
                  <p className="text-sm text-gray-500">
                    {!hasPaymentCredential
                      ? "Será ativado automaticamente após conectar sua conta."
                      : paymentConfig.enabled
                        ? "Ativo no app e no e-commerce."
                        : "Desligado para esta loja."}
                  </p>
                </div>
                {hasPaymentCredential && (
                  <button
                    type="button"
                    role="switch"
                    aria-label="Pagamento online"
                    aria-checked={paymentConfig.enabled}
                    onClick={() =>
                      setPaymentConfig((prev) => ({ ...prev, enabled: !prev.enabled }))
                    }
                    className={`relative inline-flex h-7 w-12 items-center rounded-full transition-colors focus:outline-none ${
                      paymentConfig.enabled ? "bg-emerald-500" : "bg-gray-300"
                    }`}
                  >
                    <span
                      className={`inline-block h-5 w-5 transform rounded-full bg-white shadow transition-transform ${
                        paymentConfig.enabled ? "translate-x-6" : "translate-x-1"
                      }`}
                    />
                  </button>
                )}
              </div>

              <div className="border border-emerald-100 rounded-lg p-4 bg-emerald-50/40 space-y-3">
                <div className="flex items-start justify-between gap-4">
                  <div className="flex items-start gap-3">
                    <div
                      className={`mt-0.5 h-8 w-8 rounded-full flex items-center justify-center ${
                        paymentConfig.oauth_connected
                          ? "bg-emerald-100 text-emerald-700"
                          : "bg-white text-gray-500"
                      }`}
                    >
                      <CheckCircle2 size={18} />
                    </div>
                    <div>
                      <p className="font-medium text-gray-800">
                        {paymentConfig.oauth_connected
                          ? "Conta Mercado Pago conectada"
                          : paymentConfig.access_token_configured
                            ? "Mercado Pago configurado"
                            : "Conecte sua conta Mercado Pago"}
                      </p>
                      <p className="text-sm text-gray-500">
                        {paymentConfig.oauth_connected
                          ? "Confira abaixo a conta que receberá as vendas desta loja."
                          : paymentConfig.access_token_configured
                            ? "A configuração atual foi preservada. Conecte para usar o novo vínculo automático."
                            : "Clique em Conectar para entrar no Mercado Pago e autorizar o CorePet."}
                      </p>
                    </div>
                  </div>
                  {paymentConfig.oauth_connected ? (
                    <button
                      type="button"
                      onClick={desconectarMercadoPago}
                      disabled={disconnectingPayment}
                      className="inline-flex items-center gap-2 rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50"
                    >
                      <Unplug size={16} />
                      {disconnectingPayment ? "Desconectando..." : "Desconectar"}
                    </button>
                  ) : (
                    <button
                      type="button"
                      onClick={conectarMercadoPago}
                      disabled={connectingPayment || !paymentConfig.oauth_available}
                      className="inline-flex items-center gap-2 rounded-lg bg-emerald-600 px-3 py-2 text-sm font-semibold text-white hover:bg-emerald-700 disabled:opacity-50"
                    >
                      <ExternalLink size={16} />
                      {connectingPayment ? "Abrindo..." : "Conectar"}
                    </button>
                  )}
                </div>
                {paymentConfig.oauth_connected && (
                  <div className="rounded-lg border border-emerald-100 bg-white p-3">
                    {paymentAccountLoading ? (
                      <p className="text-sm text-gray-500">
                        Confirmando a conta no Mercado Pago...
                      </p>
                    ) : paymentAccount ? (
                      <div className="space-y-3">
                        <div
                          className={`flex items-center gap-2 text-sm font-semibold ${
                            paymentAccount.verified ? "text-emerald-700" : "text-amber-700"
                          }`}
                        >
                          {paymentAccount.verified ? (
                            <CheckCircle2 size={17} />
                          ) : (
                            <AlertCircle size={17} />
                          )}
                          <span>
                            {paymentAccount.verified
                              ? "Conta confirmada diretamente no Mercado Pago"
                              : "Confira novamente a conta autorizada"}
                          </span>
                        </div>
                        <dl className="grid gap-3 text-sm sm:grid-cols-2">
                          {paymentAccount.account_holder && (
                            <div>
                              <dt className="text-xs font-medium uppercase tracking-wide text-gray-400">
                                Titular
                              </dt>
                              <dd className="font-medium text-gray-800">
                                {paymentAccount.account_holder}
                              </dd>
                            </div>
                          )}
                          {paymentAccount.identification_type &&
                            paymentAccount.identification_last_four && (
                              <div>
                                <dt className="text-xs font-medium uppercase tracking-wide text-gray-400">
                                  Documento
                                </dt>
                                <dd className="font-medium text-gray-800">
                                  {paymentAccount.identification_type.toUpperCase()} final{" "}
                                  {paymentAccount.identification_last_four}
                                </dd>
                              </div>
                            )}
                          {paymentAccount.email_masked && (
                            <div>
                              <dt className="text-xs font-medium uppercase tracking-wide text-gray-400">
                                E-mail da conta
                              </dt>
                              <dd className="font-medium text-gray-800">
                                {paymentAccount.email_masked}
                              </dd>
                            </div>
                          )}
                          {(paymentAccount.mercado_pago_user_id ||
                            paymentConfig.mercado_pago_user_id) && (
                            <div>
                              <dt className="text-xs font-medium uppercase tracking-wide text-gray-400">
                                ID Mercado Pago
                              </dt>
                              <dd className="font-medium text-gray-800">
                                {paymentAccount.mercado_pago_user_id ||
                                  paymentConfig.mercado_pago_user_id}
                              </dd>
                            </div>
                          )}
                        </dl>
                      </div>
                    ) : (
                      <div className="flex flex-wrap items-center justify-between gap-3">
                        <div>
                          <p className="text-sm text-amber-700">{paymentAccountError}</p>
                          {paymentConfig.mercado_pago_user_id && (
                            <p className="mt-1 text-xs text-gray-500">
                              ID Mercado Pago: {paymentConfig.mercado_pago_user_id}
                            </p>
                          )}
                        </div>
                        <button
                          type="button"
                          onClick={recarregarPaymentAccount}
                          className="rounded-md border border-gray-200 bg-white px-3 py-1.5 text-xs font-semibold text-gray-700 hover:bg-gray-50"
                        >
                          Tentar novamente
                        </button>
                      </div>
                    )}
                  </div>
                )}
                {!paymentConfig.oauth_connected && !paymentConfig.oauth_available && (
                  <p className="text-xs text-amber-700 bg-amber-50 border border-amber-100 rounded-md px-3 py-2">
                    A conexão está temporariamente indisponível. Fale com o suporte CorePet.
                  </p>
                )}
              </div>
            </>
          )}
        </div>

        {hasPaymentCredential && (
          <button
            type="submit"
            disabled={savingPayment || paymentLoading}
            className="w-full bg-emerald-600 hover:bg-emerald-700 disabled:opacity-50 text-white font-semibold py-2.5 rounded-xl transition-colors"
          >
            {savingPayment ? "Salvando..." : "Salvar preferência de pagamento"}
          </button>
        )}
      </form>

      {/* Avisos de Estoque Pendentes */}
      <div className="bg-white rounded-xl border border-gray-200 p-6 shadow-sm space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-base font-semibold text-gray-800">🔔 Avisos de Estoque Pendentes</h2>
          {avisos.length > 0 && (
            <span className="bg-red-100 text-red-600 text-xs font-bold px-2 py-0.5 rounded-full">
              {avisos.length}
            </span>
          )}
        </div>
        <p className="text-sm text-gray-500">
          Clientes que pediram para ser avisados quando um produto voltar ao estoque. Os emails são
          enviados automaticamente quando você aumenta o estoque do produto.
        </p>

        {loadingAvisos ? (
          <div className="animate-pulse h-10 bg-gray-100 rounded" />
        ) : Object.keys(avisosPorProduto).length === 0 ? (
          <p className="text-sm text-gray-400 italic">Nenhum aviso pendente no momento.</p>
        ) : (
          <div className="space-y-3">
            {Object.values(avisosPorProduto).map((grupo) => (
              <div
                key={grupo.product_id}
                className="border border-gray-100 rounded-lg p-3 space-y-1"
              >
                <p className="font-medium text-sm text-gray-800">{grupo.product_name}</p>
                <p className="text-xs text-gray-500">
                  {grupo.emails.length} cliente{grupo.emails.length !== 1 ? "s" : ""} aguardando. Os
                  endereços ficam protegidos e não são exibidos nesta tela.
                </p>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
