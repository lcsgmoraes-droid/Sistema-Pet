import { useFocusEffect, useNavigation } from "@react-navigation/native";
import React, { useCallback, useEffect, useState } from "react";
import { Alert, Linking } from "react-native";

import {
  finalizarCheckoutAppLoja,
  resumoCheckout,
} from "../../services/shop.service";
import type { CheckoutResumo } from "../../services/shop.service";
import { useAuthStore } from "../../store/auth.store";
import { useCartStore } from "../../store/cart.store";
import { useTenantStore } from "../../store/tenant.store";
import { formatarMoeda } from "../../utils/format";
import { CartAddressModal } from "./cart/CartAddressModal";
import { CartContent } from "./cart/CartContent";
import {
  buildPagamentoLabel,
  buildRecebimentoLabel,
  formatarCep,
  formatarEnderecoEntrega,
  formatarEnderecoSalvo,
  ModoRecebimento,
  montarEnderecoInicial,
  PagamentoTipo,
  TipoRetirada,
} from "./cart/CartUtils";

export default function CartScreen() {
  const navigation = useNavigation<any>();
  const { itens, subtotal, carregar, atualizar, remover, limpar } =
    useCartStore();
  const { user } = useAuthStore();
  const tenant = useTenantStore((state) => state.tenant);
  const [finalizando, setFinalizando] = useState(false);
  const [pagamentoTipo, setPagamentoTipo] = useState<PagamentoTipo>("");
  const [pagamentoBandeira, setPagamentoBandeira] = useState("Visa");
  const [pagamentoParcelas, setPagamentoParcelas] = useState(1);
  const [modo, setModo] = useState<ModoRecebimento>("retirada");
  const [tipoRetirada, setTipoRetirada] = useState<TipoRetirada>("proprio");
  const [isDrive, setIsDrive] = useState(false);

  const enderecoInicial = montarEnderecoInicial(user);
  const enderecoSalvo = formatarEnderecoSalvo(enderecoInicial);
  const [usarEnderecoSalvo, setUsarEnderecoSalvo] = useState(true);
  const [modalEnderecoAberto, setModalEnderecoAberto] = useState(false);
  const [cep, setCep] = useState(enderecoInicial.cep);
  const [rua, setRua] = useState(enderecoInicial.rua);
  const [numero, setNumero] = useState(enderecoInicial.numero);
  const [complemento, setComplemento] = useState(enderecoInicial.complemento);
  const [bairro, setBairro] = useState(enderecoInicial.bairro);
  const [cidade, setCidade] = useState(enderecoInicial.cidade);
  const [estado, setEstado] = useState(enderecoInicial.estado);
  const [buscandoCep, setBuscandoCep] = useState(false);
  const [checkoutResumo, setCheckoutResumo] = useState<CheckoutResumo | null>(
    null,
  );
  const [calculandoFrete, setCalculandoFrete] = useState(false);
  const [erroFrete, setErroFrete] = useState("");

  useFocusEffect(
    useCallback(() => {
      if (!user?.id || !tenant?.id) return;
      void carregar({ userId: user.id, tenantId: tenant.id });
    }, [carregar, tenant?.id, user?.id]),
  );

  useEffect(() => {
    if (
      tenant?.ecommerce_retirada_ativa === false &&
      tenant.ecommerce_entrega_ativa !== false
    ) {
      setModo("entrega");
    } else if (
      tenant?.ecommerce_entrega_ativa === false &&
      tenant.ecommerce_retirada_ativa !== false
    ) {
      setModo("retirada");
    }
  }, [tenant?.ecommerce_entrega_ativa, tenant?.ecommerce_retirada_ativa]);

  useEffect(() => {
    setCheckoutResumo(null);
    setErroFrete("");
    setCalculandoFrete(false);
    if (!itens.length || !tenant) return undefined;

    const endereco = modo === "entrega" ? getEnderecoEntrega() : undefined;
    const cidadeCheckout =
      modo === "entrega"
        ? cidade.trim()
        : String(tenant.cidade || user?.cidade || "").trim();
    const enderecoCompleto =
      modo === "retirada" ||
      Boolean(rua.trim() && numero.trim() && cidade.trim() && estado.trim());
    if (!cidadeCheckout || !enderecoCompleto) return undefined;

    let active = true;
    setCalculandoFrete(true);
    const timer = setTimeout(async () => {
      try {
        const resumo = await resumoCheckout({
          cidade: cidadeCheckout,
          modo,
          endereco,
          tipoRetirada,
        });
        if (active) setCheckoutResumo(resumo);
      } catch (error: any) {
        if (active) {
          setErroFrete(
            error?.response?.data?.detail ||
              "Não foi possível calcular o frete para este endereço.",
          );
        }
      } finally {
        if (active) setCalculandoFrete(false);
      }
    }, 650);

    return () => {
      active = false;
      clearTimeout(timer);
    };
  }, [
    bairro,
    cep,
    cidade,
    complemento,
    estado,
    itens.length,
    modo,
    numero,
    rua,
    subtotal,
    tenant,
    tipoRetirada,
    user?.cidade,
  ]);

  async function buscarCep(value: string) {
    const { numeros, cep: cepFormatado } = formatarCep(value);
    setCep(cepFormatado);

    if (numeros.length === 8) {
      setBuscandoCep(true);
      try {
        const resp = await fetch(`https://viacep.com.br/ws/${numeros}/json/`);
        const data = await resp.json();
        if (!data.erro) {
          setRua(data.logradouro ?? "");
          setBairro(data.bairro ?? "");
          setCidade(data.localidade ?? "");
          setEstado(data.uf ?? "");
        }
      } catch {
        // Mantem preenchimento manual quando o ViaCEP nao responde.
      } finally {
        setBuscandoCep(false);
      }
    }
  }

  function getEnderecoEntrega() {
    return formatarEnderecoEntrega({
      cep,
      rua,
      numero,
      complemento,
      bairro,
      cidade,
      estado,
    });
  }

  function usarEnderecoInformado() {
    if (!rua.trim() || !cidade.trim()) {
      Alert.alert(
        "Campos obrigatórios",
        "Preencha pelo menos a rua e a cidade.",
      );
      return;
    }
    setUsarEnderecoSalvo(false);
    setModalEnderecoAberto(false);
  }

  async function handleDecreaseItem(item: any) {
    try {
      if (item.quantidade <= 1) {
        await remover(item.produto_id);
      } else {
        await atualizar(item.produto_id, item.quantidade - 1);
      }
    } catch {
      Alert.alert("Erro", "Não foi possível atualizar o item.");
    }
  }

  async function handleIncreaseItem(item: any) {
    try {
      await atualizar(item.produto_id, item.quantidade + 1);
    } catch {
      Alert.alert("Erro", "Não foi possível atualizar o item.");
    }
  }

  function handleClearCart() {
    Alert.alert("Limpar carrinho", "Deseja remover todos os produtos?", [
      { text: "Cancelar", style: "cancel" },
      {
        text: "Limpar",
        style: "destructive",
        onPress: async () => {
          try {
            await limpar();
          } catch {
            Alert.alert("Erro", "Não foi possível limpar o carrinho.");
          }
        },
      },
    ]);
  }

  async function handleFinalizar() {
    if (itens.length === 0) {
      Alert.alert("Carrinho vazio", "Adicione produtos antes de finalizar.");
      return;
    }

    if (modo === "entrega") {
      if (!rua.trim() || !numero.trim() || !cidade.trim() || !estado.trim()) {
        Alert.alert(
          "Endereço incompleto",
          "Preencha rua, número, cidade e estado para entrega.",
        );
        return;
      }
      if (usarEnderecoSalvo && !enderecoSalvo) {
        Alert.alert(
          "Sem endereço",
          "Nenhum endereço salvo no perfil. Preencha o endereço de entrega.",
        );
        setUsarEnderecoSalvo(false);
        return;
      }
    }

    if (!checkoutResumo) {
      Alert.alert(
        "Frete ainda não calculado",
        erroFrete || "Complete o endereço e aguarde o cálculo do frete.",
      );
      return;
    }

    if (!pagamentoTipo) {
      Alert.alert(
        "Forma de pagamento",
        "Escolha PIX, débito ou crédito para continuar.",
      );
      return;
    }

    const enderecoFormatado =
      modo === "entrega" ? getEnderecoEntrega() : undefined;
    const modoLabel = buildRecebimentoLabel({
      modo,
      tipoRetirada,
      isDrive,
      enderecoFormatado,
    });
    const pagamentoLabel = buildPagamentoLabel(
      pagamentoTipo,
      pagamentoBandeira,
      pagamentoParcelas,
    );
    const pagLabel = pagamentoTipo ? `\n💳 Pagamento: ${pagamentoLabel}` : "";
    const enderecoLoja = tenant
      ? [
          [tenant.endereco, tenant.numero].filter(Boolean).join(", "),
          tenant.bairro,
          [tenant.cidade, tenant.uf].filter(Boolean).join("/"),
        ]
          .filter(Boolean)
          .join(" - ")
      : "";
    const lojaLabel = tenant
      ? `Loja: ${tenant.nome}${enderecoLoja ? `\n${enderecoLoja}` : ""}`
      : "Loja selecionada no aplicativo";
    const freteLabel = checkoutResumo.frete.frete_gratis_aplicado
      ? "Grátis"
      : formatarMoeda(checkoutResumo.frete.valor_frete || 0);
    const distanciaLabel =
      checkoutResumo.frete.distancia_km != null
        ? ` (${checkoutResumo.frete.distancia_km.toFixed(1)} km)`
        : "";

    Alert.alert(
      "Confirmar compra",
      `${lojaLabel}\n\nProdutos: ${formatarMoeda(checkoutResumo.subtotal)}\nFrete${distanciaLabel}: ${freteLabel}\nTotal: ${formatarMoeda(checkoutResumo.total)}\n\n${modoLabel}${pagLabel}\n\nConfirme que esta comprando na loja correta. O pedido sera liberado apos aprovacao do pagamento online.`,
      [
        { text: "Cancelar", style: "cancel" },
        {
          text: "Continuar",
          onPress: async () => {
            setFinalizando(true);
            try {
              const pedido = await finalizarCheckoutAppLoja({
                cidade:
                  modo === "entrega"
                    ? cidade.trim()
                    : String(tenant?.cidade || user?.cidade || "loja"),
                modo,
                tipoRetirada,
                isDrive:
                  isDrive && modo === "retirada" && tipoRetirada === "proprio",
                endereco: enderecoFormatado,
                formaPagamentoNome: pagamentoLabel || undefined,
              });

              await limpar();
              if (pedido.payment_url) {
                void Linking.openURL(pedido.payment_url).catch(() => {
                  Alert.alert(
                    "Pedido criado",
                    "Nao consegui abrir o pagamento automaticamente. Use o botao Abrir pagamento na proxima tela.",
                  );
                });
              }
              navigation.navigate("CheckoutSucesso", { pedido });
            } catch (err: any) {
              Alert.alert(
                "Erro ao finalizar",
                err?.response?.data?.detail || "Tente novamente.",
              );
            } finally {
              setFinalizando(false);
            }
          },
        },
      ],
    );
  }

  return (
    <>
      <CartContent
        itens={itens}
        subtotal={subtotal}
        finalizando={finalizando}
        checkoutResumo={checkoutResumo}
        calculandoFrete={calculandoFrete}
        erroFrete={erroFrete}
        entregaAtiva={tenant?.ecommerce_entrega_ativa !== false}
        retiradaAtiva={tenant?.ecommerce_retirada_ativa !== false}
        modo={modo}
        tipoRetirada={tipoRetirada}
        isDrive={isDrive}
        enderecoSalvo={enderecoSalvo}
        usarEnderecoSalvo={usarEnderecoSalvo}
        rua={rua}
        pagamentoTipo={pagamentoTipo}
        pagamentoBandeira={pagamentoBandeira}
        pagamentoParcelas={pagamentoParcelas}
        onNavigateScanner={() => navigation.navigate("BarcodeScanner")}
        onNavigateCatalog={() => navigation.navigate("Catalogo")}
        onClearCart={handleClearCart}
        onFinalize={handleFinalizar}
        onDecreaseItem={handleDecreaseItem}
        onIncreaseItem={handleIncreaseItem}
        onModoChange={setModo}
        onTipoRetiradaChange={setTipoRetirada}
        onDriveToggle={() => setIsDrive((prev) => !prev)}
        onUsarEnderecoSalvoChange={setUsarEnderecoSalvo}
        onOpenAddressModal={() => setModalEnderecoAberto(true)}
        onPagamentoTipoChange={setPagamentoTipo}
        onPagamentoBandeiraChange={setPagamentoBandeira}
        onPagamentoParcelasChange={setPagamentoParcelas}
        getEnderecoEntrega={getEnderecoEntrega}
      />

      <CartAddressModal
        visible={modalEnderecoAberto}
        cep={cep}
        rua={rua}
        numero={numero}
        complemento={complemento}
        bairro={bairro}
        cidade={cidade}
        estado={estado}
        buscandoCep={buscandoCep}
        onClose={() => setModalEnderecoAberto(false)}
        onCepChange={buscarCep}
        onRuaChange={setRua}
        onNumeroChange={setNumero}
        onComplementoChange={setComplemento}
        onBairroChange={setBairro}
        onCidadeChange={setCidade}
        onEstadoChange={setEstado}
        onUseAddress={usarEnderecoInformado}
      />
    </>
  );
}
