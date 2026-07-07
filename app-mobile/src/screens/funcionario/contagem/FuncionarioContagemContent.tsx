import { Ionicons } from "@expo/vector-icons";
import React, { type Dispatch, type SetStateAction } from "react";
import { ActivityIndicator, Text, TextInput, TouchableOpacity, View } from "react-native";

import KeyboardSafeScrollView from "../../../components/KeyboardSafeScrollView";
import { CORES } from "../../../theme";
import type {
  FuncionarioContagem,
  FuncionarioContagemAplicarEstoqueModo,
  FuncionarioContagemFornecedor,
  FuncionarioContagemResumo,
  FuncionarioProdutoEstoque,
} from "../../../types";
import { formatarMoeda } from "../../../utils/format";
import {
  FuncionarioContagemCheckboxLinha as CheckboxLinha,
  FuncionarioContagemProdutoImagem as ProdutoImagem,
} from "./FuncionarioContagemItemComponents";
import { funcionarioContagemStyles as styles } from "./FuncionarioContagemStyles";
import { formatarQuantidade, type ContagemItemLocal } from "./FuncionarioContagemUtils";

type ResumoContagem = {
  quantidadeTotal: number;
  totalCusto: number;
  totalVenda: number;
};

export type FuncionarioContagemContentProps = {
  titulo: string;
  alterarTitulo: (valor: string) => void;
  buscaFornecedor: string;
  alterarBuscaFornecedor: (valor: string) => void;
  fornecedor: FuncionarioContagemFornecedor | null;
  limparFornecedor: () => void;
  buscarFornecedor: () => void | Promise<void>;
  fornecedores: FuncionarioContagemFornecedor[];
  selecionarFornecedor: (item: FuncionarioContagemFornecedor) => void;
  observacao: string;
  alterarObservacao: (valor: string) => void;
  abrirScanner: () => void;
  buscaManual: string;
  setBuscaManual: Dispatch<SetStateAction<string>>;
  buscarManualProduto: () => void | Promise<void>;
  buscandoProduto: boolean;
  sugestoes: FuncionarioProdutoEstoque[];
  selecionarProduto: (item: FuncionarioProdutoEstoque) => void;
  produto: FuncionarioProdutoEstoque | null;
  limparProduto: () => void;
  quantidade: string;
  setQuantidade: Dispatch<SetStateAction<string>>;
  observacaoItem: string;
  setObservacaoItem: Dispatch<SetStateAction<string>>;
  adicionarItem: () => void;
  itens: ContagemItemLocal[];
  removerItem: (id: string) => void;
  resumo: ResumoContagem;
  mostrarCusto: boolean;
  setMostrarCusto: Dispatch<SetStateAction<boolean>>;
  mostrarVenda: boolean;
  setMostrarVenda: Dispatch<SetStateAction<boolean>>;
  feedbackVibracaoAtiva: boolean;
  setFeedbackVibracaoAtiva: Dispatch<SetStateAction<boolean>>;
  feedbackVozErroAtiva: boolean;
  setFeedbackVozErroAtiva: Dispatch<SetStateAction<boolean>>;
  salvando: boolean;
  salvar: () => void | Promise<FuncionarioContagem | null>;
  aplicandoEstoque: FuncionarioContagemAplicarEstoqueModo | null;
  confirmarAplicarEstoque: (modo: FuncionarioContagemAplicarEstoqueModo) => void;
  exportando: "pdf" | "xlsx" | null;
  exportar: (formato: "pdf" | "xlsx") => void | Promise<void>;
  contagemSalva: FuncionarioContagem | null;
  contagensRecentes: FuncionarioContagemResumo[];
  carregandoHistorico: boolean;
  abrirContagem: (contagemId: number) => void | Promise<void>;
  confirmarExcluirContagem: (contagem: FuncionarioContagemResumo) => void;
  excluindoContagemId: number | null;
};

export function FuncionarioContagemContent({
  titulo,
  alterarTitulo,
  buscaFornecedor,
  alterarBuscaFornecedor,
  fornecedor,
  limparFornecedor,
  buscarFornecedor,
  fornecedores,
  selecionarFornecedor,
  observacao,
  alterarObservacao,
  abrirScanner,
  buscaManual,
  setBuscaManual,
  buscarManualProduto,
  buscandoProduto,
  sugestoes,
  selecionarProduto,
  produto,
  limparProduto,
  quantidade,
  setQuantidade,
  observacaoItem,
  setObservacaoItem,
  adicionarItem,
  itens,
  removerItem,
  resumo,
  mostrarCusto,
  setMostrarCusto,
  mostrarVenda,
  setMostrarVenda,
  feedbackVibracaoAtiva,
  setFeedbackVibracaoAtiva,
  feedbackVozErroAtiva,
  setFeedbackVozErroAtiva,
  salvando,
  salvar,
  aplicandoEstoque,
  confirmarAplicarEstoque,
  exportando,
  exportar,
  contagemSalva,
  contagensRecentes,
  carregandoHistorico,
  abrirContagem,
  confirmarExcluirContagem,
  excluindoContagemId,
}: FuncionarioContagemContentProps) {
  const contagemJaAplicada =
    contagemSalva?.status === "entrada_aplicada" || contagemSalva?.status === "balanco_aplicado";
  const bloqueiaAcoesEstoque = !itens.length || aplicandoEstoque !== null || salvando || contagemJaAplicada;

  return (
    <KeyboardSafeScrollView style={styles.container} contentContainerStyle={styles.conteudo}>
      <View style={styles.headerCard}>
        <View style={styles.headerIcone}>
          <Ionicons name="clipboard-outline" size={24} color={CORES.aviso} />
        </View>
        <View style={styles.headerTexto}>
          <Text style={styles.titulo}>Contagem</Text>
          <Text style={styles.subtitulo}>Bipe produtos e gere PDF ou Excel.</Text>
        </View>
      </View>

      <View style={styles.card}>
        <Text style={styles.secaoTitulo}>Cabecalho</Text>
        <Text style={styles.label}>Titulo</Text>
        <TextInput
          value={titulo}
          onChangeText={alterarTitulo}
          placeholder="Ex: Devolucao fornecedor"
          style={styles.input}
        />

        <Text style={styles.label}>Fornecedor</Text>
        <View style={styles.buscaLinha}>
          <TextInput
            value={buscaFornecedor}
            onChangeText={alterarBuscaFornecedor}
            placeholder="Opcional"
            style={styles.inputBusca}
            returnKeyType="search"
            onSubmitEditing={() => buscarFornecedor()}
          />
          {fornecedor ? (
            <TouchableOpacity style={styles.botaoBusca} onPress={limparFornecedor}>
              <Ionicons name="close" size={20} color="#fff" />
            </TouchableOpacity>
          ) : (
            <TouchableOpacity style={styles.botaoBusca} onPress={() => buscarFornecedor()}>
              <Ionicons name="search" size={20} color="#fff" />
            </TouchableOpacity>
          )}
        </View>

        {fornecedores.map((item) => (
          <TouchableOpacity key={item.id} style={styles.sugestao} onPress={() => selecionarFornecedor(item)}>
            <View style={styles.fornecedorIcone}>
              <Ionicons name="business-outline" size={18} color={CORES.primario} />
            </View>
            <View style={{ flex: 1 }}>
              <Text style={styles.sugestaoNome}>{item.nome}</Text>
              <Text style={styles.sugestaoMeta}>{item.documento || "Fornecedor"}</Text>
            </View>
            <Ionicons name="chevron-forward" size={18} color={CORES.textoClaro} />
          </TouchableOpacity>
        ))}

        <Text style={styles.label}>Observacao da contagem</Text>
        <TextInput
          value={observacao}
          onChangeText={alterarObservacao}
          placeholder="Opcional"
          style={[styles.input, styles.inputMultilinha]}
          multiline
        />
      </View>

      <View style={styles.card}>
        <TouchableOpacity
          style={styles.botaoScan}
          onPress={abrirScanner}
        >
          <Ionicons name="camera" size={20} color="#fff" />
          <Text style={styles.botaoScanTexto}>Ler codigo de barras</Text>
        </TouchableOpacity>

        <View style={styles.feedbackOpcoes}>
          <CheckboxLinha
            ativo={feedbackVibracaoAtiva}
            titulo="Vibracao"
            descricao="Feedback curto nas leituras."
            onPress={() => setFeedbackVibracaoAtiva((atual) => !atual)}
          />
          <CheckboxLinha
            ativo={feedbackVozErroAtiva}
            titulo="Voz no erro"
            descricao="Fala quando o codigo nao for encontrado."
            onPress={() => setFeedbackVozErroAtiva((atual) => !atual)}
          />
        </View>

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

        {sugestoes.map((item) => (
          <TouchableOpacity key={item.id} style={styles.sugestao} onPress={() => selecionarProduto(item)}>
            <ProdutoImagem uri={item.imagem_url} />
            <View style={{ flex: 1 }}>
              <Text style={styles.sugestaoNome} numberOfLines={2}>
                {item.nome}
              </Text>
              <Text style={styles.sugestaoMeta}>SKU {item.codigo || "-"} | {item.unidade || "UN"}</Text>
            </View>
            <Ionicons name="chevron-forward" size={18} color={CORES.textoClaro} />
          </TouchableOpacity>
        ))}
      </View>

      {produto ? (
        <View style={styles.card}>
          <View style={styles.produtoCabecalho}>
            <ProdutoImagem uri={produto.imagem_url} compacta />
            <View style={{ flex: 1 }}>
              <Text style={styles.produtoNome}>{produto.nome}</Text>
              <Text style={styles.produtoMeta}>SKU {produto.codigo || "-"} | {produto.unidade || "UN"}</Text>
            </View>
            <TouchableOpacity style={styles.botaoLimpar} onPress={limparProduto}>
              <Ionicons name="close" size={18} color={CORES.erro} />
            </TouchableOpacity>
          </View>

          <View style={styles.metricas}>
            <View style={styles.metrica}>
              <Text style={styles.metricaLabel}>Custo</Text>
              <Text style={styles.metricaValor}>{formatarMoeda(produto.preco_custo)}</Text>
            </View>
            <View style={styles.metrica}>
              <Text style={styles.metricaLabel}>Venda</Text>
              <Text style={styles.metricaValor}>{formatarMoeda(produto.preco_venda)}</Text>
            </View>
          </View>

          <Text style={styles.label}>Quantidade contada</Text>
          <TextInput
            value={quantidade}
            onChangeText={setQuantidade}
            placeholder="Ex: 12"
            keyboardType="decimal-pad"
            style={styles.input}
          />

          <Text style={styles.label}>Observacao do item</Text>
          <TextInput
            value={observacaoItem}
            onChangeText={setObservacaoItem}
            placeholder="Opcional"
            style={[styles.input, styles.inputMultilinha]}
            multiline
          />

          <TouchableOpacity style={styles.botaoSalvar} onPress={adicionarItem}>
            <Ionicons name="add-circle" size={20} color="#fff" />
            <Text style={styles.botaoSalvarTexto}>Adicionar item</Text>
          </TouchableOpacity>
        </View>
      ) : null}

      <View style={styles.card}>
        <View style={styles.secaoCabecalho}>
          <Text style={styles.secaoTitulo}>Itens contados</Text>
          <Text style={styles.badge}>{itens.length}</Text>
        </View>

        {itens.length ? (
          itens.map((item) => (
            <View key={item.id} style={styles.itemLinha}>
              <ProdutoImagem uri={item.produto.imagem_url} compacta />
              <View style={{ flex: 1 }}>
                <Text style={styles.itemNome} numberOfLines={2}>
                  {item.produto.nome}
                </Text>
                <Text style={styles.itemMeta}>
                  SKU {item.produto.codigo || "-"} | Qtd. {formatarQuantidade(item.quantidade)} {item.produto.unidade || "UN"}
                </Text>
                {item.observacao ? <Text style={styles.itemObs} numberOfLines={2}>{item.observacao}</Text> : null}
              </View>
              <TouchableOpacity style={styles.botaoRemover} onPress={() => removerItem(item.id)}>
                <Ionicons name="trash-outline" size={18} color={CORES.erro} />
              </TouchableOpacity>
            </View>
          ))
        ) : (
          <View style={styles.vazio}>
            <Ionicons name="cube-outline" size={28} color={CORES.textoClaro} />
            <Text style={styles.vazioTexto}>Nenhum produto contado ainda.</Text>
          </View>
        )}

        <View style={styles.resumoBox}>
          <Text style={styles.resumoTexto}>Quantidade total</Text>
          <Text style={styles.resumoValor}>{formatarQuantidade(resumo.quantidadeTotal)}</Text>
        </View>
      </View>

      <View style={styles.card}>
        <Text style={styles.secaoTitulo}>Arquivo</Text>
        <CheckboxLinha
          ativo={mostrarCusto}
          titulo="Mostrar custo"
          descricao="Inclui custo unitario e total de custo."
          onPress={() => setMostrarCusto((atual) => !atual)}
        />
        <CheckboxLinha
          ativo={mostrarVenda}
          titulo="Mostrar venda"
          descricao="Inclui venda unitaria e total de venda."
          onPress={() => setMostrarVenda((atual) => !atual)}
        />

        {mostrarCusto ? (
          <View style={styles.totalLinha}>
            <Text style={styles.totalLabel}>Total custo</Text>
            <Text style={styles.totalValor}>{formatarMoeda(resumo.totalCusto)}</Text>
          </View>
        ) : null}
        {mostrarVenda ? (
          <View style={styles.totalLinha}>
            <Text style={styles.totalLabel}>Total venda</Text>
            <Text style={styles.totalValor}>{formatarMoeda(resumo.totalVenda)}</Text>
          </View>
        ) : null}

        <TouchableOpacity
          style={[styles.botaoSalvar, salvando && styles.botaoDesabilitado]}
          onPress={() => salvar()}
          disabled={salvando}
        >
          {salvando ? <ActivityIndicator color="#fff" /> : <Ionicons name="save-outline" size={20} color="#fff" />}
          <Text style={styles.botaoSalvarTexto}>{contagemSalva ? "Salvar nova versao" : "Salvar contagem"}</Text>
        </TouchableOpacity>

        <View style={styles.exportLinha}>
          <TouchableOpacity
            style={[styles.botaoExportar, (!itens.length || exportando !== null) && styles.botaoDesabilitado]}
            onPress={() => exportar("pdf")}
            disabled={!itens.length || exportando !== null}
          >
            {exportando === "pdf" ? <ActivityIndicator color="#fff" /> : <Ionicons name="document-text-outline" size={18} color="#fff" />}
            <Text style={styles.botaoExportarTexto}>PDF</Text>
          </TouchableOpacity>
          <TouchableOpacity
            style={[styles.botaoExportar, (!itens.length || exportando !== null) && styles.botaoDesabilitado]}
            onPress={() => exportar("xlsx")}
            disabled={!itens.length || exportando !== null}
          >
            {exportando === "xlsx" ? <ActivityIndicator color="#fff" /> : <Ionicons name="grid-outline" size={18} color="#fff" />}
            <Text style={styles.botaoExportarTexto}>Excel</Text>
          </TouchableOpacity>
        </View>

        {contagemSalva ? (
          <View style={styles.resultado}>
            <Ionicons name="checkmark-circle-outline" size={18} color={CORES.sucesso} />
            <Text style={styles.resultadoTexto}>
              Contagem #{contagemSalva.id} {contagemJaAplicada ? "aplicada ao estoque." : "salva."}
            </Text>
          </View>
        ) : null}
      </View>

      <View style={styles.card}>
        <Text style={styles.secaoTitulo}>Estoque</Text>
        <View style={styles.estoqueAcoesLinha}>
          <TouchableOpacity
            style={[
              styles.botaoEstoqueEntrada,
              bloqueiaAcoesEstoque && styles.botaoDesabilitado,
            ]}
            onPress={() => confirmarAplicarEstoque("entrada")}
            disabled={bloqueiaAcoesEstoque}
          >
            {aplicandoEstoque === "entrada" ? (
              <ActivityIndicator color="#fff" />
            ) : (
              <Ionicons name="download-outline" size={18} color="#fff" />
            )}
            <Text style={styles.botaoEstoqueTexto}>Fazer entrada</Text>
          </TouchableOpacity>
          <TouchableOpacity
            style={[
              styles.botaoEstoqueBalanco,
              bloqueiaAcoesEstoque && styles.botaoDesabilitado,
            ]}
            onPress={() => confirmarAplicarEstoque("balanco")}
            disabled={bloqueiaAcoesEstoque}
          >
            {aplicandoEstoque === "balanco" ? (
              <ActivityIndicator color="#fff" />
            ) : (
              <Ionicons name="swap-horizontal-outline" size={18} color="#fff" />
            )}
            <Text style={styles.botaoEstoqueTexto}>Fazer balanco</Text>
          </TouchableOpacity>
        </View>
        {contagemJaAplicada ? (
          <View style={styles.avisoEstoqueAplicado}>
            <Ionicons name="lock-closed-outline" size={16} color="#92400E" />
            <Text style={styles.avisoEstoqueAplicadoTexto}>
              Esta contagem ja foi aplicada ao estoque. Salve uma nova versao para aplicar novamente.
            </Text>
          </View>
        ) : null}
      </View>

      {contagensRecentes.length || carregandoHistorico ? (
        <View style={styles.card}>
          <View style={styles.secaoCabecalho}>
            <Text style={styles.secaoTitulo}>Recentes</Text>
            {carregandoHistorico ? <ActivityIndicator color={CORES.primario} /> : null}
          </View>
          {contagensRecentes.slice(0, 5).map((item) => (
            <View key={item.id} style={styles.historicoItem}>
              <TouchableOpacity style={styles.historicoAbrir} onPress={() => abrirContagem(item.id)}>
                <View style={{ flex: 1 }}>
                  <Text style={styles.historicoTitulo}>{item.titulo}</Text>
                  <Text style={styles.historicoMeta}>
                    #{item.id} | {item.total_itens} item(ns) | {item.fornecedor_nome || "Sem fornecedor"}
                  </Text>
                </View>
                <Ionicons name="chevron-forward" size={18} color={CORES.textoClaro} />
              </TouchableOpacity>
              <TouchableOpacity
                style={styles.botaoExcluirHistorico}
                onPress={() => confirmarExcluirContagem(item)}
                disabled={excluindoContagemId === item.id}
              >
                {excluindoContagemId === item.id ? (
                  <ActivityIndicator color={CORES.erro} size="small" />
                ) : (
                  <Ionicons name="trash-outline" size={18} color={CORES.erro} />
                )}
              </TouchableOpacity>
            </View>
          ))}
        </View>
      ) : null}
    </KeyboardSafeScrollView>
  );
}
