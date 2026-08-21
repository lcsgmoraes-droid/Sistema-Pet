import { useEffect, useState } from "react";
import { trackBeginCheckout, trackCheckoutSubmitted } from "../../services/analytics";
import ecommerceApi from "../../services/ecommerceApi";
import {
  STORAGE_ADDRESS_KEY,
  buildAddressText,
  buildCustomerAddressFields,
  buildIdempotencyKey,
  extractApiErrorMessage,
  fetchAddressByCep,
  getStoredAddressFields,
} from "./ecommerceMvpUtils";

export default function useEcommerceCheckout({
  authHeaders,
  cart,
  clearCart,
  customer,
  customerToken,
  isProfileComplete,
  recordOrderId,
  setView,
  tenantContext,
  onError,
  onRequireAuthForCheckout,
  onSuccess,
}) {
  const [checkoutLoading, setCheckoutLoading] = useState(false);
  const [cupom, setCupom] = useState("");
  const [cupomResult, setCupomResult] = useState(null);
  const [cidadeDestino, setCidadeDestino] = useState("");
  const [deliveryMode, setDeliveryMode] = useState("entrega");
  const [tipoRetirada, setTipoRetirada] = useState("proprio");
  const [isDrive, setIsDrive] = useState(false);
  const [addressFields, setAddressFields] = useState(() => getStoredAddressFields());
  const [checkoutResumo, setCheckoutResumo] = useState(null);
  const [checkoutResult, setCheckoutResult] = useState(null);
  const [pagamentoTipo, setPagamentoTipo] = useState("");
  const [pagamentoBandeira, setPagamentoBandeira] = useState("Visa");
  const [pagamentoParcelas, setPagamentoParcelas] = useState(1);

  useEffect(() => {
    if (tenantContext?.cidade && !cidadeDestino) {
      setCidadeDestino(tenantContext.cidade);
    }
  }, [tenantContext?.cidade, cidadeDestino]);

  useEffect(() => {
    if (
      tenantContext?.ecommerce_entrega_ativa === false &&
      tenantContext?.ecommerce_retirada_ativa
    ) {
      setDeliveryMode("retirada");
    } else if (
      tenantContext?.ecommerce_retirada_ativa === false &&
      tenantContext?.ecommerce_entrega_ativa
    ) {
      setDeliveryMode("entrega");
    }
  }, [tenantContext?.ecommerce_entrega_ativa, tenantContext?.ecommerce_retirada_ativa]);

  useEffect(() => {
    if (!customer) return;
    setAddressFields(buildCustomerAddressFields(customer));
  }, [customer]);

  useEffect(() => {
    setCheckoutResumo(null);
    if (!customerToken || !cart?.itens?.length) return undefined;

    const cidadeFinal = String(
      deliveryMode === "retirada"
        ? tenantContext?.cidade || cidadeDestino
        : addressFields.cidade || cidadeDestino,
    ).trim();
    const enderecoFormatado =
      deliveryMode === "retirada" ? "RETIRADA NA LOJA" : buildAddressText(addressFields);
    const enderecoCompleto =
      deliveryMode === "retirada" ||
      Boolean(
        addressFields.endereco?.trim() &&
        addressFields.numero?.trim() &&
        addressFields.cidade?.trim() &&
        addressFields.estado?.trim(),
      );
    if (cidadeFinal.length < 2 || !enderecoCompleto) return undefined;

    let active = true;
    const timer = window.setTimeout(async () => {
      try {
        const response = await ecommerceApi.get("/api/checkout/resumo", {
          headers: authHeaders,
          params: {
            cidade_destino: cidadeFinal,
            endereco_entrega: enderecoFormatado,
            cupom: cupomResult?.codigo || undefined,
            tipo_retirada: deliveryMode === "retirada" ? tipoRetirada : undefined,
          },
        });
        if (active) {
          setCheckoutResumo(response.data);
          onError("");
        }
      } catch (err) {
        if (active) {
          setCheckoutResumo(null);
          onError(extractApiErrorMessage(err, "Não foi possível calcular o frete"));
        }
      }
    }, 650);

    return () => {
      active = false;
      window.clearTimeout(timer);
    };
  }, [
    addressFields.bairro,
    addressFields.cep,
    addressFields.cidade,
    addressFields.complemento,
    addressFields.endereco,
    addressFields.estado,
    addressFields.numero,
    authHeaders,
    cart?.itens?.length,
    cart?.total,
    cidadeDestino,
    cupomResult?.codigo,
    customerToken,
    deliveryMode,
    onError,
    tenantContext?.cidade,
    tipoRetirada,
  ]);

  function resetCheckoutStatus() {
    setCheckoutResumo(null);
    setCheckoutResult(null);
  }

  function requireAuthForCheckout() {
    if (typeof onRequireAuthForCheckout === "function") {
      onRequireAuthForCheckout();
      return;
    }
    setView("conta");
  }

  async function handleCheckoutCepBlur() {
    const data = await fetchAddressByCep(addressFields.cep);
    if (!data) return;
    setAddressFields((prev) => ({
      ...prev,
      cep: data.cep || prev.cep,
      endereco: data.endereco || prev.endereco,
      bairro: data.bairro || prev.bairro,
      cidade: data.cidade || prev.cidade,
      estado: data.estado || prev.estado,
    }));
  }

  async function applyCupom(e) {
    e.preventDefault();
    if (!customerToken) {
      onError("Fa\u00e7a login para aplicar cupom.");
      setView("conta");
      return;
    }
    if (!cupom.trim()) return;
    onError("");
    try {
      const response = await ecommerceApi.post(
        "/api/carrinho/aplicar-cupom",
        { codigo: cupom.trim() },
        { headers: authHeaders },
      );
      setCupomResult(response.data);
      onSuccess("Cupom validado.");
    } catch (err) {
      setCupomResult(null);
      onError(extractApiErrorMessage(err, "Cupom inv\u00e1lido"));
    }
  }

  async function calcularResumoCheckout(e) {
    e.preventDefault();
    if (!customerToken) {
      onError("Fa\u00e7a login para continuar no checkout.");
      requireAuthForCheckout();
      return;
    }
    if (!cart?.itens?.length) {
      onError("Adicione itens no carrinho antes de calcular o checkout.");
      return;
    }

    const cidadeFinal = String(
      deliveryMode === "retirada"
        ? tenantContext?.cidade || cidadeDestino
        : addressFields.cidade || cidadeDestino,
    ).trim();
    if (!cidadeFinal || cidadeFinal.length < 2) {
      onError("Cidade da loja n\u00e3o configurada para checkout.");
      return;
    }
    const enderecoFormatado =
      deliveryMode === "retirada" ? "RETIRADA NA LOJA" : buildAddressText(addressFields);
    if (
      deliveryMode === "entrega" &&
      (!addressFields.endereco?.trim() ||
        !addressFields.numero?.trim() ||
        !addressFields.cidade?.trim() ||
        !addressFields.estado?.trim())
    ) {
      onError("Complete rua, número, cidade e UF para calcular o frete.");
      return;
    }

    onError("");
    setCheckoutResumo(null);
    try {
      const response = await ecommerceApi.get("/api/checkout/resumo", {
        headers: authHeaders,
        params: {
          cidade_destino: cidadeFinal,
          endereco_entrega: enderecoFormatado,
          cupom: cupomResult?.codigo || undefined,
          tipo_retirada: deliveryMode === "retirada" ? tipoRetirada : undefined,
        },
      });
      setCheckoutResumo(response.data);
      onSuccess("Resumo de checkout calculado.");
    } catch (err) {
      onError(extractApiErrorMessage(err, "Erro ao calcular resumo do checkout"));
    }
  }

  async function finalizarCheckout() {
    if (!customerToken) {
      onError("Fa\u00e7a login para finalizar o pedido.");
      requireAuthForCheckout();
      return;
    }
    if (!isProfileComplete) {
      onError("Complete seu cadastro antes de finalizar o pedido.");
      setView("conta");
      return;
    }
    const cidadeFinal = String(
      deliveryMode === "retirada"
        ? tenantContext?.cidade || cidadeDestino
        : addressFields.cidade || cidadeDestino,
    ).trim();
    if (!cidadeFinal || cidadeFinal.length < 2) {
      onError("Cidade da loja n\u00e3o configurada para checkout.");
      return;
    }

    const enderecoFormatado =
      deliveryMode === "retirada" ? "RETIRADA NA LOJA" : buildAddressText(addressFields);

    if (deliveryMode === "entrega" && !enderecoFormatado) {
      onError("Informe o endere\u00e7o de entrega.");
      return;
    }
    if (!pagamentoTipo) {
      onError("Escolha PIX, debito ou credito para continuar para o pagamento.");
      return;
    }
    if (!checkoutResumo) {
      onError("Aguarde o cálculo atualizado do frete antes de continuar.");
      return;
    }

    setCheckoutLoading(true);
    onError("");
    onSuccess("");
    setCheckoutResult(null);

    try {
      const response = await ecommerceApi.post(
        "/api/checkout/finalizar",
        {
          cidade_destino: cidadeFinal,
          endereco_entrega: enderecoFormatado || null,
          cupom: cupomResult?.codigo || null,
          tipo_retirada: deliveryMode === "retirada" ? tipoRetirada : null,
          is_drive: deliveryMode === "retirada" && tipoRetirada === "proprio" ? isDrive : false,
          forma_pagamento_nome: (() => {
            if (pagamentoTipo === "pix") return "PIX";
            if (pagamentoTipo === "debito") return `D\u00e9bito ${pagamentoBandeira}`;
            if (pagamentoTipo === "credito")
              return `Cr\u00e9dito ${pagamentoBandeira} ${pagamentoParcelas}x`;
            return null;
          })(),
        },
        {
          headers: {
            ...authHeaders,
            "Idempotency-Key": buildIdempotencyKey(),
          },
        },
      );

      const result = response.data;
      setCheckoutResult(result);
      trackCheckoutSubmitted(result, cart);
      clearCart();
      setCheckoutResumo(null);
      setCupomResult(null);
      setCupom("");
      if (deliveryMode === "entrega") {
        localStorage.setItem(STORAGE_ADDRESS_KEY, JSON.stringify(addressFields));
      }

      if (result?.payment_url) {
        onSuccess("Redirecionando para pagamento seguro...");
        window.location.assign(result.payment_url);
        return;
      }

      if (result?.pedido_id) {
        await recordOrderId(result.pedido_id);
      }

      onSuccess("Pagamento enviado para analise. O pedido sera liberado apos aprovacao.");
      setView("pedidos");
    } catch (err) {
      onError(extractApiErrorMessage(err, "Erro ao finalizar checkout"));
    } finally {
      setCheckoutLoading(false);
    }
  }

  function handleCheckoutFromLoja() {
    if (!cart?.itens?.length) {
      onError("Adicione itens no carrinho antes de finalizar.");
      return;
    }
    if (!customerToken) {
      onError("Fa\u00e7a login para finalizar o pedido.");
      requireAuthForCheckout();
      return;
    }
    if (!isProfileComplete) {
      onError(
        "Complete seu cadastro (nome completo, telefone, CPF e endere\u00e7o) antes de finalizar.",
      );
      setView("conta");
      return;
    }
    setView("checkout");
    trackBeginCheckout(cart);
  }

  return {
    addressFields,
    checkoutLoading,
    checkoutResumo,
    checkoutResult,
    cidadeDestino,
    cupom,
    cupomResult,
    deliveryMode,
    isDrive,
    pagamentoBandeira,
    pagamentoParcelas,
    pagamentoTipo,
    tipoRetirada,
    applyCupom,
    calcularResumoCheckout,
    finalizarCheckout,
    handleCheckoutCepBlur,
    handleCheckoutFromLoja,
    resetCheckoutStatus,
    setAddressFields,
    setCidadeDestino,
    setCupom,
    setDeliveryMode,
    setIsDrive,
    setPagamentoBandeira,
    setPagamentoParcelas,
    setPagamentoTipo,
    setTipoRetirada,
  };
}
