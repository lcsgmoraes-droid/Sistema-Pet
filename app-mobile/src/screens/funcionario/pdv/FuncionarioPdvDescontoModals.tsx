import { Ionicons } from "@expo/vector-icons";
import React, { useEffect, useMemo, useState } from "react";
import {
  KeyboardAvoidingView,
  Modal,
  Platform,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  TouchableOpacity,
  View,
} from "react-native";

import { CORES, ESPACO, FONTE, RAIO } from "../../../theme";
import { formatarMoeda } from "../../../utils/format";
import { FuncionarioPdvProductImage as ProdutoImagem } from "./FuncionarioPdvProductImage";
import {
  aplicarDescontoTotalPdv,
  descontoItemPdv,
  formatarQuantidadeCampo,
  formatarValorCampo,
  parseNumero,
  subtotalBrutoItemPdv,
  subtotalLiquidoItemPdv,
  atualizarItemCarrinhoPdv,
  type ItemCarrinhoPdv,
  type TipoDescontoPdv,
} from "./FuncionarioPdvUtils";

type ItemFormPayload = {
  quantidade: number;
  precoUnitario: number;
  tipoDesconto: TipoDescontoPdv;
  valorDesconto: number;
};

function SeletorTipoDesconto({ tipo, onChange }: { tipo: TipoDescontoPdv; onChange: (tipo: TipoDescontoPdv) => void }) {
  return (
    <View style={styles.tipoLinha}>
      {(["valor", "percentual"] as const).map((opcao) => {
        const ativo = tipo === opcao;
        return (
          <TouchableOpacity
            key={opcao}
            style={[styles.tipoBotao, ativo && styles.tipoBotaoAtivo]}
            onPress={() => onChange(opcao)}
          >
            <Text style={[styles.tipoTexto, ativo && styles.tipoTextoAtivo]}>{opcao === "valor" ? "R$" : "%"}</Text>
          </TouchableOpacity>
        );
      })}
    </View>
  );
}

export function FuncionarioPdvItemModal({
  item,
  visible,
  onClose,
  onRemover,
  onSalvar,
}: {
  item: ItemCarrinhoPdv | null;
  visible: boolean;
  onClose: () => void;
  onRemover: () => void;
  onSalvar: (payload: ItemFormPayload) => void;
}) {
  const [preco, setPreco] = useState("");
  const [quantidade, setQuantidade] = useState("");
  const [tipoDesconto, setTipoDesconto] = useState<TipoDescontoPdv>("valor");
  const [valorDesconto, setValorDesconto] = useState("");

  useEffect(() => {
    if (!visible || !item) return;
    setPreco(formatarValorCampo(item.precoUnitario));
    setQuantidade(formatarQuantidadeCampo(item.quantidade));
    setTipoDesconto(item.tipoDesconto);
    setValorDesconto(
      formatarValorCampo(item.tipoDesconto === "percentual" ? item.descontoPercentual : item.descontoValor),
    );
  }, [item, visible]);

  const previa = useMemo(() => {
    if (!item) return null;
    return atualizarItemCarrinhoPdv(item, {
      precoUnitario: parseNumero(preco) ?? 0,
      quantidade: parseNumero(quantidade) ?? 0,
      tipoDesconto,
      valorDesconto: parseNumero(valorDesconto) ?? 0,
    });
  }, [item, preco, quantidade, tipoDesconto, valorDesconto]);
  const formularioValido = Boolean(previa && (parseNumero(preco) ?? 0) > 0 && (parseNumero(quantidade) ?? 0) > 0);

  function trocarTipo(novoTipo: TipoDescontoPdv) {
    if (previa) {
      setValorDesconto(
        formatarValorCampo(novoTipo === "percentual" ? previa.descontoPercentual : previa.descontoValor),
      );
    }
    setTipoDesconto(novoTipo);
  }

  function salvar() {
    if (!previa || !formularioValido) return;
    onSalvar({
      precoUnitario: previa.precoUnitario,
      quantidade: previa.quantidade,
      tipoDesconto,
      valorDesconto: parseNumero(valorDesconto) ?? 0,
    });
  }

  if (!item) return null;

  return (
    <Modal visible={visible} transparent animationType="slide" onRequestClose={onClose}>
      <KeyboardAvoidingView style={styles.overlay} behavior={Platform.OS === "ios" ? "padding" : undefined}>
        <View style={styles.card}>
          <View style={styles.header}>
            <Text style={styles.titulo}>Alterar item da venda</Text>
            <TouchableOpacity style={styles.fechar} onPress={onClose}>
              <Ionicons name="close" size={22} color={CORES.textoSecundario} />
            </TouchableOpacity>
          </View>
          <ScrollView keyboardShouldPersistTaps="handled" showsVerticalScrollIndicator={false}>
            <View style={styles.produtoBox}>
              <ProdutoImagem uri={item.produto.imagem_url} />
              <View style={{ flex: 1 }}>
                <Text style={styles.produtoNome}>{item.produto.nome}</Text>
                <Text style={styles.produtoMeta}>Codigo: {item.produto.codigo || "-"}</Text>
                <Text style={styles.ajuda}>Confira o preco e o desconto antes de salvar.</Text>
              </View>
            </View>

            <View style={styles.camposLinha}>
              <View style={styles.campoMetade}>
                <Text style={styles.label}>Preco</Text>
                <TextInput
                  value={preco}
                  onChangeText={setPreco}
                  keyboardType="decimal-pad"
                  selectTextOnFocus
                  style={styles.input}
                />
              </View>
              <View style={styles.campoMetade}>
                <Text style={styles.label}>Quantidade</Text>
                <TextInput
                  value={quantidade}
                  onChangeText={setQuantidade}
                  keyboardType="decimal-pad"
                  selectTextOnFocus
                  style={styles.input}
                />
              </View>
            </View>

            <Text style={styles.label}>Tipo de desconto</Text>
            <SeletorTipoDesconto tipo={tipoDesconto} onChange={trocarTipo} />
            <Text style={styles.label}>Valor do desconto</Text>
            <View style={styles.inputComPrefixo}>
              <Text style={styles.prefixo}>{tipoDesconto === "valor" ? "R$" : "%"}</Text>
              <TextInput
                value={valorDesconto}
                onChangeText={setValorDesconto}
                keyboardType="decimal-pad"
                selectTextOnFocus
                style={styles.inputPrefixado}
              />
            </View>

            {previa ? (
              <View style={styles.previaBox}>
                <View style={styles.previaLinha}>
                  <Text style={styles.previaLabel}>Total bruto</Text>
                  <Text style={styles.previaValor}>{formatarMoeda(subtotalBrutoItemPdv(previa))}</Text>
                </View>
                {descontoItemPdv(previa) > 0 ? (
                  <View style={styles.previaLinha}>
                    <Text style={styles.previaLabel}>Desconto</Text>
                    <Text style={styles.descontoValor}>- {formatarMoeda(descontoItemPdv(previa))}</Text>
                  </View>
                ) : null}
                <View style={[styles.previaLinha, styles.previaTotalLinha]}>
                  <Text style={styles.previaTotal}>Total liquido</Text>
                  <Text style={styles.liquidoValor}>{formatarMoeda(subtotalLiquidoItemPdv(previa))}</Text>
                </View>
              </View>
            ) : null}
            {!formularioValido ? <Text style={styles.erro}>Informe preco e quantidade maiores que zero.</Text> : null}
          </ScrollView>

          <View style={styles.acoes}>
            <TouchableOpacity style={styles.cancelar} onPress={onClose}>
              <Text style={styles.cancelarTexto}>Fechar</Text>
            </TouchableOpacity>
            <TouchableOpacity style={styles.remover} onPress={onRemover}>
              <Text style={styles.acaoTextoClaro}>Remover</Text>
            </TouchableOpacity>
            <TouchableOpacity
              style={[styles.salvar, !formularioValido && styles.desabilitado]}
              onPress={salvar}
              disabled={!formularioValido}
            >
              <Text style={styles.acaoTextoClaro}>Salvar</Text>
            </TouchableOpacity>
          </View>
        </View>
      </KeyboardAvoidingView>
    </Modal>
  );
}

export function FuncionarioPdvDescontoTotalModal({
  itens,
  descontoAtual,
  visible,
  onClose,
  onAplicar,
}: {
  itens: ItemCarrinhoPdv[];
  descontoAtual: number;
  visible: boolean;
  onClose: () => void;
  onAplicar: (tipo: TipoDescontoPdv, valor: number) => void;
}) {
  const [tipoDesconto, setTipoDesconto] = useState<TipoDescontoPdv>("valor");
  const [valorDesconto, setValorDesconto] = useState("");

  useEffect(() => {
    if (!visible) return;
    setTipoDesconto("valor");
    setValorDesconto(formatarValorCampo(descontoAtual));
  }, [descontoAtual, visible]);

  const totalBruto = useMemo(() => itens.reduce((soma, item) => soma + subtotalBrutoItemPdv(item), 0), [itens]);
  const itensComDesconto = useMemo(
    () => aplicarDescontoTotalPdv(itens, tipoDesconto, parseNumero(valorDesconto) ?? 0),
    [itens, tipoDesconto, valorDesconto],
  );
  const descontoCalculado = itensComDesconto.reduce((soma, item) => soma + descontoItemPdv(item), 0);

  return (
    <Modal visible={visible} transparent animationType="slide" onRequestClose={onClose}>
      <KeyboardAvoidingView style={styles.overlay} behavior={Platform.OS === "ios" ? "padding" : undefined}>
        <View style={styles.cardCompacto}>
          <View style={styles.header}>
            <Text style={styles.titulo}>Aplicar desconto no total</Text>
            <TouchableOpacity style={styles.fechar} onPress={onClose}>
              <Ionicons name="close" size={22} color={CORES.textoSecundario} />
            </TouchableOpacity>
          </View>

          <View style={styles.totalBrutoBox}>
            <Text style={styles.previaLabel}>Total bruto (sem desconto)</Text>
            <Text style={styles.totalBrutoValor}>{formatarMoeda(totalBruto)}</Text>
          </View>
          <Text style={styles.label}>Tipo de desconto</Text>
          <SeletorTipoDesconto tipo={tipoDesconto} onChange={setTipoDesconto} />
          <Text style={styles.label}>Valor</Text>
          <View style={styles.inputComPrefixo}>
            <Text style={styles.prefixo}>{tipoDesconto === "valor" ? "R$" : "%"}</Text>
            <TextInput
              value={valorDesconto}
              onChangeText={setValorDesconto}
              keyboardType="decimal-pad"
              selectTextOnFocus
              style={styles.inputPrefixado}
            />
          </View>
          <View style={styles.previaBox}>
            <View style={styles.previaLinha}>
              <Text style={styles.previaLabel}>Desconto</Text>
              <Text style={styles.descontoValor}>- {formatarMoeda(descontoCalculado)}</Text>
            </View>
            <View style={[styles.previaLinha, styles.previaTotalLinha]}>
              <Text style={styles.previaTotal}>Total liquido</Text>
              <Text style={styles.liquidoValor}>{formatarMoeda(Math.max(0, totalBruto - descontoCalculado))}</Text>
            </View>
          </View>

          <View style={styles.acoesTotal}>
            <TouchableOpacity style={styles.cancelar} onPress={onClose}>
              <Text style={styles.cancelarTexto}>Fechar</Text>
            </TouchableOpacity>
            {descontoAtual > 0 ? (
              <TouchableOpacity style={styles.removerDesconto} onPress={() => onAplicar("valor", 0)}>
                <Text style={styles.removerDescontoTexto}>Remover</Text>
              </TouchableOpacity>
            ) : null}
            <TouchableOpacity
              style={styles.salvar}
              onPress={() => onAplicar(tipoDesconto, parseNumero(valorDesconto) ?? 0)}
            >
              <Text style={styles.acaoTextoClaro}>Aplicar</Text>
            </TouchableOpacity>
          </View>
        </View>
      </KeyboardAvoidingView>
    </Modal>
  );
}

const styles = StyleSheet.create({
  overlay: {
    flex: 1,
    justifyContent: "flex-end",
    backgroundColor: "rgba(15,23,42,0.55)",
  },
  card: {
    maxHeight: "92%",
    backgroundColor: CORES.superficie,
    borderTopLeftRadius: RAIO.lg,
    borderTopRightRadius: RAIO.lg,
    padding: ESPACO.lg,
    paddingBottom: ESPACO.xxl,
  },
  cardCompacto: {
    backgroundColor: CORES.superficie,
    borderTopLeftRadius: RAIO.lg,
    borderTopRightRadius: RAIO.lg,
    padding: ESPACO.lg,
    paddingBottom: ESPACO.xxl,
  },
  header: {
    flexDirection: "row",
    alignItems: "center",
    marginBottom: ESPACO.md,
  },
  titulo: {
    flex: 1,
    color: CORES.texto,
    fontSize: FONTE.titulo,
    fontWeight: "900",
  },
  fechar: {
    width: 40,
    height: 40,
    borderRadius: RAIO.circulo,
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: CORES.fundo,
  },
  produtoBox: {
    flexDirection: "row",
    gap: ESPACO.md,
    alignItems: "center",
    borderRadius: RAIO.md,
    backgroundColor: CORES.fundo,
    padding: ESPACO.md,
    marginBottom: ESPACO.sm,
  },
  produtoNome: { color: CORES.texto, fontSize: FONTE.media, fontWeight: "900" },
  produtoMeta: {
    color: CORES.textoSecundario,
    fontSize: FONTE.pequena,
    marginTop: 2,
  },
  ajuda: {
    color: CORES.textoSecundario,
    fontSize: FONTE.pequena,
    marginTop: ESPACO.xs,
  },
  camposLinha: { flexDirection: "row", gap: ESPACO.sm },
  campoMetade: { flex: 1 },
  label: {
    color: CORES.texto,
    fontSize: FONTE.normal,
    fontWeight: "800",
    marginTop: ESPACO.sm,
  },
  input: {
    minHeight: 48,
    borderWidth: 1,
    borderColor: CORES.borda,
    borderRadius: RAIO.md,
    backgroundColor: "#fff",
    color: CORES.texto,
    paddingHorizontal: ESPACO.md,
    marginTop: ESPACO.xs,
  },
  tipoLinha: { flexDirection: "row", gap: ESPACO.sm, marginTop: ESPACO.xs },
  tipoBotao: {
    flex: 1,
    minHeight: 46,
    borderWidth: 2,
    borderColor: CORES.borda,
    borderRadius: RAIO.md,
    alignItems: "center",
    justifyContent: "center",
  },
  tipoBotaoAtivo: {
    borderColor: CORES.primario,
    backgroundColor: CORES.primario,
  },
  tipoTexto: { color: CORES.textoSecundario, fontWeight: "900" },
  tipoTextoAtivo: { color: "#fff" },
  inputComPrefixo: {
    flexDirection: "row",
    alignItems: "center",
    minHeight: 48,
    borderWidth: 1,
    borderColor: CORES.borda,
    borderRadius: RAIO.md,
    backgroundColor: "#fff",
    marginTop: ESPACO.xs,
  },
  prefixo: {
    color: CORES.textoSecundario,
    fontWeight: "800",
    paddingLeft: ESPACO.md,
  },
  inputPrefixado: {
    flex: 1,
    minHeight: 46,
    color: CORES.texto,
    paddingHorizontal: ESPACO.sm,
  },
  previaBox: {
    borderRadius: RAIO.md,
    backgroundColor: "#EFF6FF",
    padding: ESPACO.md,
    gap: ESPACO.xs,
    marginTop: ESPACO.md,
  },
  previaLinha: {
    flexDirection: "row",
    justifyContent: "space-between",
    gap: ESPACO.md,
  },
  previaLabel: { color: CORES.textoSecundario, fontSize: FONTE.pequena },
  previaValor: { color: CORES.texto, fontWeight: "800" },
  descontoValor: { color: CORES.erro, fontWeight: "900" },
  previaTotalLinha: {
    borderTopWidth: 1,
    borderTopColor: "#BFDBFE",
    paddingTop: ESPACO.sm,
  },
  previaTotal: { color: CORES.texto, fontSize: FONTE.media, fontWeight: "900" },
  liquidoValor: {
    color: CORES.sucesso,
    fontSize: FONTE.media,
    fontWeight: "900",
  },
  erro: { color: CORES.erro, fontSize: FONTE.pequena, marginTop: ESPACO.sm },
  acoes: { flexDirection: "row", gap: ESPACO.sm, marginTop: ESPACO.lg },
  acoesTotal: { flexDirection: "row", gap: ESPACO.sm, marginTop: ESPACO.lg },
  cancelar: {
    flex: 1,
    minHeight: 50,
    borderWidth: 1,
    borderColor: CORES.borda,
    borderRadius: RAIO.md,
    alignItems: "center",
    justifyContent: "center",
  },
  cancelarTexto: { color: CORES.textoSecundario, fontWeight: "800" },
  remover: {
    flex: 1,
    minHeight: 50,
    borderRadius: RAIO.md,
    backgroundColor: CORES.erro,
    alignItems: "center",
    justifyContent: "center",
  },
  salvar: {
    flex: 1,
    minHeight: 50,
    borderRadius: RAIO.md,
    backgroundColor: CORES.sucesso,
    alignItems: "center",
    justifyContent: "center",
  },
  acaoTextoClaro: { color: "#fff", fontWeight: "900" },
  desabilitado: { opacity: 0.45 },
  totalBrutoBox: {
    borderRadius: RAIO.md,
    backgroundColor: CORES.fundo,
    padding: ESPACO.md,
  },
  totalBrutoValor: {
    color: CORES.texto,
    fontSize: FONTE.destaque,
    fontWeight: "900",
    marginTop: 2,
  },
  removerDesconto: {
    flex: 1,
    minHeight: 50,
    borderWidth: 1,
    borderColor: "#FCA5A5",
    borderRadius: RAIO.md,
    alignItems: "center",
    justifyContent: "center",
  },
  removerDescontoTexto: { color: CORES.erro, fontWeight: "900" },
});
