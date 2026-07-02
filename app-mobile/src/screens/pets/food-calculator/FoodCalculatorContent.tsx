import { Ionicons } from "@expo/vector-icons";
import React, { type Dispatch, type SetStateAction } from "react";
import { ActivityIndicator, Image, Text, TextInput, TouchableOpacity, View } from "react-native";

import KeyboardSafeScrollView from "../../../components/KeyboardSafeScrollView";
import type { RacaoCadastrada } from "../../../services/shop.service";
import { CORES, ESPACO, FONTE } from "../../../theme";
import type { Pet } from "../../../types";
import { calcularIdadeMeses, formatarMoeda } from "../../../utils/format";
import {
  FoodCalculatorField as Campo,
  FoodCalculatorResultCard as ResultadoCard,
} from "./FoodCalculatorResultCards";
import { FoodCalculatorSelectorModal } from "./FoodCalculatorSelectors";
import { foodCalculatorStyles as styles } from "./FoodCalculatorStyles";
import { NIVEIS_ATIVIDADE, type FoodCalculatorSelectorKind, type NivelAtividadeKey } from "./FoodCalculatorUtils";

export type FoodCalculatorContentProps = {
  racoes: RacaoCadastrada[];
  racoesFiltradas: RacaoCadastrada[];
  buscaRacao: string;
  setBuscaRacao: Dispatch<SetStateAction<string>>;
  carregandoRacoes: boolean;
  seletorAberto: FoodCalculatorSelectorKind;
  setSeletorAberto: Dispatch<SetStateAction<FoodCalculatorSelectorKind>>;
  pets: Pet[];
  petSelecionado: Pet | null;
  setPetSelecionado: Dispatch<SetStateAction<Pet | null>>;
  racaoSelecionada: RacaoCadastrada | null;
  racaoComparar: RacaoCadastrada | null;
  setRacaoComparar: Dispatch<SetStateAction<RacaoCadastrada | null>>;
  classificacoesDisponiveis: string[];
  categoriaFiltro: string | null;
  setCategoriaFiltro: Dispatch<SetStateAction<string | null>>;
  melhoresOpcoes: any[];
  setMelhoresOpcoes: Dispatch<SetStateAction<any[]>>;
  buscandoMelhor: boolean;
  adicionando: Record<number, boolean>;
  pesoPet: string;
  setPesoPet: Dispatch<SetStateAction<string>>;
  idadeMeses: string;
  setIdadeMeses: Dispatch<SetStateAction<string>>;
  nivelAtividade: NivelAtividadeKey;
  setNivelAtividade: Dispatch<SetStateAction<NivelAtividadeKey>>;
  calculando: boolean;
  resultadoPrincipal: any;
  setResultadoComparar: Dispatch<SetStateAction<any>>;
  resultadoComparar: any;
  calcular: () => void | Promise<void>;
  buscarMelhorOpcao: (classif: string | null) => void | Promise<void>;
  adicionarNoCarrinho: (produtoId: number) => void | Promise<void>;
  selecionarRacao: (racao: RacaoCadastrada) => void;
};

export function FoodCalculatorContent({
  racoes,
  racoesFiltradas,
  buscaRacao,
  setBuscaRacao,
  carregandoRacoes,
  seletorAberto,
  setSeletorAberto,
  pets,
  petSelecionado,
  setPetSelecionado,
  racaoSelecionada,
  racaoComparar,
  setRacaoComparar,
  classificacoesDisponiveis,
  categoriaFiltro,
  setCategoriaFiltro,
  melhoresOpcoes,
  setMelhoresOpcoes,
  buscandoMelhor,
  adicionando,
  pesoPet,
  setPesoPet,
  idadeMeses,
  setIdadeMeses,
  nivelAtividade,
  setNivelAtividade,
  calculando,
  resultadoPrincipal,
  setResultadoComparar,
  resultadoComparar,
  calcular,
  buscarMelhorOpcao,
  adicionarNoCarrinho,
  selecionarRacao,
}: FoodCalculatorContentProps) {
  return (
    <KeyboardSafeScrollView style={styles.container} contentContainerStyle={styles.content}>
      {/* Cabeçalho */}
      <View style={styles.header}>
        <Text style={styles.emoji}>🥣</Text>
        <Text style={styles.titulo}>Calculadora de Ração</Text>
        <Text style={styles.subtitulo}>
          Selecione uma ração do estoque e descubra a quantidade ideal por dia.
        </Text>
      </View>

      {/* Formulário */}
      <View style={styles.card}>

        {/* Seletor de pet */}
        <Campo label="Meu pet (opcional — preenche peso e idade automaticamente)">
          <TouchableOpacity
            style={styles.seletorBtn}
            onPress={() => setSeletorAberto('pet')}
          >
            {petSelecionado ? (
              <View style={styles.petSelecionadoRow}>
                {petSelecionado.foto_url ? (
                  <Image source={{ uri: petSelecionado.foto_url }} style={styles.petFotoMini} />
                ) : (
                  <View style={styles.petFotoMiniPlaceholder}><Text>🐾</Text></View>
                )}
                <View style={{ flex: 1 }}>
                  <Text style={styles.seletorNome}>{petSelecionado.nome}</Text>
                  <Text style={styles.seletorSub}>
                    {petSelecionado.peso ? `${petSelecionado.peso}kg` : ''}
                    {petSelecionado.peso && (petSelecionado.idade_aproximada || petSelecionado.data_nascimento) ? ' · ' : ''}
                    {petSelecionado.idade_aproximada
                      ? `${petSelecionado.idade_aproximada} meses`
                      : calcularIdadeMeses(petSelecionado.data_nascimento)
                      ? `${calcularIdadeMeses(petSelecionado.data_nascimento)} meses`
                      : ''}
                  </Text>
                </View>
                <TouchableOpacity onPress={() => {
                  setPetSelecionado(null);
                  setPesoPet('');
                  setIdadeMeses('');
                }}>
                  <Ionicons name="close-circle" size={20} color={CORES.erro} />
                </TouchableOpacity>
              </View>
            ) : (
              <Text style={styles.seletorPlaceholder}>
                {pets.length === 0 ? 'Nenhum pet cadastrado' : `Selecionar entre ${pets.length} pets...`}
              </Text>
            )}
            {!petSelecionado && <Ionicons name="chevron-down" size={18} color={CORES.textoClaro} />}
          </TouchableOpacity>
        </Campo>

        {/* Seleção de ração principal */}
        <Campo label="Ração principal *">
          <TouchableOpacity
            style={styles.seletorBtn}
            onPress={() => setSeletorAberto('principal')}
            disabled={carregandoRacoes}
          >
            {carregandoRacoes ? (
              <ActivityIndicator size="small" color={CORES.primario} />
            ) : racaoSelecionada ? (
              <View style={{ flex: 1 }}>
                <Text style={styles.seletorNome}>{racaoSelecionada.nome}</Text>
                <Text style={styles.seletorSub}>
                  {racaoSelecionada.peso_embalagem}kg · {formatarMoeda(racaoSelecionada.preco)}
                </Text>
              </View>
            ) : (
              <Text style={styles.seletorPlaceholder}>
                {racoes.length === 0
                  ? 'Nenhuma ração com dados cadastrados'
                  : `Selecionar entre ${racoes.length} rações...`}
              </Text>
            )}
            <Ionicons name="chevron-down" size={18} color={CORES.textoClaro} />
          </TouchableOpacity>
        </Campo>

        {/* Seleção de ração para comparar */}
        <Campo label="Ração para comparar (opcional)">
          <TouchableOpacity
            style={styles.seletorBtn}
            onPress={() => setSeletorAberto('comparar')}
            disabled={carregandoRacoes}
          >
            {racaoComparar ? (
              <View style={{ flex: 1 }}>
                <Text style={styles.seletorNome}>{racaoComparar.nome}</Text>
                <Text style={styles.seletorSub}>
                  {racaoComparar.peso_embalagem}kg · {formatarMoeda(racaoComparar.preco)}
                </Text>
              </View>
            ) : (
              <Text style={styles.seletorPlaceholder}>Selecionar para comparar...</Text>
            )}
            {racaoComparar ? (
              <TouchableOpacity
                onPress={(e) => {
                  setRacaoComparar(null);
                  setResultadoComparar(null);
                }}
              >
                <Ionicons name="close-circle" size={20} color={CORES.erro} />
              </TouchableOpacity>
            ) : (
              <Ionicons name="chevron-down" size={18} color={CORES.textoClaro} />
            )}
          </TouchableOpacity>
        </Campo>

        {/* Peso do pet */}
        <Campo label="Peso do pet (kg) *">
          <TextInput
            style={styles.input}
            placeholder="Ex: 8.5"
            placeholderTextColor={CORES.textoClaro}
            keyboardType="decimal-pad"
            value={pesoPet}
            onChangeText={setPesoPet}
          />
        </Campo>

        {/* Idade */}
        <Campo label="Idade do pet (meses, opcional)">
          <TextInput
            style={styles.input}
            placeholder="Ex: 24"
            placeholderTextColor={CORES.textoClaro}
            keyboardType="number-pad"
            value={idadeMeses}
            onChangeText={setIdadeMeses}
          />
        </Campo>

        {/* Nível de atividade */}
        <Campo label="Nível de atividade">
          {NIVEIS_ATIVIDADE.map((n) => (
            <TouchableOpacity
              key={n.key}
              style={[styles.nivelCard, nivelAtividade === n.key && styles.nivelAtivo]}
              onPress={() => setNivelAtividade(n.key as any)}
            >
              <Text style={styles.nivelEmoji}>{n.emoji}</Text>
              <View style={{ flex: 1 }}>
                <Text style={[styles.nivelLabel, nivelAtividade === n.key && styles.nivelLabelAtivo]}>
                  {n.label}
                </Text>
                <Text style={styles.nivelDesc}>{n.descricao}</Text>
              </View>
              {nivelAtividade === n.key && (
                <Text style={{ color: CORES.primario }}>✓</Text>
              )}
            </TouchableOpacity>
          ))}
        </Campo>

        {/* Seletor de categoria / melhor opção */}
        {classificacoesDisponiveis.length > 0 && (
          <Campo label="Descobrir melhor custo-benefício">
            <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 8, marginBottom: 6 }}>
              <TouchableOpacity
                onPress={() => {
                  setCategoriaFiltro(null);
                  setMelhoresOpcoes([]);
                }}
                style={[styles.categoriaBotao, categoriaFiltro === null && styles.categoriaBotaoAtivo]}
              >
                <Text style={[styles.categoriaBotaoTexto, categoriaFiltro === null && styles.categoriaBotaoTextoAtivo]}>
                  Todas
                </Text>
              </TouchableOpacity>
              {classificacoesDisponiveis.map((c) => (
                <TouchableOpacity
                  key={c}
                  onPress={() => {
                    const nova = categoriaFiltro === c ? null : c;
                    setCategoriaFiltro(nova ?? null);
                    setMelhoresOpcoes([]);
                  }}
                  style={[styles.categoriaBotao, categoriaFiltro === c && styles.categoriaBotaoAtivo]}
                >
                  <Text style={[styles.categoriaBotaoTexto, categoriaFiltro === c && styles.categoriaBotaoTextoAtivo]}>
                    {c}
                  </Text>
                </TouchableOpacity>
              ))}
            </View>
            <TouchableOpacity
              style={[styles.botaoSecundario, buscandoMelhor && styles.botaoDesativado]}
              onPress={() => buscarMelhorOpcao(categoriaFiltro)}
              disabled={buscandoMelhor}
            >
              {buscandoMelhor ? (
                <ActivityIndicator size="small" color={CORES.primario} />
              ) : (
                <Text style={styles.botaoSecundarioTexto}>
                  {categoriaFiltro ? `🏆 Ver top 3 da linha "${categoriaFiltro}"` : '🏆 Ver top 3 de todas as rações'}
                </Text>
              )}
            </TouchableOpacity>
          </Campo>
        )}

        <TouchableOpacity
          style={[styles.botao, calculando && styles.botaoDesativado]}
          onPress={calcular}
          disabled={calculando}
        >
          {calculando ? (
            <ActivityIndicator color="#fff" />
          ) : (
            <Text style={styles.botaoTexto}>
              {racaoComparar ? 'Calcular e comparar 🔄' : 'Calcular 🥣'}
            </Text>
          )}
        </TouchableOpacity>
      </View>

      {/* Top 3 melhores rações */}
      {melhoresOpcoes.length > 0 && (
        <View style={styles.comparativoContainer}>
          <Text style={styles.comparativoTitulo}>
            🏆 Top 3 custo-benefício{melhoresOpcoes[0]?.categoria ? ` — ${melhoresOpcoes[0].categoria}` : ' — Todas'}
          </Text>
          {melhoresOpcoes.map((opcao: any, idx: number) => (
            <View
              key={opcao.produto_id}
              style={[
                styles.resultadoCard,
                idx === 0 && { borderWidth: 2, borderColor: '#f59e0b', marginBottom: ESPACO.sm },
              ]}
            >
              {idx === 0 && (
                <Text style={{ fontSize: 11, fontWeight: '700', color: '#d97706', marginBottom: 4 }}>🥇 MELHOR CUSTO-BENEFÍCIO</Text>
              )}
              {idx === 1 && (
                <Text style={{ fontSize: 11, fontWeight: '700', color: '#6b7280', marginBottom: 4 }}>🥈 2º lugar</Text>
              )}
              {idx === 2 && (
                <Text style={{ fontSize: 11, fontWeight: '700', color: '#92400e', marginBottom: 4 }}>🥉 3º lugar</Text>
              )}
              <Text style={styles.resultadoNome} numberOfLines={2}>{opcao.produto_nome}</Text>
              {/* Preço da embalagem */}
              {opcao.preco > 0 && (
                <Text style={{ fontSize: FONTE.media, fontWeight: '700', color: CORES.texto, marginBottom: 6 }}>
                  {formatarMoeda(opcao.preco)}
                  <Text style={{ fontSize: FONTE.pequena, fontWeight: '400', color: CORES.textoSecundario }}> / embalagem {opcao.peso_embalagem_kg ?? ''}kg</Text>
                </Text>
              )}
              <View style={{ flexDirection: 'row', gap: 8, marginTop: 6, flexWrap: 'wrap' }}>
                <View style={[styles.itemResultado, styles.itemDestaque, { flex: 1, minWidth: 110 }]}>
                  <Text style={styles.itemEmoji}>🥣</Text>
                  <View>
                    <Text style={styles.itemTitulo}>Qtd Diária</Text>
                    <Text style={[styles.itemValor, styles.itemValorDestaque]}>{opcao.quantidade_diaria_g}g</Text>
                  </View>
                </View>
                <View style={[styles.itemResultado, styles.itemDestaque, { flex: 1, minWidth: 110 }]}>
                  <Text style={styles.itemEmoji}>💸</Text>
                  <View>
                    <Text style={styles.itemTitulo}>Custo/mês</Text>
                    <Text style={[styles.itemValor, styles.itemValorDestaque]}>{formatarMoeda(opcao.custo_mensal)}</Text>
                  </View>
                </View>
              </View>
              <Text style={{ fontSize: 11, color: CORES.textoSecundario, marginTop: 4 }}>📅 Duração: {opcao.duracao_dias} dias · R$ {opcao.custo_por_dia?.toFixed(2)}/dia</Text>
              {/* Botão adicionar ao carrinho */}
              {opcao.produto_id && (
                <TouchableOpacity
                  style={[styles.botaoAdicionar, adicionando[opcao.produto_id] && styles.botaoDesativado]}
                  onPress={() => adicionarNoCarrinho(opcao.produto_id)}
                  disabled={!!adicionando[opcao.produto_id]}
                >
                  {adicionando[opcao.produto_id] ? (
                    <ActivityIndicator size="small" color="#fff" />
                  ) : (
                    <>
                      <Ionicons name="cart-outline" size={16} color="#fff" />
                      <Text style={styles.botaoAdicionarTexto}>Adicionar ao carrinho</Text>
                    </>
                  )}
                </TouchableOpacity>
              )}
            </View>
          ))}
        </View>
      )}

      {resultadoPrincipal && !resultadoComparar && (
        <ResultadoCard resultado={resultadoPrincipal} titulo={racaoSelecionada?.nome} />
      )}

      {/* Comparativo lado a lado */}
      {resultadoPrincipal && resultadoComparar && (
        <View style={styles.comparativoContainer}>
          <Text style={styles.comparativoTitulo}>📊 Comparativo</Text>
          <View style={styles.comparativoRow}>
            <ResultadoCard
              resultado={resultadoPrincipal}
              titulo={racaoSelecionada?.nome ?? 'Ração A'}
              compact
            />
            <ResultadoCard
              resultado={resultadoComparar}
              titulo={racaoComparar?.nome ?? 'Ração B'}
              compact
            />
          </View>
          {/* Melhor custo-benefício */}
          {resultadoPrincipal.custo_mensal > 0 && resultadoComparar.custo_mensal > 0 && (
            <View style={styles.veredito}>
              <Text style={styles.vereditoTexto}>
                {resultadoPrincipal.custo_mensal <= resultadoComparar.custo_mensal
                  ? `✅ ${racaoSelecionada?.nome ?? 'Ração A'} tem menor custo mensal (${formatarMoeda(resultadoPrincipal.custo_mensal)}/mês)`
                  : `✅ ${racaoComparar?.nome ?? 'Ração B'} tem menor custo mensal (${formatarMoeda(resultadoComparar.custo_mensal)}/mês)`}
              </Text>
            </View>
          )}
        </View>
      )}

      <View style={{ height: ESPACO.xxl }} />

      <FoodCalculatorSelectorModal
        seletorAberto={seletorAberto}
        setSeletorAberto={setSeletorAberto}
        pets={pets}
        setPetSelecionado={setPetSelecionado}
        setPesoPet={setPesoPet}
        setIdadeMeses={setIdadeMeses}
        racoes={racoes}
        racoesFiltradas={racoesFiltradas}
        buscaRacao={buscaRacao}
        setBuscaRacao={setBuscaRacao}
        selecionarRacao={selecionarRacao}
      />
    </KeyboardSafeScrollView>
  );
}
