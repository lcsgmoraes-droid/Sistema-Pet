import { Ionicons } from "@expo/vector-icons";
import React from "react";
import {
  ActivityIndicator,
  FlatList,
  KeyboardAvoidingView,
  Platform,
  Text,
  TouchableOpacity,
  View,
} from "react-native";

import { CORES } from "../../../theme";
import { formatarMoeda } from "../../../utils/format";
import { CartItemCard } from "./CartItemCard";
import { cartStyles as styles } from "./CartStyles";
import { ModoRecebimento, PagamentoTipo, TipoRetirada } from "./CartUtils";

type CartContentProps = {
  itens: any[];
  subtotal: number;
  finalizando: boolean;
  modo: ModoRecebimento;
  tipoRetirada: TipoRetirada;
  isDrive: boolean;
  enderecoSalvo: string | null;
  usarEnderecoSalvo: boolean;
  rua: string;
  pagamentoTipo: PagamentoTipo;
  pagamentoBandeira: string;
  pagamentoParcelas: number;
  onNavigateScanner: () => void;
  onNavigateCatalog: () => void;
  onClearCart: () => void;
  onFinalize: () => void;
  onDecreaseItem: (item: any) => void;
  onIncreaseItem: (item: any) => void;
  onModoChange: (value: ModoRecebimento) => void;
  onTipoRetiradaChange: (value: TipoRetirada) => void;
  onDriveToggle: () => void;
  onUsarEnderecoSalvoChange: (value: boolean) => void;
  onOpenAddressModal: () => void;
  onPagamentoTipoChange: (value: PagamentoTipo) => void;
  onPagamentoBandeiraChange: (value: string) => void;
  onPagamentoParcelasChange: (value: number) => void;
  getEnderecoEntrega: () => string;
};

export function CartContent({
  itens,
  subtotal,
  finalizando,
  modo,
  tipoRetirada,
  isDrive,
  enderecoSalvo,
  usarEnderecoSalvo,
  rua,
  pagamentoTipo,
  pagamentoBandeira,
  pagamentoParcelas,
  onNavigateScanner,
  onNavigateCatalog,
  onClearCart,
  onFinalize,
  onDecreaseItem,
  onIncreaseItem,
  onModoChange,
  onTipoRetiradaChange,
  onDriveToggle,
  onUsarEnderecoSalvoChange,
  onOpenAddressModal,
  onPagamentoTipoChange,
  onPagamentoBandeiraChange,
  onPagamentoParcelasChange,
  getEnderecoEntrega,
}: CartContentProps) {
  if (itens.length === 0) {
    return (
      <View style={styles.vazio}>
        <Text style={styles.vazioEmoji}>🛒</Text>
        <Text style={styles.vazioTitulo}>Carrinho vazio</Text>
        <Text style={styles.vazioTexto}>
          Adicione produtos pelo catálogo ou escanear o código de barras.
        </Text>
        <TouchableOpacity
          style={styles.botaoScanner}
          onPress={onNavigateScanner}
        >
          <Ionicons name="barcode-outline" size={20} color="#fff" />
          <Text style={styles.botaoScannerTexto}>Escanear produto</Text>
        </TouchableOpacity>
        <TouchableOpacity
          style={styles.botaoCatalogo}
          onPress={onNavigateCatalog}
        >
          <Text style={styles.botaoCatalogoTexto}>Ver catálogo</Text>
        </TouchableOpacity>
      </View>
    );
  }

  return (
    <KeyboardAvoidingView
      style={styles.container}
      behavior={Platform.OS === "ios" ? "padding" : "height"}
    >
      <FlatList
        style={{ flex: 1 }}
        data={itens}
        keyExtractor={(item) => String(item.produto_id)}
        renderItem={({ item }) => (
          <CartItemCard
            item={item}
            onDecrease={onDecreaseItem}
            onIncrease={onIncreaseItem}
          />
        )}
        contentContainerStyle={styles.lista}
        keyboardShouldPersistTaps="handled"
        ListHeaderComponent={
          <TouchableOpacity style={styles.btnLimpar} onPress={onClearCart}>
            <Text style={styles.btnLimparTexto}>Limpar carrinho</Text>
          </TouchableOpacity>
        }
        ListFooterComponent={
          <View style={styles.opcaoEntrega}>
            <Text style={styles.secaoTitulo}>Forma de recebimento</Text>
            <View style={styles.modoRow}>
              <TouchableOpacity
                style={[
                  styles.modoBotao,
                  modo === "retirada" && styles.modoBotaoAtivo,
                ]}
                onPress={() => onModoChange("retirada")}
              >
                <Ionicons
                  name="storefront-outline"
                  size={18}
                  color={modo === "retirada" ? "#fff" : CORES.texto}
                />
                <Text
                  style={[
                    styles.modoTexto,
                    modo === "retirada" && styles.modoTextoAtivo,
                  ]}
                >
                  Retirar na loja
                </Text>
              </TouchableOpacity>
              <TouchableOpacity
                style={[
                  styles.modoBotao,
                  modo === "entrega" && styles.modoBotaoAtivo,
                ]}
                onPress={() => onModoChange("entrega")}
              >
                <Ionicons
                  name="bicycle-outline"
                  size={18}
                  color={modo === "entrega" ? "#fff" : CORES.texto}
                />
                <Text
                  style={[
                    styles.modoTexto,
                    modo === "entrega" && styles.modoTextoAtivo,
                  ]}
                >
                  Entrega
                </Text>
              </TouchableOpacity>
            </View>

            {modo === "retirada" && (
              <View style={styles.subSecao}>
                <Text style={styles.subSecaoTitulo}>Quem vai retirar?</Text>
                <TouchableOpacity
                  style={[
                    styles.opcaoBotao,
                    tipoRetirada === "proprio" && styles.opcaoBotaoAtivo,
                  ]}
                  onPress={() => onTipoRetiradaChange("proprio")}
                >
                  <Text
                    style={[
                      styles.opcaoTexto,
                      tipoRetirada === "proprio" && styles.opcaoTextoAtivo,
                    ]}
                  >
                    🙋 Eu mesmo(a) vou retirar
                  </Text>
                </TouchableOpacity>
                <TouchableOpacity
                  style={[
                    styles.opcaoBotao,
                    tipoRetirada === "terceiro" && styles.opcaoBotaoAtivo,
                  ]}
                  onPress={() => onTipoRetiradaChange("terceiro")}
                >
                  <Text
                    style={[
                      styles.opcaoTexto,
                      tipoRetirada === "terceiro" && styles.opcaoTextoAtivo,
                    ]}
                  >
                    👥 Outra pessoa vai retirar por mim
                  </Text>
                </TouchableOpacity>
                {tipoRetirada === "terceiro" && (
                  <View style={styles.aviso}>
                    <Text style={styles.avisoTexto}>
                      🔑 Uma senha secreta será gerada após confirmar.
                      Compartilhe com a pessoa que irá retirar.
                    </Text>
                  </View>
                )}
                {tipoRetirada === "proprio" && (
                  <TouchableOpacity
                    style={[
                      styles.opcaoBotao,
                      isDrive && styles.opcaoBotaoAtivo,
                    ]}
                    onPress={onDriveToggle}
                  >
                    <Text
                      style={[
                        styles.opcaoTexto,
                        isDrive && styles.opcaoTextoAtivo,
                      ]}
                    >
                      🚗{" "}
                      {isDrive
                        ? "✅ Vou aguardar no carro (Drive-thru)"
                        : "Vou aguardar no carro (Drive-thru)"}
                    </Text>
                  </TouchableOpacity>
                )}
              </View>
            )}

            {modo === "entrega" && (
              <View style={styles.subSecao}>
                <Text style={styles.subSecaoTitulo}>Endereço de entrega</Text>
                {enderecoSalvo ? (
                  <>
                    <TouchableOpacity
                      style={[
                        styles.opcaoBotao,
                        usarEnderecoSalvo && styles.opcaoBotaoAtivo,
                      ]}
                      onPress={() => onUsarEnderecoSalvoChange(true)}
                    >
                      <Text
                        style={[
                          styles.opcaoTexto,
                          usarEnderecoSalvo && styles.opcaoTextoAtivo,
                        ]}
                      >
                        🏠 Entregar no meu endereço cadastrado
                      </Text>
                      {usarEnderecoSalvo && (
                        <Text style={styles.enderecoSalvoTexto}>
                          {enderecoSalvo}
                        </Text>
                      )}
                    </TouchableOpacity>

                    <TouchableOpacity
                      style={[
                        styles.opcaoBotao,
                        !usarEnderecoSalvo && styles.opcaoBotaoAtivo,
                      ]}
                      onPress={() => {
                        onUsarEnderecoSalvoChange(false);
                        onOpenAddressModal();
                      }}
                    >
                      <Text
                        style={[
                          styles.opcaoTexto,
                          !usarEnderecoSalvo && styles.opcaoTextoAtivo,
                        ]}
                      >
                        📍 Entregar em outro endereço
                      </Text>
                      {!usarEnderecoSalvo && rua ? (
                        <Text style={styles.enderecoSalvoTexto}>
                          {getEnderecoEntrega()}
                        </Text>
                      ) : null}
                    </TouchableOpacity>

                    {!usarEnderecoSalvo && (
                      <TouchableOpacity
                        style={styles.btnEditar}
                        onPress={onOpenAddressModal}
                      >
                        <Ionicons
                          name="pencil-outline"
                          size={14}
                          color={CORES.primario}
                        />
                        <Text style={styles.btnEditarTexto}>
                          Editar endereço
                        </Text>
                      </TouchableOpacity>
                    )}
                  </>
                ) : (
                  <TouchableOpacity
                    style={styles.opcaoBotao}
                    onPress={onOpenAddressModal}
                  >
                    <Ionicons
                      name="add-circle-outline"
                      size={18}
                      color={CORES.primario}
                    />
                    <Text
                      style={[styles.opcaoTexto, { color: CORES.primario }]}
                    >
                      {rua
                        ? getEnderecoEntrega()
                        : "Preencher endereço de entrega"}
                    </Text>
                  </TouchableOpacity>
                )}
              </View>
            )}

            <View style={styles.subSecao}>
              <Text style={styles.subSecaoTitulo}>💳 Forma de pagamento</Text>
              <Text style={styles.pagamentoAviso}>
                O carrinho ainda nao e pedido. O pedido so sera liberado apos
                aprovacao do pagamento online.
              </Text>
              <View style={styles.modoRow}>
                {(["pix", "debito", "credito"] as const).map((tipo) => (
                  <TouchableOpacity
                    key={tipo}
                    style={[
                      styles.pagBotao,
                      pagamentoTipo === tipo && styles.pagBotaoAtivo,
                    ]}
                    onPress={() => onPagamentoTipoChange(tipo)}
                  >
                    <Text style={styles.pagBotaoIcon}>
                      {tipo === "pix" ? "📱" : "💳"}
                    </Text>
                    <Text
                      style={[
                        styles.pagBotaoTexto,
                        pagamentoTipo === tipo && styles.pagBotaoTextoAtivo,
                      ]}
                    >
                      {tipo === "pix"
                        ? "PIX"
                        : tipo === "debito"
                          ? "Débito"
                          : "Crédito"}
                    </Text>
                  </TouchableOpacity>
                ))}
              </View>

              {(pagamentoTipo === "debito" || pagamentoTipo === "credito") && (
                <View style={{ marginTop: 8 }}>
                  <Text style={styles.pagLabel}>Bandeira</Text>
                  <View style={styles.modoRow}>
                    {["Visa", "Mastercard", "Elo", "Outra"].map((bandeira) => (
                      <TouchableOpacity
                        key={bandeira}
                        style={[
                          styles.bandeiraBotao,
                          pagamentoBandeira === bandeira &&
                            styles.bandeiraBotaoAtivo,
                        ]}
                        onPress={() => onPagamentoBandeiraChange(bandeira)}
                      >
                        <Text
                          style={[
                            styles.bandeiraTexto,
                            pagamentoBandeira === bandeira &&
                              styles.bandeiraTextoAtivo,
                          ]}
                        >
                          {bandeira}
                        </Text>
                      </TouchableOpacity>
                    ))}
                  </View>
                </View>
              )}

              {pagamentoTipo === "credito" && (
                <View style={{ marginTop: 8 }}>
                  <Text style={styles.pagLabel}>Parcelas</Text>
                  <View style={styles.modoRow}>
                    {[1, 2, 3].map((parcela) => (
                      <TouchableOpacity
                        key={parcela}
                        style={[
                          styles.bandeiraBotao,
                          pagamentoParcelas === parcela &&
                            styles.bandeiraBotaoAtivo,
                        ]}
                        onPress={() => onPagamentoParcelasChange(parcela)}
                      >
                        <Text
                          style={[
                            styles.bandeiraTexto,
                            pagamentoParcelas === parcela &&
                              styles.bandeiraTextoAtivo,
                          ]}
                        >
                          {parcela}x
                        </Text>
                      </TouchableOpacity>
                    ))}
                  </View>
                </View>
              )}
            </View>
          </View>
        }
      />

      <View style={styles.rodape}>
        <View style={styles.resumo}>
          <Text style={styles.resumoLabel}>Total</Text>
          <Text style={styles.resumoTotal}>{formatarMoeda(subtotal)}</Text>
        </View>

        <TouchableOpacity
          style={[styles.botaoFinalizar, finalizando && styles.botaoDesativado]}
          onPress={onFinalize}
          disabled={finalizando}
        >
          {finalizando ? (
            <ActivityIndicator color="#fff" />
          ) : (
            <>
              <Ionicons name="checkmark-circle" size={20} color="#fff" />
              <Text style={styles.botaoFinalizarTexto}>Ir para pagamento</Text>
            </>
          )}
        </TouchableOpacity>
      </View>
    </KeyboardAvoidingView>
  );
}
