import React, { type Dispatch, type SetStateAction } from "react";
import {
  ActivityIndicator,
  Modal,
  ScrollView,
  Text,
  TextInput,
  TouchableOpacity,
  View,
} from "react-native";

import { detalheEntregaStyles as styles } from "./DetalheEntregaStyles";
import type {
  FormaRecebimento,
  Parada,
  Rota,
  VendaDetalhes,
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
  return (
    <>
      <Modal
        visible={modalOrdemAberto}
        transparent
        animationType="fade"
        onRequestClose={fecharModalOrdem}
      >
        <View style={styles.modalOverlay}>
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
                  {salvandoOrdemManual ? "Salvando..." : "Salvar posiÃ§Ã£o"}
                </Text>
              </TouchableOpacity>
            </View>
          </View>
        </View>
      </Modal>

      <Modal
        visible={modalNaoEntregueAberto}
        transparent
        animationType="fade"
        onRequestClose={fecharModalNaoEntregue}
      >
        <View style={styles.modalOverlay}>
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
        </View>
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
              PrÃ©-integraÃ§Ã£o Stone/Operadora
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
                  DÃ©bito
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
                  CrÃ©dito
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
              <Text style={styles.modalTitulo}>?? Detalhes da Venda</Text>
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
                <Text style={styles.detalheLinha}>
                  <Text style={styles.detalheLabel}>Pagamento: </Text>
                  {vendaDetalhes?.forma_pagamento || "N/A"}
                </Text>
                <Text style={styles.detalheLinha}>
                  <Text style={styles.detalheLabel}>Status pagamento: </Text>
                  {vendaDetalhes?.status_pagamento || "N/A"}
                </Text>
                <Text style={styles.detalheLinha}>
                  <Text style={styles.detalheLabel}>EndereÃ§o: </Text>
                  {vendaDetalhes?.endereco_entrega || "N/A"}
                </Text>
                <Text style={styles.detalheLinha}>
                  <Text style={styles.detalheLabel}>Obs. da entrega: </Text>
                  {vendaDetalhes?.observacoes_entrega || "N/A"}
                </Text>
                <Text style={styles.detalheLinha}>
                  <Text style={styles.detalheLabel}>Total: </Text>
                  R$ {Number(vendaDetalhes?.valor_total ?? vendaDetalhes?.total ?? 0).toFixed(2)}
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
                      {Number(item.quantidade || 0)} x R$ {Number(item.preco_unitario || 0).toFixed(2)}
                      {" ? "}R$ {Number(item.subtotal || 0).toFixed(2)}
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
