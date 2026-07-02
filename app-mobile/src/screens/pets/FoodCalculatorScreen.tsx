import React, { useEffect, useMemo, useState } from "react";
import { Alert } from "react-native";

import { listarPets } from "../../services/pets.service";
import {
  adicionarAoCarrinho,
  calcularRacaoComProduto,
  compararRacoesCategoria,
  listarRacoesCadastradas,
  type RacaoCadastrada,
} from "../../services/shop.service";
import type { Pet } from "../../types";
import { calcularIdadeMeses } from "../../utils/format";
import { FoodCalculatorContent } from "./food-calculator/FoodCalculatorContent";
import type { FoodCalculatorSelectorKind, NivelAtividadeKey } from "./food-calculator/FoodCalculatorUtils";

interface Props {
  route: { params?: { pet?: Pet } };
}

export default function FoodCalculatorScreen({ route }: Props) {
  const petInicial = route.params?.pet;

  const [racoes, setRacoes] = useState<RacaoCadastrada[]>([]);
  const [buscaRacao, setBuscaRacao] = useState('');
  const [carregandoRacoes, setCarregandoRacoes] = useState(true);
  const [seletorAberto, setSeletorAberto] = useState<FoodCalculatorSelectorKind>(null);

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
  const [nivelAtividade, setNivelAtividade] = useState<NivelAtividadeKey>('normal');
  const [calculando, setCalculando] = useState(false);
  const [resultadoPrincipal, setResultadoPrincipal] = useState<any>(null);
  const [resultadoComparar, setResultadoComparar] = useState<any>(null);
  const racoesFiltradas = useMemo(() => {
    const termo = buscaRacao.trim().toLowerCase();
    if (!termo) return racoes;
    return racoes.filter((racao) =>
      `${racao.nome} ${racao.classificacao_racao || ''} ${racao.categoria_racao || ''}`
        .toLowerCase()
        .includes(termo)
    );
  }, [buscaRacao, racoes]);

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
    setBuscaRacao('');
    setResultadoPrincipal(null);
    setResultadoComparar(null);
  }

  return (
    <FoodCalculatorContent
      racoes={racoes}
      racoesFiltradas={racoesFiltradas}
      buscaRacao={buscaRacao}
      setBuscaRacao={setBuscaRacao}
      carregandoRacoes={carregandoRacoes}
      seletorAberto={seletorAberto}
      setSeletorAberto={setSeletorAberto}
      pets={pets}
      petSelecionado={petSelecionado}
      setPetSelecionado={setPetSelecionado}
      racaoSelecionada={racaoSelecionada}
      racaoComparar={racaoComparar}
      setRacaoComparar={setRacaoComparar}
      classificacoesDisponiveis={classificacoesDisponiveis}
      categoriaFiltro={categoriaFiltro}
      setCategoriaFiltro={setCategoriaFiltro}
      melhoresOpcoes={melhoresOpcoes}
      setMelhoresOpcoes={setMelhoresOpcoes}
      buscandoMelhor={buscandoMelhor}
      adicionando={adicionando}
      pesoPet={pesoPet}
      setPesoPet={setPesoPet}
      idadeMeses={idadeMeses}
      setIdadeMeses={setIdadeMeses}
      nivelAtividade={nivelAtividade}
      setNivelAtividade={setNivelAtividade}
      calculando={calculando}
      resultadoPrincipal={resultadoPrincipal}
      setResultadoComparar={setResultadoComparar}
      resultadoComparar={resultadoComparar}
      calcular={calcular}
      buscarMelhorOpcao={buscarMelhorOpcao}
      adicionarNoCarrinho={adicionarNoCarrinho}
      selecionarRacao={selecionarRacao}
    />
  );
}
