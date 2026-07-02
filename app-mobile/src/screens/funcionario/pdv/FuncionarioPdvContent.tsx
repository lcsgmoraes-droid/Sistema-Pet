import { Ionicons } from "@expo/vector-icons";
import React, { type Dispatch, type SetStateAction } from "react";
import { ActivityIndicator, Text, TextInput, TouchableOpacity, View } from "react-native";

import KeyboardSafeScrollView from "../../../components/KeyboardSafeScrollView";
import { CORES } from "../../../theme";
import type {
  FuncionarioPdvBeneficiosPreview,
  FuncionarioPdvCaixa,
  FuncionarioPdvCliente,
  FuncionarioPdvFormaPagamento,
  FuncionarioPdvFormaPagamentoOpcao,
  FuncionarioPdvProduto,
} from "../../../types";
import { formatarMoeda } from "../../../utils/format";
import { FuncionarioPdvProductImage as ProdutoImagem } from "./FuncionarioPdvProductImage";
import { funcionarioPdvStyles as styles } from "./FuncionarioPdvStyles";
import {
  FORMAS_PAGAMENTO,
  formatarQuantidade,
  formatarQuantidadeCampo,
  formatarValorCampo,
  type ItemCarrinhoPdv,
} from "./FuncionarioPdvUtils";

export type FuncionarioPdvContentProps = {
  caixa: FuncionarioPdvCaixa | null;
  carregarCaixa: () => void | Promise<void>;
  carregandoCaixa: boolean;
  abrirScanner: () => void;
  buscaManual: string;
  setBuscaManual: Dispatch<SetStateAction<string>>;
  buscarManualProduto: () => void | Promise<void>;
  buscandoProduto: boolean;
  sugestoes: FuncionarioPdvProduto[];
  adicionarProduto: (produto: FuncionarioPdvProduto) => void;
  carrinho: ItemCarrinhoPdv[];
  totalItens: number;
  quantidadeEditando: Record<number, string>;
  valorEditando: Record<number, string>;
  alterarQuantidade: (produtoId: number, quantidade: number) => void;
  editarQuantidadeItem: (produtoId: number, texto: string) => void;
  finalizarEdicaoQuantidade: (produtoId: number) => void;
  editarValorItem: (item: ItemCarrinhoPdv, texto: string) => void;
  finalizarEdicaoValor: (item: ItemCarrinhoPdv) => void;
  cliente: FuncionarioPdvCliente | null;
  setCliente: Dispatch<SetStateAction<FuncionarioPdvCliente | null>>;
  mostrarDetalhesCliente: boolean;
  setMostrarDetalhesCliente: Dispatch<SetStateAction<boolean>>;
  clienteBusca: string;
  setClienteBusca: Dispatch<SetStateAction<string>>;
  buscarCliente: () => void | Promise<void>;
  clientesSugestoes: FuncionarioPdvCliente[];
  setClientesSugestoes: Dispatch<SetStateAction<FuncionarioPdvCliente[]>>;
  carregandoBeneficios: boolean;
  cupomCodigo: string;
  setCupomCodigo: Dispatch<SetStateAction<string>>;
  carregarBeneficios: () => void | Promise<void>;
  erroBeneficios: string | null;
  beneficiosPreview: FuncionarioPdvBeneficiosPreview | null;
  totalComBeneficios: number;
  usarCashback: boolean;
  setUsarCashback: Dispatch<SetStateAction<boolean>>;
  cashbackValor: string;
  setCashbackValor: Dispatch<SetStateAction<string>>;
  valorAPagar: number;
  formaPagamento: FuncionarioPdvFormaPagamento;
  setFormaPagamento: Dispatch<SetStateAction<FuncionarioPdvFormaPagamento>>;
  setFormaPagamentoIdSelecionada: Dispatch<SetStateAction<number | null>>;
  setNumeroParcelas: Dispatch<SetStateAction<number>>;
  setNsuCartao: Dispatch<SetStateAction<string>>;
  valorRecebido: string;
  setValorRecebido: Dispatch<SetStateAction<string>>;
  troco: number;
  ehCartao: boolean;
  formaPagamentoSelecionada: FuncionarioPdvFormaPagamentoOpcao | null;
  opcoesCartao: FuncionarioPdvFormaPagamentoOpcao[];
  nsuCartao: string;
  parcelasCredito: number[];
  numeroParcelas: number;
  observacoes: string;
  setObservacoes: Dispatch<SetStateAction<string>>;
  total: number;
  finalizando: boolean;
  salvandoAberta: boolean;
  salvarAberta: () => void | Promise<void>;
  finalizar: () => void | Promise<void>;
};

export function FuncionarioPdvContent({
  caixa,
  carregarCaixa,
  carregandoCaixa,
  abrirScanner,
  buscaManual,
  setBuscaManual,
  buscarManualProduto,
  buscandoProduto,
  sugestoes,
  adicionarProduto,
  carrinho,
  totalItens,
  quantidadeEditando,
  valorEditando,
  alterarQuantidade,
  editarQuantidadeItem,
  finalizarEdicaoQuantidade,
  editarValorItem,
  finalizarEdicaoValor,
  cliente,
  setCliente,
  mostrarDetalhesCliente,
  setMostrarDetalhesCliente,
  clienteBusca,
  setClienteBusca,
  buscarCliente,
  clientesSugestoes,
  setClientesSugestoes,
  carregandoBeneficios,
  cupomCodigo,
  setCupomCodigo,
  carregarBeneficios,
  erroBeneficios,
  beneficiosPreview,
  totalComBeneficios,
  usarCashback,
  setUsarCashback,
  cashbackValor,
  setCashbackValor,
  valorAPagar,
  formaPagamento,
  setFormaPagamento,
  setFormaPagamentoIdSelecionada,
  setNumeroParcelas,
  setNsuCartao,
  valorRecebido,
  setValorRecebido,
  troco,
  ehCartao,
  formaPagamentoSelecionada,
  opcoesCartao,
  nsuCartao,
  parcelasCredito,
  numeroParcelas,
  observacoes,
  setObservacoes,
  total,
  finalizando,
  salvandoAberta,
  salvarAberta,
  finalizar,
}: FuncionarioPdvContentProps) {
  return (
    <KeyboardSafeScrollView style={styles.container} contentContainerStyle={styles.conteudo}>
        <View style={styles.headerCard}>
          <View style={styles.headerIcone}>
            <Ionicons name="cart-outline" size={24} color={CORES.primario} />
          </View>
          <View style={{ flex: 1 }}>
            <Text style={styles.titulo}>PDV rapido</Text>
            <Text style={styles.subtitulo}>Venda simples usando os dados e regras do ERP.</Text>
          </View>
          <TouchableOpacity style={styles.botaoAtualizarCaixa} onPress={carregarCaixa} disabled={carregandoCaixa}>
            {carregandoCaixa ? (
              <ActivityIndicator color={CORES.primario} />
            ) : (
              <Ionicons name="refresh" size={18} color={CORES.primario} />
            )}
          </TouchableOpacity>
        </View>

        <View style={[styles.caixaBox, caixa?.aberto ? styles.caixaAberto : styles.caixaFechado]}>
          <Ionicons
            name={caixa?.aberto ? "checkmark-circle-outline" : "alert-circle-outline"}
            size={20}
            color={caixa?.aberto ? CORES.sucesso : CORES.aviso}
          />
          <Text style={styles.caixaTexto}>
            {caixa?.aberto ? `Caixa #${caixa.numero_caixa ?? caixa.caixa_id} aberto` : caixa?.mensagem || "Consultando caixa..."}
          </Text>
        </View>

        <View style={styles.card}>
          <TouchableOpacity
            style={styles.botaoScan}
            onPress={abrirScanner}
          >
            <Ionicons name="camera" size={20} color="#fff" />
            <Text style={styles.botaoScanTexto}>Ler codigo de barras</Text>
          </TouchableOpacity>

          <View style={styles.buscaLinha}>
            <TextInput
              value={buscaManual}
              onChangeText={setBuscaManual}
              placeholder="Buscar produto por nome, codigo ou barras"
              style={styles.inputBusca}
              returnKeyType="search"
              onSubmitEditing={() => buscarManualProduto()}
            />
            <TouchableOpacity style={styles.botaoBusca} onPress={() => buscarManualProduto()} disabled={buscandoProduto}>
              {buscandoProduto ? <ActivityIndicator color="#fff" /> : <Ionicons name="search" size={20} color="#fff" />}
            </TouchableOpacity>
          </View>

          {sugestoes.map((produto) => (
            <TouchableOpacity key={produto.id} style={styles.sugestao} onPress={() => adicionarProduto(produto)}>
              <ProdutoImagem uri={produto.imagem_url} />
              <View style={{ flex: 1 }}>
                <Text style={styles.sugestaoNome} numberOfLines={2}>{produto.nome}</Text>
                <Text style={styles.sugestaoMeta}>
                  SKU {produto.codigo || "-"} | Estoque {formatarQuantidade(produto.estoque_atual)} | {formatarMoeda(produto.preco_venda)}
                </Text>
              </View>
              <Ionicons name="add-circle-outline" size={22} color={CORES.sucesso} />
            </TouchableOpacity>
          ))}
        </View>

        <View style={styles.card}>
          <View style={styles.linhaTitulo}>
            <Text style={styles.secaoTitulo}>Carrinho</Text>
            <Text style={styles.badge}>{formatarQuantidade(totalItens)} item(ns)</Text>
          </View>
          {carrinho.length === 0 ? (
            <View style={styles.vazio}>
              <Ionicons name="cube-outline" size={34} color={CORES.textoClaro} />
              <Text style={styles.vazioTexto}>Nenhum produto adicionado</Text>
            </View>
          ) : (
            carrinho.map((item) => (
              <View key={item.produto.id} style={styles.itemCarrinho}>
                <ProdutoImagem uri={item.produto.imagem_url} compacta />
                <View style={styles.itemCarrinhoConteudo}>
                  <View style={styles.itemCarrinhoTopo}>
                    <View style={{ flex: 1 }}>
                      <Text style={styles.itemNome} numberOfLines={2}>{item.produto.nome}</Text>
                      <Text style={styles.itemMeta}>
                        {formatarMoeda(item.produto.preco_venda)} / {(item.produto.unidade || "un").toLowerCase()}
                      </Text>
                    </View>
                    <Text style={styles.itemSubtotal}>
                      {formatarMoeda(item.quantidade * Number(item.produto.preco_venda ?? 0))}
                    </Text>
                  </View>
                  <View style={styles.itemControles}>
                    <View style={styles.campoCarrinho}>
                      <Text style={styles.campoCarrinhoLabel}>Qtd.</Text>
                      <View style={styles.quantidadeBox}>
                        <TouchableOpacity
                          style={styles.botaoQuantidade}
                          onPress={() => alterarQuantidade(item.produto.id, item.quantidade - 1)}
                        >
                          <Ionicons name="remove" size={16} color={CORES.texto} />
                        </TouchableOpacity>
                        <TextInput
                          value={quantidadeEditando[item.produto.id] ?? formatarQuantidadeCampo(item.quantidade)}
                          onChangeText={(valor) => editarQuantidadeItem(item.produto.id, valor)}
                          onBlur={() => finalizarEdicaoQuantidade(item.produto.id)}
                          keyboardType="decimal-pad"
                          returnKeyType="done"
                          selectTextOnFocus
                          style={styles.inputQuantidade}
                        />
                        <TouchableOpacity
                          style={styles.botaoQuantidade}
                          onPress={() => alterarQuantidade(item.produto.id, item.quantidade + 1)}
                        >
                          <Ionicons name="add" size={16} color={CORES.texto} />
                        </TouchableOpacity>
                      </View>
                    </View>
                    <View style={styles.campoCarrinho}>
                      <Text style={styles.campoCarrinhoLabel}>Valor (R$)</Text>
                      <TextInput
                        value={
                          valorEditando[item.produto.id] ??
                          formatarValorCampo(item.quantidade * Number(item.produto.preco_venda ?? 0))
                        }
                        onChangeText={(valor) => editarValorItem(item, valor)}
                        onBlur={() => finalizarEdicaoValor(item)}
                        keyboardType="decimal-pad"
                        returnKeyType="done"
                        selectTextOnFocus
                        style={styles.inputValorItem}
                      />
                    </View>
                  </View>
                </View>
              </View>
            ))
          )}
        </View>

        <View style={styles.card}>
          <Text style={styles.secaoTitulo}>Comprador opcional</Text>
          {cliente ? (
            <>
              <View style={styles.clienteSelecionado}>
                <View style={{ flex: 1 }}>
                  <Text style={styles.clienteNome}>{cliente.nome}</Text>
                  <Text style={styles.clienteMeta}>
                    Codigo {cliente.codigo || "-"} | {cliente.tipo_cadastro || "pessoa"}
                  </Text>
                </View>
                <TouchableOpacity
                  style={styles.botaoDetalhesCliente}
                  onPress={() => setMostrarDetalhesCliente((atual) => !atual)}
                >
                  <Ionicons name="information-circle-outline" size={17} color={CORES.primario} />
                  <Text style={styles.botaoDetalhesClienteTexto}>Detalhes</Text>
                </TouchableOpacity>
                <TouchableOpacity
                  style={styles.botaoLimpar}
                  onPress={() => {
                    setCliente(null);
                    setMostrarDetalhesCliente(false);
                    setUsarCashback(false);
                    setCashbackValor("");
                  }}
                >
                  <Ionicons name="close" size={18} color={CORES.erro} />
                </TouchableOpacity>
              </View>
              {mostrarDetalhesCliente ? (
                <View style={styles.detalhesCliente}>
                  <Text style={styles.detalhesClienteTitulo}>Detalhes do cliente</Text>
                  <Text style={styles.detalhesClienteLinha}>Telefone: {cliente.celular || cliente.telefone || "-"}</Text>
                  <Text style={styles.detalhesClienteLinha}>Documento: {cliente.documento || "-"}</Text>
                  <Text style={styles.detalhesClienteLinha}>Email: {cliente.email || "-"}</Text>
                  <Text style={styles.detalhesClienteLinha}>Endereco: {cliente.endereco || "-"}</Text>
                  <Text style={styles.detalhesClienteLinha}>Credito: {formatarMoeda(cliente.credito ?? 0)}</Text>
                  <Text style={styles.detalhesClienteSubtitulo}>Cartao fidelidade</Text>
                  <Text style={styles.detalhesClienteLinha}>
                    {cliente.fidelidade
                      ? `Pontos ${cliente.fidelidade.pontos ?? 0} | Carimbos ${cliente.fidelidade.carimbos ?? 0}`
                      : "Sem informacao de fidelidade"}
                  </Text>
                  <Text style={styles.detalhesClienteSubtitulo}>Cupons disponiveis</Text>
                  {(cliente.cupons_disponiveis ?? []).length ? (
                    (cliente.cupons_disponiveis ?? []).slice(0, 3).map((cupom: any, indice: number) => (
                      <Text key={`${cupom.code ?? indice}`} style={styles.detalhesClienteLinha}>
                        {cupom.code ?? "Cupom"} {cupom.discount_applied ? `- ${formatarMoeda(cupom.discount_applied)}` : ""}
                      </Text>
                    ))
                  ) : (
                    <Text style={styles.detalhesClienteLinha}>Nenhum cupom nominal carregado.</Text>
                  )}
                </View>
              ) : null}
            </>
          ) : (
            <>
              <View style={styles.buscaLinha}>
                <TextInput
                  value={clienteBusca}
                  onChangeText={setClienteBusca}
                  placeholder="Buscar pessoa por nome ou telefone"
                  style={styles.inputBusca}
                  returnKeyType="search"
                  onSubmitEditing={() => buscarCliente()}
                />
                <TouchableOpacity style={styles.botaoBusca} onPress={() => buscarCliente()}>
                  <Ionicons name="search" size={20} color="#fff" />
                </TouchableOpacity>
              </View>
              {clientesSugestoes.map((item) => (
                <TouchableOpacity
                  key={item.id}
                  style={styles.sugestao}
                  onPress={() => {
                    setCliente(item);
                    setMostrarDetalhesCliente(false);
                    setClientesSugestoes([]);
                    setClienteBusca("");
                    setUsarCashback(false);
                    setCashbackValor("");
                  }}
                >
                  <View style={{ flex: 1 }}>
                    <Text style={styles.sugestaoNome}>{item.nome}</Text>
                    <Text style={styles.sugestaoMeta}>
                      Codigo {item.codigo || "-"} | {item.celular || item.telefone || "-"}
                      {item.tipo_cadastro ? ` | ${item.tipo_cadastro}` : ""}
                    </Text>
                  </View>
                  <Ionicons name="person-add-outline" size={20} color={CORES.primario} />
                </TouchableOpacity>
              ))}
            </>
          )}
        </View>

        <View style={styles.card}>
          <View style={styles.linhaTitulo}>
            <Text style={styles.secaoTitulo}>Beneficios e campanhas</Text>
            {carregandoBeneficios ? <ActivityIndicator color={CORES.primario} /> : null}
          </View>

          <View style={styles.buscaLinha}>
            <TextInput
              value={cupomCodigo}
              onChangeText={setCupomCodigo}
              placeholder="Codigo do cupom"
              autoCapitalize="characters"
              style={styles.inputBusca}
            />
            <TouchableOpacity style={styles.botaoBusca} onPress={carregarBeneficios} disabled={!carrinho.length}>
              <Ionicons name="ticket-outline" size={20} color="#fff" />
            </TouchableOpacity>
          </View>

          {erroBeneficios ? (
            <View style={styles.beneficioErro}>
              <Ionicons name="alert-circle-outline" size={18} color={CORES.erro} />
              <Text style={styles.beneficioErroTexto}>{erroBeneficios}</Text>
            </View>
          ) : null}

          {beneficiosPreview?.cupons_disponiveis?.length ? (
            <View style={styles.cuponsLista}>
              {beneficiosPreview.cupons_disponiveis.slice(0, 3).map((cupom) => (
                <TouchableOpacity
                  key={cupom.code}
                  style={styles.cupomChip}
                  onPress={() => setCupomCodigo(cupom.code)}
                >
                  <Ionicons name="pricetag-outline" size={15} color={CORES.primario} />
                  <Text style={styles.cupomChipTexto}>
                    {cupom.code} - {formatarMoeda(cupom.discount_applied)}
                  </Text>
                </TouchableOpacity>
              ))}
            </View>
          ) : null}

          {beneficiosPreview?.beneficios_gerados?.length ? (
            <View style={styles.beneficiosGeradosBox}>
              <Text style={styles.beneficiosGeradosTitulo}>Beneficios que esta venda vai gerar</Text>
              {beneficiosPreview.beneficios_gerados.slice(0, 4).map((beneficio, indice) => (
                <View key={`${beneficio.tipo}-${indice}`} style={styles.beneficioGeradoLinha}>
                  <Ionicons
                    name={beneficio.tipo === "cashback" ? "wallet-outline" : beneficio.tipo === "fidelidade" ? "star-outline" : "ticket-outline"}
                    size={16}
                    color={CORES.sucesso}
                  />
                  <View style={{ flex: 1 }}>
                    <Text style={styles.beneficioGeradoTitulo}>{beneficio.titulo}</Text>
                    <Text style={styles.beneficioGeradoDescricao}>
                      {beneficio.descricao || (beneficio.valor ? formatarMoeda(beneficio.valor) : `${beneficio.quantidade ?? 0}`)}
                    </Text>
                  </View>
                </View>
              ))}
            </View>
          ) : null}

          {cliente ? (
            <View style={styles.cashbackBox}>
              <View style={{ flex: 1 }}>
                <Text style={styles.cashbackTitulo}>Cashback disponivel</Text>
                <Text style={styles.cashbackValor}>{formatarMoeda(beneficiosPreview?.cashback_disponivel ?? 0)}</Text>
              </View>
              <TouchableOpacity
                style={[styles.cashbackToggle, usarCashback && styles.cashbackToggleAtivo]}
                onPress={() => {
                  const saldo = beneficiosPreview?.cashback_disponivel ?? 0;
                  const sugerido = Math.min(saldo, totalComBeneficios);
                  setUsarCashback((atual) => !atual);
                  if (!usarCashback && sugerido > 0) {
                    setCashbackValor(String(sugerido.toFixed(2)).replace(".", ","));
                  }
                }}
              >
                <Ionicons
                  name={usarCashback ? "checkmark-circle" : "ellipse-outline"}
                  size={18}
                  color={usarCashback ? "#fff" : CORES.primario}
                />
                <Text style={[styles.cashbackToggleTexto, usarCashback && styles.cashbackToggleTextoAtivo]}>
                  Usar
                </Text>
              </TouchableOpacity>
            </View>
          ) : (
            <View style={styles.beneficioInfo}>
              <Ionicons name="person-circle-outline" size={18} color={CORES.textoSecundario} />
              <Text style={styles.beneficioInfoTexto}>Selecione um cliente para ver cashback e cupons nominais.</Text>
            </View>
          )}

          {usarCashback ? (
            <>
              <Text style={styles.label}>Valor de cashback</Text>
              <TextInput
                value={cashbackValor}
                onChangeText={setCashbackValor}
                placeholder="Ex: 10,00"
                keyboardType="decimal-pad"
                style={styles.input}
              />
            </>
          ) : null}

          {beneficiosPreview ? (
            <View style={styles.beneficioResumo}>
              <View style={styles.beneficioLinha}>
                <Text style={styles.beneficioResumoLabel}>Subtotal</Text>
                <Text style={styles.beneficioResumoValor}>{formatarMoeda(beneficiosPreview.subtotal)}</Text>
              </View>
              {beneficiosPreview.desconto_cupom > 0 ? (
                <View style={styles.beneficioLinha}>
                  <Text style={styles.beneficioResumoLabel}>Cupom</Text>
                  <Text style={styles.beneficioResumoDesconto}>- {formatarMoeda(beneficiosPreview.desconto_cupom)}</Text>
                </View>
              ) : null}
              {beneficiosPreview.cashback_valor > 0 ? (
                <View style={styles.beneficioLinha}>
                  <Text style={styles.beneficioResumoLabel}>Cashback</Text>
                  <Text style={styles.beneficioResumoDesconto}>- {formatarMoeda(beneficiosPreview.cashback_valor)}</Text>
                </View>
              ) : null}
              <View style={styles.beneficioLinha}>
                <Text style={styles.beneficioResumoTotal}>A pagar</Text>
                <Text style={styles.beneficioResumoTotal}>{formatarMoeda(valorAPagar)}</Text>
              </View>
            </View>
          ) : null}
        </View>

        <View style={styles.card}>
          <Text style={styles.secaoTitulo}>Pagamento</Text>
          <View style={styles.formasGrid}>
            {FORMAS_PAGAMENTO.map((forma) => (
              <TouchableOpacity
                key={forma.key}
                style={[styles.formaBotao, formaPagamento === forma.key && styles.formaBotaoAtivo]}
                onPress={() => {
                  setFormaPagamento(forma.key);
                  setFormaPagamentoIdSelecionada(null);
                  setNumeroParcelas(1);
                  setNsuCartao("");
                }}
              >
                <Ionicons
                  name={forma.icon as keyof typeof Ionicons.glyphMap}
                  size={20}
                  color={formaPagamento === forma.key ? CORES.primario : CORES.textoSecundario}
                />
                <Text style={[styles.formaTexto, formaPagamento === forma.key && styles.formaTextoAtivo]}>
                  {forma.label}
                </Text>
              </TouchableOpacity>
            ))}
          </View>

          {formaPagamento === "dinheiro" ? (
            <>
              <Text style={styles.label}>Valor recebido</Text>
              <TextInput
                value={valorRecebido}
                onChangeText={setValorRecebido}
                placeholder="Ex: 100,00"
                keyboardType="decimal-pad"
                style={styles.input}
              />
              <Text style={styles.troco}>Troco: {formatarMoeda(troco)}</Text>
            </>
          ) : null}

          {ehCartao ? (
            <View style={styles.cartaoBox}>
              <Text style={styles.label}>Bandeira/operadora</Text>
              {!formaPagamentoSelecionada ? (
                <Text style={styles.cartaoInstrucao}>Selecione a bandeira/operadora do cartao</Text>
              ) : null}
              {opcoesCartao.length ? (
                <View style={styles.cartaoOpcoesGrid}>
                  {opcoesCartao.map((opcao) => {
                    const ativa = formaPagamentoSelecionada?.id === opcao.id;
                    return (
                      <TouchableOpacity
                        key={opcao.id}
                        style={[styles.cartaoOpcao, ativa && styles.cartaoOpcaoAtiva]}
                        onPress={() => {
                          setFormaPagamentoIdSelecionada(opcao.id);
                          setNumeroParcelas(1);
                        }}
                      >
                        <Text style={[styles.cartaoOpcaoTitulo, ativa && styles.cartaoOpcaoTituloAtivo]}>
                          {opcao.bandeira || opcao.nome}
                        </Text>
                        <Text style={styles.cartaoOpcaoSubtitulo}>
                          {opcao.operadora || opcao.tipo || "Cartao"} {opcao.taxa_percentual ? `- taxa ${opcao.taxa_percentual}%` : ""}
                        </Text>
                        {opcao.requer_nsu ? <Text style={styles.cartaoOpcaoAviso}>NSU recomendado</Text> : null}
                      </TouchableOpacity>
                    );
                  })}
                </View>
              ) : (
                <View style={styles.cartaoAviso}>
                  <Ionicons name="alert-circle-outline" size={18} color={CORES.erro} />
                  <Text style={styles.cartaoAvisoTexto}>Nenhuma forma de cartao configurada no ERP.</Text>
                </View>
              )}

              <Text style={styles.label}>NSU (opcional)</Text>
              <TextInput
                value={nsuCartao}
                onChangeText={setNsuCartao}
                placeholder="Codigo NSU da maquininha"
                keyboardType="number-pad"
                style={styles.input}
              />

              {formaPagamento === "credito" && parcelasCredito.length > 1 ? (
                <View style={styles.parcelasBox}>
                  <Text style={styles.label}>Parcelamento</Text>
                  <View style={styles.parcelasGrid}>
                    {parcelasCredito.map((parcela) => (
                      <TouchableOpacity
                        key={parcela}
                        style={[styles.parcelaBotao, numeroParcelas === parcela && styles.parcelaBotaoAtivo]}
                        onPress={() => setNumeroParcelas(parcela)}
                      >
                        <Text style={[styles.parcelaTexto, numeroParcelas === parcela && styles.parcelaTextoAtivo]}>
                          {parcela}x
                        </Text>
                      </TouchableOpacity>
                    ))}
                  </View>
                </View>
              ) : null}
            </View>
          ) : null}

          <Text style={styles.label}>Observacao</Text>
          <TextInput
            value={observacoes}
            onChangeText={setObservacoes}
            placeholder="Opcional"
            style={[styles.input, styles.inputMultilinha]}
            multiline
          />
        </View>

        <View style={styles.resumo}>
          <View>
            <Text style={styles.resumoLabel}>Total a pagar</Text>
            <Text style={styles.resumoValor}>{formatarMoeda(valorAPagar)}</Text>
            {valorAPagar !== total ? (
              <Text style={styles.resumoSubvalor}>Venda {formatarMoeda(totalComBeneficios)}</Text>
            ) : null}
          </View>
          <View style={styles.resumoAcoes}>
            <TouchableOpacity
              style={[styles.botaoSalvarAberta, (salvandoAberta || finalizando || !carrinho.length || !caixa?.aberto) && styles.botaoDesabilitado]}
              onPress={salvarAberta}
              disabled={salvandoAberta || finalizando || !carrinho.length || !caixa?.aberto}
            >
              {salvandoAberta ? <ActivityIndicator color={CORES.primario} /> : <Ionicons name="save-outline" size={18} color={CORES.primario} />}
              <Text style={styles.botaoSalvarAbertaTexto}>Salvar para o caixa</Text>
            </TouchableOpacity>
            <TouchableOpacity
              style={[styles.botaoFinalizar, (finalizando || salvandoAberta || !carrinho.length || !caixa?.aberto) && styles.botaoDesabilitado]}
              onPress={finalizar}
              disabled={finalizando || salvandoAberta || !carrinho.length || !caixa?.aberto}
            >
              {finalizando ? <ActivityIndicator color="#fff" /> : <Ionicons name="checkmark-circle" size={20} color="#fff" />}
              <Text style={styles.botaoFinalizarTexto}>Finalizar</Text>
            </TouchableOpacity>
          </View>
        </View>
    </KeyboardSafeScrollView>
  );
}
