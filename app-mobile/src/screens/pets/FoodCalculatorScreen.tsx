import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  StyleSheet,
  ScrollView,
  ActivityIndicator,
  Alert,
  Modal,
  FlatList,
  Image,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { calcularRacaoComProduto, compararRacoesCategoria, listarRacoesCadastradas, RacaoCadastrada, adicionarAoCarrinho } from '../../services/shop.service';
import { listarPets } from '../../services/pets.service';
import { Pet } from '../../types';
import { CORES, ESPACO, FONTE, RAIO, SOMBRA } from '../../theme';
import { formatarMoeda, calcularIdadeMeses } from '../../utils/format';

const NIVEIS_ATIVIDADE = [
  { key: 'baixo', label: 'Baixo', emoji: '🛋️', descricao: 'Sedentário, pouca brincadeira' },
  { key: 'normal', label: 'Normal', emoji: '🚶', descricao: 'Brincadeiras normais por dia' },
  { key: 'alto', label: 'Alto', emoji: '🏃', descricao: 'Muito ativo, muito exercício' },
];

interface Props {
  route: { params?: { pet?: Pet } };
}

export default function FoodCalculatorScreen({ route }: Props) {
  const petInicial = route.params?.pet;

  const [racoes, setRacoes] = useState<RacaoCadastrada[]>([]);
  const [carregandoRacoes, setCarregandoRacoes] = useState(true);
  const [seletorAberto, setSeletorAberto] = useState<'principal' | 'comparar' | 'pet' | null>(null);

  // Pets do usuário
  const [pets, setPets] = useState<Pet[]>([]);
  const [petSelecionado, setPetSelecionado] = useState<Pet | null>(petInicial ?? null);

  // Produto selecionado principal
  const [racaoSelecionada, setRacaoSelecionada] = useState<RacaoCadastrada | null>(null);
  // Produto para comparar (opcional)
  const [racaoComparar, setRacaoComparar] = useState<RacaoCadastrada | null>(null);

  // Seletor de categoria
  const [classificacoesDisponiveis, setClassificacoesDisponiveis] = useState<string[]>([]);
  const [categoriaFiltro, setCategoriaFiltro] = useState<string | null>(null);
  const [melhoresOpcoes, setMelhoresOpcoes] = useState<any[]>([]);
  const [buscandoMelhor, setBuscandoMelhor] = useState(false);
  const [adicionando, setAdicionando] = useState<Record<number, boolean>>({});

  const [pesoPet, setPesoPet] = useState(
    petInicial?.peso ? String(petInicial.peso) : ''
  );
  const [idadeMeses, setIdadeMeses] = useState(() => {
    if (petInicial?.idade_aproximada) return String(petInicial.idade_aproximada);
    const calculado = calcularIdadeMeses(petInicial?.data_nascimento);
    return calculado ? String(calculado) : '';
  });
  const [nivelAtividade, setNivelAtividade] = useState<'baixo' | 'normal' | 'alto'>('normal');
  const [calculando, setCalculando] = useState(false);
  const [resultadoPrincipal, setResultadoPrincipal] = useState<any>(null);
  const [resultadoComparar, setResultadoComparar] = useState<any>(null);

  useEffect(() => {
    carregarRacoes();
    listarPets().then(setPets).catch(() => {});
  }, []);

  async function carregarRacoes() {
    setCarregandoRacoes(true);
    try {
      const lista = await listarRacoesCadastradas();
      setRacoes(lista);
      const classifs = Array.from(
        new Set(lista.map((r) => r.classificacao_racao).filter(Boolean))
      ) as string[];
      setClassificacoesDisponiveis(classifs);
      if (lista.length === 0) {
        Alert.alert(
          'Nenhuma ração cadastrada',
          'Nenhum produto de ração encontrado com dados de embalagem cadastrados. ' +
          'Acesse o sistema web, vá em Produtos → aba Ração e preencha o Peso da Embalagem.',
          [{ text: 'OK' }]
        );
      }
    } catch {
      Alert.alert('Erro', 'Não foi possível carregar as rações disponíveis.');
    } finally {
      setCarregandoRacoes(false);
    }
  }

  async function calcular() {
    const peso = parseFloat(pesoPet);
    if (!pesoPet || isNaN(peso) || peso <= 0) {
      Alert.alert('Campo obrigatório', 'Informe o peso do pet em kg.');
      return;
    }

    setCalculando(true);
    setResultadoPrincipal(null);
    setResultadoComparar(null);

    try {
      // Calcular para a ração principal
      const res1 = await calcularRacaoComProduto({
        produto_id: racaoSelecionada?.id ?? null,
        peso_pet_kg: peso,
        idade_meses: idadeMeses ? parseInt(idadeMeses) : null,
        nivel_atividade: nivelAtividade,
      });
      setResultadoPrincipal(res1);

      // Se tiver ração para comparar, calcular também
      if (racaoComparar) {
        const res2 = await calcularRacaoComProduto({
          produto_id: racaoComparar.id,
          peso_pet_kg: peso,
          idade_meses: idadeMeses ? parseInt(idadeMeses) : null,
          nivel_atividade: nivelAtividade,
        });
        setResultadoComparar(res2);
      }
    } catch (err: any) {
      Alert.alert('Erro', err?.response?.data?.detail || 'Não foi possível calcular.');
    } finally {
      setCalculando(false);
    }
  }

  async function buscarMelhorOpcao(classif: string | null) {
    const peso = parseFloat(pesoPet);
    if (!pesoPet || isNaN(peso) || peso <= 0) {
      Alert.alert('Peso necessário', 'Preencha o peso do pet antes de buscar a melhor opção.');
      return;
    }
    setBuscandoMelhor(true);
    setMelhoresOpcoes([]);
    try {
      const comp = await compararRacoesCategoria({
        peso_pet_kg: peso,
        idade_meses: idadeMeses ? parseInt(idadeMeses) : null,
        nivel_atividade: nivelAtividade,
        classificacao: classif,
      });
      // Top 3 ordenado por menor custo diário
      const top3 = [...comp.racoes]
        .sort((a: any, b: any) => a.custo_por_dia - b.custo_por_dia)
        .slice(0, 3)
        .map((r: any) => ({ ...r, categoria: classif }));
      setMelhoresOpcoes(top3);
    } catch {
      Alert.alert('Erro', 'Não foi possível comparar as rações.');
    } finally {
      setBuscandoMelhor(false);
    }
  }

  async function adicionarNoCarrinho(produto_id: number) {
    if (!produto_id) return;
    setAdicionando((prev) => ({ ...prev, [produto_id]: true }));
    try {
      await adicionarAoCarrinho(produto_id, 1);
      Alert.alert('Adicionado! 🛒', 'Ração adicionada ao carrinho.');
    } catch {
      Alert.alert('Erro', 'Não foi possível adicionar ao carrinho.');
    } finally {
      setAdicionando((prev) => ({ ...prev, [produto_id]: false }));
    }
  }

  function selecionarRacao(racao: RacaoCadastrada) {
    if (seletorAberto === 'principal') {
      setRacaoSelecionada(racao);
    } else {
      setRacaoComparar(racao);
    }
    setSeletorAberto(null);
    setResultadoPrincipal(null);
    setResultadoComparar(null);
  }

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content}>
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

      {/* Modal seletor de ração / pet */}
      <Modal
        visible={seletorAberto !== null}
        animationType="slide"
        presentationStyle="pageSheet"
        onRequestClose={() => setSeletorAberto(null)}
      >
        <View style={styles.modal}>
          <View style={styles.modalHeader}>
            <Text style={styles.modalTitulo}>
              {seletorAberto === 'pet' ? 'Selecionar pet' : seletorAberto === 'principal' ? 'Selecionar ração' : 'Selecionar para comparar'}
            </Text>
            <TouchableOpacity onPress={() => setSeletorAberto(null)}>
              <Ionicons name="close" size={24} color={CORES.texto} />
            </TouchableOpacity>
          </View>

          {/* Lista de pets */}
          {seletorAberto === 'pet' && (
            pets.length === 0 ? (
              <View style={styles.modalVazio}>
                <Text style={{ fontSize: 40 }}>🐾</Text>
                <Text style={styles.modalVazioTexto}>Nenhum pet cadastrado.</Text>
                <Text style={styles.modalVazioSub}>Vá em Pets e adicione seu pet com peso e idade.</Text>
              </View>
            ) : (
              <FlatList
                data={pets}
                keyExtractor={(p) => String(p.id)}
                contentContainerStyle={{ padding: ESPACO.md }}
                renderItem={({ item }) => (
                  <TouchableOpacity
                    style={styles.racaoItem}
                    onPress={() => {
                      setPetSelecionado(item);
                      if (item.peso) setPesoPet(String(item.peso));
                      // Usa idade_aproximada; se ausente, calcula a partir da data_nascimento
                      if (item.idade_aproximada) {
                        setIdadeMeses(String(item.idade_aproximada));
                      } else {
                        const calc = calcularIdadeMeses(item.data_nascimento);
                        setIdadeMeses(calc ? String(calc) : '');
                      }
                      setSeletorAberto(null);
                    }}
                  >
                    {item.foto_url ? (
                      <Image source={{ uri: item.foto_url }} style={styles.racaoFoto} resizeMode="cover" />
                    ) : (
                      <View style={[styles.racaoFoto, styles.racaoFotoPlaceholder]}>
                        <Text style={{ fontSize: 22 }}>🐾</Text>
                      </View>
                    )}
                    <View style={{ flex: 1 }}>
                      <Text style={styles.racaoNome}>{item.nome}</Text>
                      <Text style={styles.racaoSub}>
                        {item.especie ?? ''}
                        {item.peso ? ` · ${item.peso}kg` : ''}
                        {item.idade_aproximada
                          ? ` · ${item.idade_aproximada} meses`
                          : calcularIdadeMeses(item.data_nascimento)
                          ? ` · ${calcularIdadeMeses(item.data_nascimento)} meses`
                          : ''}
                      </Text>
                    </View>
                    <Ionicons name="chevron-forward" size={18} color={CORES.textoClaro} />
                  </TouchableOpacity>
                )}
              />
            )
          )}
          {/* Lista de rações */}
          {seletorAberto !== 'pet' && (
          racoes.length === 0 ? (
            <View style={styles.modalVazio}>
              <Text style={{ fontSize: 40 }}>🥫</Text>
              <Text style={styles.modalVazioTexto}>
                Nenhuma ração com peso de embalagem cadastrado.
              </Text>
              <Text style={styles.modalVazioSub}>
                Vá ao sistema ERP → Produtos → aba Ração e preencha o campo "Peso da Embalagem (kg)".
              </Text>
            </View>
          ) : (
            <FlatList
              data={racoes}
              keyExtractor={(r) => String(r.id)}
              contentContainerStyle={{ padding: ESPACO.md }}
              renderItem={({ item }) => (
                <TouchableOpacity
                  style={styles.racaoItem}
                  onPress={() => selecionarRacao(item)}
                >
                  {item.foto_url ? (
                    <Image source={{ uri: item.foto_url }} style={styles.racaoFoto} resizeMode="contain" />
                  ) : (
                    <View style={[styles.racaoFoto, styles.racaoFotoPlaceholder]}>
                      <Text style={{ fontSize: 22 }}>🥫</Text>
                    </View>
                  )}
                  <View style={{ flex: 1 }}>
                    <Text style={styles.racaoNome}>{item.nome}</Text>
                    <Text style={styles.racaoSub}>
                      Embalagem: {item.peso_embalagem}kg
                      {item.classificacao_racao ? ` · ${item.classificacao_racao}` : ''}
                    </Text>
                    <Text style={styles.racaoPreco}>{formatarMoeda(item.preco)}</Text>
                  </View>
                  <Ionicons name="chevron-forward" size={18} color={CORES.textoClaro} />
                </TouchableOpacity>
              )}
            />
          )
          )}
        </View>
      </Modal>
    </ScrollView>
  );
}

function Campo({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <View style={styles.campo}>
      <Text style={styles.label}>{label}</Text>
      {children}
    </View>
  );
}

function ResultadoCard({
  resultado,
  titulo,
  compact = false,
}: {
  resultado: any;
  titulo?: string | null;
  compact?: boolean;
}) {
  return (
    <View style={[styles.resultadoCard, compact && styles.resultadoCardCompact]}>
      {titulo && (
        <Text style={styles.resultadoNome} numberOfLines={2}>{titulo}</Text>
      )}
      <Text style={styles.resultadoTitulo}>Resultado</Text>

      <ItemResultado
        emoji="🥣"
        titulo="Qtd Diária"
        valor={`${resultado.quantidade_diaria_g}g`}
        destaque
      />

      {Number(resultado.duracao_dias) > 0 && (
        <ItemResultado
          emoji="📅"
          titulo="Duração"
          valor={`${resultado.duracao_dias} dias`}
        />
      )}

      {Number(resultado.custo_por_dia) > 0 && (
        <ItemResultado
          emoji="💸"
          titulo="Custo/dia"
          valor={formatarMoeda(resultado.custo_por_dia)}
        />
      )}

      {Number(resultado.custo_mensal) > 0 && (
        <ItemResultado
          emoji="📆"
          titulo="Custo/mês"
          valor={formatarMoeda(resultado.custo_mensal)}
        />
      )}

      {resultado.alerta && (
        <View style={styles.alerta}>
          <Text style={styles.alertaTexto}>⚠️ {resultado.alerta}</Text>
        </View>
      )}
    </View>
  );
}

function ItemResultado({
  emoji,
  titulo,
  valor,
  destaque = false,
  compact = false,
}: {
  emoji: string;
  titulo: string;
  valor: string;
  destaque?: boolean;
  compact?: boolean;
}) {
  return (
    <View style={[styles.itemResultado, destaque && styles.itemDestaque, compact && styles.itemResultadoCompact]}>
      <Text style={[styles.itemEmoji, compact && styles.itemEmojiCompact]}>{emoji}</Text>
      <View style={{ flex: 1 }}>
        <Text style={[styles.itemTitulo, compact && styles.itemTituloCompact]}>{titulo}</Text>
        <Text style={[styles.itemValor, destaque && styles.itemValorDestaque, compact && styles.itemValorCompact]}>{valor}</Text>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: CORES.fundo },
  content: { padding: ESPACO.lg },
  header: { alignItems: 'center', marginBottom: ESPACO.lg },
  emoji: { fontSize: 48, marginBottom: ESPACO.sm },
  titulo: { fontSize: FONTE.titulo, fontWeight: 'bold', color: CORES.texto },
  subtitulo: {
    fontSize: FONTE.normal,
    color: CORES.textoSecundario,
    textAlign: 'center',
    marginTop: ESPACO.xs,
  },
  card: {
    backgroundColor: CORES.superficie,
    borderRadius: RAIO.lg,
    padding: ESPACO.lg,
    marginBottom: ESPACO.lg,
    ...SOMBRA,
  },
  campo: { marginBottom: ESPACO.md },
  label: { fontSize: FONTE.normal, fontWeight: '600', color: CORES.texto, marginBottom: ESPACO.xs },
  input: {
    borderWidth: 1,
    borderColor: CORES.borda,
    borderRadius: RAIO.md,
    paddingHorizontal: ESPACO.md,
    paddingVertical: ESPACO.sm + 2,
    fontSize: FONTE.media,
    color: CORES.texto,
    backgroundColor: CORES.fundo,
  },
  seletorBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    borderWidth: 1,
    borderColor: CORES.borda,
    borderRadius: RAIO.md,
    paddingHorizontal: ESPACO.md,
    paddingVertical: ESPACO.sm + 2,
    backgroundColor: CORES.fundo,
    gap: ESPACO.sm,
  },
  seletorNome: { fontSize: FONTE.normal, fontWeight: '600', color: CORES.texto },
  seletorSub: { fontSize: FONTE.pequena, color: CORES.textoSecundario },
  seletorPlaceholder: { flex: 1, fontSize: FONTE.normal, color: CORES.textoClaro },
  nivelCard: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: ESPACO.sm,
    borderRadius: RAIO.md,
    borderWidth: 1,
    borderColor: CORES.borda,
    marginBottom: ESPACO.xs,
    gap: ESPACO.sm,
  },
  nivelAtivo: { borderColor: CORES.primario, backgroundColor: CORES.primarioClaro },
  nivelEmoji: { fontSize: 22 },
  nivelLabel: { fontSize: FONTE.normal, fontWeight: '600', color: CORES.texto },
  nivelLabelAtivo: { color: CORES.primario },
  nivelDesc: { fontSize: FONTE.pequena, color: CORES.textoSecundario },
  botao: {
    backgroundColor: CORES.primario,
    borderRadius: RAIO.md,
    paddingVertical: ESPACO.md,
    alignItems: 'center',
    marginTop: ESPACO.sm,
  },
  botaoDesativado: { opacity: 0.7 },
  botaoTexto: { color: '#fff', fontSize: FONTE.media, fontWeight: 'bold' },

  // Resultado
  resultadoCard: {
    backgroundColor: CORES.superficie,
    borderRadius: RAIO.lg,
    padding: ESPACO.lg,
    marginBottom: ESPACO.lg,
    ...SOMBRA,
  },
  resultadoCardCompact: { flex: 1, marginHorizontal: ESPACO.xs, padding: ESPACO.sm },
  resultadoTituloCompact: { fontSize: FONTE.normal, marginBottom: ESPACO.xs },
  itemResultadoCompact: { padding: ESPACO.xs, gap: ESPACO.xs },
  itemEmojiCompact: { fontSize: 14 },
  itemTituloCompact: { fontSize: 10 },
  itemValorCompact: { fontSize: FONTE.normal },
  resultadoNome: {
    fontSize: FONTE.pequena,
    fontWeight: '600',
    color: CORES.primario,
    marginBottom: ESPACO.xs,
  },
  resultadoTitulo: {
    fontSize: FONTE.grande,
    fontWeight: 'bold',
    color: CORES.texto,
    marginBottom: ESPACO.md,
  },
  itemResultado: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: ESPACO.sm,
    borderRadius: RAIO.md,
    marginBottom: ESPACO.xs,
    gap: ESPACO.sm,
  },
  itemDestaque: { backgroundColor: CORES.primarioClaro },
  itemEmoji: { fontSize: 20 },
  itemTitulo: { fontSize: FONTE.pequena, color: CORES.textoSecundario },
  itemValor: { fontSize: FONTE.grande, fontWeight: 'bold', color: CORES.texto },
  itemValorDestaque: { color: CORES.primario },
  alerta: {
    backgroundColor: '#FFFBEB',
    borderRadius: RAIO.md,
    padding: ESPACO.sm,
    borderWidth: 1,
    borderColor: '#FDE68A',
    marginTop: ESPACO.sm,
  },
  alertaTexto: { fontSize: FONTE.normal, color: '#92400E' },

  // Categoria filter botões
  categoriaBotao: {
    paddingHorizontal: ESPACO.md,
    paddingVertical: ESPACO.xs + 2,
    borderRadius: RAIO.lg,
    borderWidth: 1.5,
    borderColor: CORES.borda,
    backgroundColor: CORES.fundo,
  },
  categoriaBotaoAtivo: {
    borderColor: CORES.primario,
    backgroundColor: CORES.primarioClaro,
  },
  categoriaBotaoTexto: { fontSize: FONTE.normal, color: CORES.textoSecundario, fontWeight: '500' },
  categoriaBotaoTextoAtivo: { color: CORES.primario, fontWeight: '700' },
  botaoSecundario: {
    borderWidth: 1.5,
    borderColor: CORES.primario,
    borderRadius: RAIO.md,
    paddingVertical: ESPACO.sm,
    alignItems: 'center',
    marginTop: ESPACO.xs,
  },
  botaoSecundarioTexto: { color: CORES.primario, fontSize: FONTE.normal, fontWeight: '700' },

  botaoAdicionar: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: ESPACO.xs,
    backgroundColor: CORES.primario,
    borderRadius: RAIO.md,
    paddingVertical: ESPACO.sm,
    marginTop: ESPACO.sm,
  },
  botaoAdicionarTexto: { color: '#fff', fontSize: FONTE.normal, fontWeight: '700' },

  // Comparativo
  comparativoContainer: { marginBottom: ESPACO.lg },
  comparativoTitulo: {
    fontSize: FONTE.grande,
    fontWeight: 'bold',
    color: CORES.texto,
    marginBottom: ESPACO.sm,
  },
  comparativoRow: { flexDirection: 'row', gap: ESPACO.sm },
  veredito: {
    backgroundColor: '#DCFCE7',
    borderRadius: RAIO.md,
    padding: ESPACO.md,
    marginTop: ESPACO.sm,
    borderWidth: 1,
    borderColor: '#BBF7D0',
  },
  vereditoTexto: { fontSize: FONTE.normal, color: '#166534', fontWeight: '600' },

  // Modal seletor
  modal: { flex: 1, backgroundColor: CORES.fundo },
  modalHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: ESPACO.lg,
    borderBottomWidth: 1,
    borderBottomColor: CORES.borda,
    backgroundColor: CORES.superficie,
  },
  modalTitulo: { fontSize: FONTE.grande, fontWeight: 'bold', color: CORES.texto },
  modalVazio: { flex: 1, justifyContent: 'center', alignItems: 'center', padding: ESPACO.xl, gap: ESPACO.md },
  modalVazioTexto: { fontSize: FONTE.grande, fontWeight: '600', color: CORES.texto, textAlign: 'center' },
  modalVazioSub: { fontSize: FONTE.normal, color: CORES.textoSecundario, textAlign: 'center' },
  racaoItem: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: CORES.superficie,
    borderRadius: RAIO.md,
    padding: ESPACO.md,
    marginBottom: ESPACO.sm,
    gap: ESPACO.md,
    ...SOMBRA,
  },
  racaoFoto: { width: 60, height: 60, borderRadius: RAIO.sm },
  racaoFotoPlaceholder: {
    backgroundColor: CORES.primarioClaro,
    justifyContent: 'center',
    alignItems: 'center',
  },
  racaoNome: { fontSize: FONTE.normal, fontWeight: '600', color: CORES.texto },
  racaoSub: { fontSize: FONTE.pequena, color: CORES.textoSecundario, marginTop: 2 },

  // Pet selector
  petSelecionadoRow: {
    flexDirection: 'row',
    alignItems: 'center',
    flex: 1,
    gap: ESPACO.sm,
  },
  petFotoMini: {
    width: 36,
    height: 36,
    borderRadius: 18,
  },
  petFotoMiniPlaceholder: {
    width: 36,
    height: 36,
    borderRadius: 18,
    backgroundColor: CORES.primarioClaro,
    justifyContent: 'center',
    alignItems: 'center',
  },
  racaoPreco: { fontSize: FONTE.normal, fontWeight: 'bold', color: CORES.primario, marginTop: 2 },
});
