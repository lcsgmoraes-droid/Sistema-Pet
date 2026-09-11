import React, { type Dispatch, type SetStateAction } from "react";
import {
  ActivityIndicator,
  KeyboardAvoidingView,
  Modal,
  Platform,
  ScrollView,
  Text,
  TextInput,
  TouchableOpacity,
  View,
} from "react-native";
import { formatarMoeda } from "../../../utils/format";

import { detalheEntregaStyles as styles } from "./DetalheEntregaStyles";
import {
  montarInstrucoesPagamentoEntrega,
  type FormaRecebimento,
  type Parada,
  type Rota,
  type VendaDetalhes,
} from "./DetalheEntregaUtils";

export type DetalheEntregaModalsProps = {
  rota: Rota | null;
  processando: number | null;
  modalOrdemAberto: boolean;
  paradaOrdemEmEdicao: Parada | null;
  novaOrdemTexto: string;
  setNovaOrdemTexto: Dispatch<SetStateAction<string>>;
  salvandoOrdemManual: boolean;
  fecharModalOrdem: () => void;
  confirmarNovaOrdemManual: () => void | Promise<void>;
  modalNaoEntregueAberto: boolean;
  paradaNaoEntregueId: number | null;
  motivoNaoEntregue: string;
  setMotivoNaoEntregue: Dispatch<SetStateAction<string>>;
  fecharModalNaoEntregue: () => void;
  confirmarNaoEntregue: () => void | Promise<void>;
  modalRecebimentoAberto: boolean;
  setModalRecebimentoAberto: Dispatch<SetStateAction<boolean>>;
  formaRecebimento: FormaRecebimento;
  setFormaRecebimento: Dispatch<SetStateAction<FormaRecebimento>>;
  parcelasRecebimento: number;
  setParcelasRecebimento: Dispatch<SetStateAction<number>>;
  processandoRecebimento: boolean;
  registrarRecebimento: () => void | Promise<void>;
  modalVendaAberto: boolean;
  setModalVendaAberto: Dispatch<SetStateAction<boolean>>;
  loadingVenda: boolean;
  vendaDetalhes: VendaDetalhes | null;
};

function FormModalBody({ children }: { children: React.ReactNode }) {
  return (
    <KeyboardAvoidingView
      style={{ flex: 1, backgroundColor: "rgba(0,0,0,0.4)" }}
      behavior={Platform.OS === "ios" ? "padding" : "height"}
    >
      <ScrollView
        contentContainerStyle={{ flexGrow: 1, justifyContent: "center", padding: 20 }}
        keyboardShouldPersistTaps="handled"
      >
        {children}
      </ScrollView>
    </KeyboardAvoidingView>
  );
}

export function DetalheEntregaModals({
  rota,
  processando,
  modalOrdemAberto,
  paradaOrdemEmEdicao,
  novaOrdemTexto,
  setNovaOrdemTexto,
  salvandoOrdemManual,
  fecharModalOrdem,
  confirmarNovaOrdemManual,
  modalNaoEntregueAberto,
  paradaNaoEntregueId,
  motivoNaoEntregue,
  setMotivoNaoEntregue,
  fecharModalNaoEntregue,
  confirmarNaoEntregue,
  modalRecebimentoAberto,
  setModalRecebimentoAberto,
  formaRecebimento,
  setFormaRecebimento,
  parcelasRecebimento,
  setParcelasRecebimento,
  processandoRecebimento,
  registrarRecebimento,
  modalVendaAberto,
  setModalVendaAberto,
  loadingVenda,
  vendaDetalhes,
}: DetalheEntregaModalsProps) {
  const instrucoesPagamento = montarInstrucoesPagamentoEntrega(vendaDetalhes || {});

  return (
    <>
      <Modal
        visible={modalOrdemAberto}
        transparent
        animationType="fade"
        onRequestClose={fecharModalOrdem}
      >
        <FormModalBody>
          <View style={styles.modalCard}>
            <Text style={styles.modalTitulo}>Reordenar entrega</Text>
            <Text style={styles.modalSubtitulo}>
              Escolha a nova posicao dessa parada na rota. Aceita n1, n2 ou apenas o numero.
            </Text>

            {paradaOrdemEmEdicao ? (
              <View style={styles.modalResumoOrdem}>
                <Text style={styles.modalResumoOrdemLabel}>Entrega selecionada</Text>
                <Text style={styles.modalResumoOrdemCliente} numberOfLines={1}>
                  {paradaOrdemEmEdicao.cliente_nome ??
                    `Cliente da venda #${paradaOrdemEmEdicao.venda_id}`}
                </Text>
                <Text style={styles.modalResumoOrdemEndereco} numberOfLines={2}>
                  {paradaOrdemEmEdicao.endereco}
                </Text>
              </View>
            ) : null}

            <Text style={styles.modalCampoLabel}>
              Nova posicao (1 a {rota?.paradas.length ?? 1})
            </Text>
            <TextInput
              style={styles.modalInput}
              value={novaOrdemTexto}
              onChangeText={setNovaOrdemTexto}
              placeholder="Ex: n1 ou 1"
              placeholderTextColor="#9ca3af"
              keyboardType="default"
              autoCapitalize="none"
              returnKeyType="done"
              onSubmitEditing={() => {
                void confirmarNovaOrdemManual();
              }}
              editable={!salvandoOrdemManual}
              autoFocus
            />

            <View style={styles.modalAcoes}>
              <TouchableOpacity style={styles.modalCancelar} onPress={fecharModalOrdem}>
                <Text style={styles.modalCancelarText}>Cancelar</Text>
              </TouchableOpacity>
              <TouchableOpacity
                style={[
                  styles.modalConfirmar,
                  salvandoOrdemManual && { opacity: 0.6 },
                ]}
                disabled={salvandoOrdemManual}
                onPress={() => {
                  void confirmarNovaOrdemManual();
                }}
              >
                <Text style={styles.modalConfirmarText}>
                  {salvandoOrdemManual ? "Salvando..." : "Salvar posição"}
                </Text>
              </TouchableOpacity>
            </View>
          </View>
        </FormModalBody>
      </Modal>

      <Modal
        visible={modalNaoEntregueAberto}
        transparent
        animationType="fade"
        onRequestClose={fecharModalNaoEntregue}
      >
        <FormModalBody>
          <View style={styles.modalCard}>
            <Text style={styles.modalTitulo}>Registrar nao entrega</Text>
            <Text style={styles.modalSubtitulo}>
              Informe o motivo para devolver a venda para entregas em aberto.
            </Text>

            <Text style={styles.modalCampoLabel}>Motivo (opcional)</Text>
            <TextInput
              style={[styles.modalInput, styles.modalTextarea]}
              value={motivoNaoEntregue}
              onChangeText={setMotivoNaoEntregue}
              placeholder="Ex: cliente ausente, endereco incorreto..."
              placeholderTextColor="#9ca3af"
              multiline
              textAlignVertical="top"
              editable={processando !== paradaNaoEntregueId}
            />

            <View style={styles.modalAcoes}>
              <TouchableOpacity
                style={styles.modalCancelar}
                onPress={fecharModalNaoEntregue}
                disabled={processando === paradaNaoEntregueId}
              >
                <Text style={styles.modalCancelarText}>Cancelar</Text>
              </TouchableOpacity>
              <TouchableOpacity
                style={[
                  styles.modalConfirmar,
                  styles.modalConfirmarDanger,
                  processando === paradaNaoEntregueId && { opacity: 0.6 },
                ]}
                disabled={processando === paradaNaoEntregueId}
                onPress={() => {
                  void confirmarNaoEntregue();
                }}
              >
                <Text style={styles.modalConfirmarText}>
                  {processando === paradaNaoEntregueId ? "Registrando..." : "Confirmar"}
                </Text>
              </TouchableOpacity>
            </View>
          </View>
        </FormModalBody>
      </Modal>

      <Modal
        visible={modalRecebimentoAberto}
        transparent
        animationType="fade"
        onRequestClose={() => setModalRecebimentoAberto(false)}
      >
        <View style={styles.modalOverlay}>
          <View style={styles.modalCard}>
            <Text style={styles.modalTitulo}>Registrar Recebimento</Text>
            <Text style={styles.modalSubtitulo}>
              Pré-integração Stone/Operadora
            </Text>

            <View style={styles.opcoesLinha}>
              <TouchableOpacity
                style={[
                  styles.opcaoBtn,
                  formaRecebimento === "pix" && styles.opcaoBtnAtivo,
                ]}
                onPress={() => {
                  setFormaRecebimento("pix");
                  setParcelasRecebimento(1);
                }}
              >
                <Text
                  style={[
                    styles.opcaoTexto,
                    formaRecebimento === "pix" && styles.opcaoTextoAtivo,
                  ]}
                >
                  PIX
                </Text>
              </TouchableOpacity>

              <TouchableOpacity
                style={[
                  styles.opcaoBtn,
                  formaRecebimento === "cartao_debito" && styles.opcaoBtnAtivo,
                ]}
                onPress={() => {
                  setFormaRecebimento("cartao_debito");
                  setParcelasRecebimento(1);
                }}
              >
                <Text
                  style={[
                    styles.opcaoTexto,
                    formaRecebimento === "cartao_debito" &&
                      styles.opcaoTextoAtivo,
                  ]}
                >
                  Débito
                </Text>
              </TouchableOpacity>

              <TouchableOpacity
                style={[
                  styles.opcaoBtn,
                  formaRecebimento === "cartao_credito" && styles.opcaoBtnAtivo,
                ]}
                onPress={() => setFormaRecebimento("cartao_credito")}
              >
                <Text
                  style={[
                    styles.opcaoTexto,
                    formaRecebimento === "cartao_credito" &&
                      styles.opcaoTextoAtivo,
                  ]}
                >
                  Crédito
                </Text>
              </TouchableOpacity>
            </View>

            {formaRecebimento === "cartao_credito" && (
              <View style={styles.parcelasWrap}>
                <Text style={styles.parcelasTitulo}>Parcelas</Text>
                <View style={styles.parcelasGrid}>
                  {[1, 2, 3, 4, 5, 6].map((n) => (
                    <TouchableOpacity
                      key={n}
                      style={[
                        styles.parcelaBtn,
                        parcelasRecebimento === n && styles.parcelaBtnAtivo,
                      ]}
                      onPress={() => setParcelasRecebimento(n)}
                    >
                      <Text
                        style={[
                          styles.parcelaTexto,
                          parcelasRecebimento === n && styles.parcelaTextoAtivo,
                        ]}
                      >
                        {n}x
                      </Text>
                    </TouchableOpacity>
                  ))}
                </View>
              </View>
            )}

            <View style={styles.modalAcoes}>
              <TouchableOpacity
                style={styles.modalCancelar}
                onPress={() => setModalRecebimentoAberto(false)}
              >
                <Text style={styles.modalCancelarText}>Cancelar</Text>
              </TouchableOpacity>
              <TouchableOpacity
                style={[
                  styles.modalConfirmar,
                  processandoRecebimento && { opacity: 0.6 },
                ]}
                disabled={processandoRecebimento}
                onPress={registrarRecebimento}
              >
                <Text style={styles.modalConfirmarText}>
                  {processandoRecebimento ? "Enviando..." : "Registrar"}
                </Text>
              </TouchableOpacity>
            </View>
          </View>
        </View>
      </Modal>

      <Modal
        visible={modalVendaAberto}
        transparent
        animationType="slide"
        onRequestClose={() => setModalVendaAberto(false)}
      >
        <View style={styles.modalOverlay}>
          <View style={[styles.modalCard, { maxHeight: "85%" }]}>
            <View style={styles.modalHeaderDetalhes}>
              <Text style={styles.modalTitulo}>🧾 Detalhes da Venda</Text>
              <TouchableOpacity onPress={() => setModalVendaAberto(false)}>
                <Text style={styles.fecharDetalhes}>Fechar</Text>
              </TouchableOpacity>
            </View>

            {loadingVenda ? (
              <View style={{ paddingVertical: 20 }}>
                <ActivityIndicator size="small" color="#2563eb" />
              </View>
            ) : (
              <ScrollView>
                <Text style={styles.detalheLinha}>
                  <Text style={styles.detalheLabel}>Cliente: </Text>
                  {vendaDetalhes?.cliente?.nome || "N/A"}
                </Text>
                <Text style={styles.detalheLinha}>
                  <Text style={styles.detalheLabel}>Telefone: </Text>
                  {vendaDetalhes?.cliente?.celular || vendaDetalhes?.cliente?.telefone || "N/A"}
                </Text>
                <Text style={styles.detalheLinha}>
                  <Text style={styles.detalheLabel}>Data: </Text>
                  {vendaDetalhes?.data_venda
                    ? new Date(vendaDetalhes.data_venda).toLocaleString("pt-BR")
                    : "N/A"}
                </Text>
                <View style={styles.pagamentoEntregaBox}>
                  <Text style={styles.pagamentoEntregaTitulo}>FORMA DE PAGAMENTO</Text>
                  {instrucoesPagamento.map((instrucao) => (
                    <View key={instrucao.chave} style={styles.pagamentoEntregaItem}>
                      <Text style={styles.pagamentoEntregaResumo}>{instrucao.resumo}</Text>
                      {instrucao.alerta ? (
                        <Text style={styles.pagamentoEntregaAlerta}>⚠️ {instrucao.alerta}</Text>
                      ) : null}
                      {instrucao.complemento ? (
                        <Text style={styles.pagamentoEntregaComplemento}>
                          {instrucao.complemento}
                        </Text>
                      ) : null}
                    </View>
                  ))}
                </View>
                <Text style={styles.detalheLinha}>
                  <Text style={styles.detalheLabel}>Status pagamento: </Text>
                  {vendaDetalhes?.status_pagamento || "N/A"}
                </Text>
                <Text style={styles.detalheLinha}>
                  <Text style={styles.detalheLabel}>Endereço: </Text>
                  {vendaDetalhes?.endereco_entrega || "N/A"}
                </Text>
                <Text style={styles.detalheLinha}>
                  <Text style={styles.detalheLabel}>Obs. da entrega: </Text>
                  {vendaDetalhes?.observacoes_entrega || "N/A"}
                </Text>
                <Text style={styles.detalheLinha}>
                  <Text style={styles.detalheLabel}>Total: </Text>
                  {formatarMoeda(Number(vendaDetalhes?.valor_total ?? vendaDetalhes?.total ?? 0))}
                </Text>

                <Text style={[styles.detalheLabel, { marginTop: 12, marginBottom: 8 }]}>Itens da venda:</Text>
                {(vendaDetalhes?.itens || []).map((item, index) => (
                  <View
                    key={`${item.produto_nome || item.servico_descricao || "item"}-${index}`}
                    style={styles.itemVenda}
                  >
                    <Text style={styles.itemVendaNome}>
                      {item.produto_nome || item.servico_descricao || "Item"}
                    </Text>
                    <Text style={styles.itemVendaValor}>
                      {Number(item.quantidade || 0)} x {formatarMoeda(Number(item.preco_unitario || 0))}
                      {" • "}{formatarMoeda(Number(item.subtotal || 0))}
                    </Text>
                  </View>
                ))}
              </ScrollView>
            )}
          </View>
        </View>
      </Modal>
    </>
  );
}
