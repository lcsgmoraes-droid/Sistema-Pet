import { useCallback, useEffect, useMemo, useState } from "react";
import toast from "react-hot-toast";
import {
  avaliarAptidaoRacao,
  camposIncompletosTexto,
  combinarProdutosComAptidao,
  escolherRacaoAptaPorTexto,
  extrairListaProdutos,
  formatarRacaoLabel,
  prepararProdutosComAptidao,
  produtoPareceRacao,
} from "../calculadoraRacaoUtils";
import {
  buscarRacoesNoCadastro,
  calcularRacao,
  carregarPetsCalculadora,
  carregarProdutosCalculadora,
  compararRacoesPorFiltros,
} from "./calculadoraRacaoApi";
import {
  calcularIdadeMeses,
  criarFormCalculadoraRacao,
  getEspecieRacaoPorPet,
  getPetLabel,
  montarParamsComparacao,
  montarPayloadCalculo,
  ordenarComparativoComPrincipal,
} from "./calculadoraRacaoState";
import useRacaoSearchEffect from "./useRacaoSearchEffect";

export default function useCalculadoraRacaoController() {
  const [produtos, setProdutos] = useState([]);
  const [produtosBuscaPrincipal, setProdutosBuscaPrincipal] = useState([]);
  const [produtosBuscaComparativo, setProdutosBuscaComparativo] = useState([]);
  const [pets, setPets] = useState([]);
  const [loading, setLoading] = useState(false);
  const [loadingBuscaPrincipal, setLoadingBuscaPrincipal] = useState(false);
  const [loadingBuscaComparativo, setLoadingBuscaComparativo] = useState(false);
  const [form, setForm] = useState(() => criarFormCalculadoraRacao());
  const [resultado, setResultado] = useState(null);
  const [comparativo, setComparativo] = useState([]);

  const produtosComAptidao = useMemo(() => prepararProdutosComAptidao(produtos), [produtos]);
  const produtosBuscaPrincipalComAptidao = useMemo(
    () => prepararProdutosComAptidao(produtosBuscaPrincipal),
    [produtosBuscaPrincipal],
  );
  const produtosBuscaComparativoComAptidao = useMemo(
    () => prepararProdutosComAptidao(produtosBuscaComparativo),
    [produtosBuscaComparativo],
  );
  const opcoesRacaoPrincipal = useMemo(
    () => combinarProdutosComAptidao(produtosBuscaPrincipalComAptidao, produtosComAptidao),
    [produtosBuscaPrincipalComAptidao, produtosComAptidao],
  );
  const opcoesRacaoComparativo = useMemo(
    () => combinarProdutosComAptidao(produtosBuscaComparativoComAptidao, produtosComAptidao),
    [produtosBuscaComparativoComAptidao, produtosComAptidao],
  );
  const resumoAptidao = useMemo(() => {
    const aptas = produtosComAptidao.filter((produto) => produto.aptidao.apta);
    return {
      aptas: aptas.length,
      incompletas: produtosComAptidao.length - aptas.length,
    };
  }, [produtosComAptidao]);

  const carregarProdutos = useCallback(async () => {
    try {
      const data = await carregarProdutosCalculadora();
      const listaProdutos = extrairListaProdutos(data);
      const racoes = listaProdutos.filter((produto) => produtoPareceRacao(produto));
      const aptas = racoes.filter((produto) => avaliarAptidaoRacao(produto).apta);

      setProdutos(racoes);

      if (racoes.length === 0 && listaProdutos.length > 0) {
        toast.error(
          `${listaProdutos.length} produtos encontrados, mas nenhum parece estar marcado como racao. ` +
            'Edite os produtos de racao e preencha a aba "Racao".',
          { duration: 6000 },
        );
      } else if (racoes.length === 0) {
        toast.error("Nenhum produto encontrado. Cadastre produtos primeiro.");
      } else if (aptas.length === 0) {
        toast("Racoes encontradas, mas nenhuma esta completa para analise.");
      }
    } catch (error) {
      console.error("Erro ao carregar produtos:", error);
      toast.error(`Erro ao carregar produtos: ${error.response?.data?.detail || error.message}`);
    }
  }, []);

  const carregarPets = useCallback(async () => {
    try {
      setPets(await carregarPetsCalculadora());
    } catch (error) {
      console.error("Erro ao carregar pets:", error);
    }
  }, []);

  useEffect(() => {
    void carregarProdutos();
    void carregarPets();
  }, [carregarProdutos, carregarPets]);

  useRacaoSearchEffect({
    contextoErro: "Erro ao buscar racoes no cadastro:",
    produtoId: form.produto_id,
    setLoading: setLoadingBuscaPrincipal,
    setProdutos: setProdutosBuscaPrincipal,
    termo: form.produto_nome,
  });

  useRacaoSearchEffect({
    contextoErro: "Erro ao buscar racoes para comparacao:",
    produtoId: form.produto_comparar_id,
    setLoading: setLoadingBuscaComparativo,
    setProdutos: setProdutosBuscaComparativo,
    termo: form.produto_comparar_nome,
  });

  const setCampo = useCallback((campo, valor) => {
    setForm((prev) => ({ ...prev, [campo]: valor }));
  }, []);

  const buscarProdutoComAptidao = useCallback(
    (produtoId) =>
      combinarProdutosComAptidao(
        produtosComAptidao,
        produtosBuscaPrincipalComAptidao,
        produtosBuscaComparativoComAptidao,
      ).find((produto) => String(produto.id) === String(produtoId)),
    [produtosBuscaComparativoComAptidao, produtosBuscaPrincipalComAptidao, produtosComAptidao],
  );

  const resolverRacaoPrincipalDigitada = useCallback(async () => {
    const texto = String(form.produto_nome || "").trim();
    let produto = escolherRacaoAptaPorTexto(texto, opcoesRacaoPrincipal, produtosComAptidao);
    if (produto) return produto;
    if (texto.length < 2) return null;

    try {
      setLoadingBuscaPrincipal(true);
      const racoes = await buscarRacoesNoCadastro(texto);
      setProdutosBuscaPrincipal(racoes);
      produto = escolherRacaoAptaPorTexto(
        texto,
        prepararProdutosComAptidao(racoes),
        opcoesRacaoPrincipal,
        produtosComAptidao,
      );
      return produto || null;
    } catch (error) {
      console.error("Erro ao resolver racao digitada:", error);
      return null;
    } finally {
      setLoadingBuscaPrincipal(false);
    }
  }, [form.produto_nome, opcoesRacaoPrincipal, produtosComAptidao]);

  const validarProdutoApto = useCallback(
    (produtoId, contexto = "racao") => {
      const produto = buscarProdutoComAptidao(produtoId);
      if (!produto) {
        toast.error(`Selecione uma ${contexto} apta para analise.`);
        return false;
      }
      if (!produto.aptidao.apta) {
        toast.error(camposIncompletosTexto(produto.aptidao.faltantes));
        return false;
      }
      return true;
    },
    [buscarProdutoComAptidao],
  );

  const selecionarRacaoPrincipal = useCallback((produto) => {
    if (!produto.aptidao.apta) {
      toast.error(camposIncompletosTexto(produto.aptidao.faltantes));
      return;
    }
    setForm((prev) => ({
      ...prev,
      produto_id: produto.id,
      produto_nome: formatarRacaoLabel(produto),
      categoria_racao: produto.categoria_racao || "",
    }));
  }, []);

  const selecionarRacaoComparativo = useCallback((produto) => {
    if (!produto.aptidao.apta) {
      toast.error(camposIncompletosTexto(produto.aptidao.faltantes));
      return;
    }
    setForm((prev) => ({
      ...prev,
      produto_comparar_id: produto.id,
      produto_comparar_nome: formatarRacaoLabel(produto),
      classificacao: "",
    }));
  }, []);

  const alterarBuscaRacaoPrincipal = useCallback(
    (valor) => {
      const produtoExato = escolherRacaoAptaPorTexto(valor, opcoesRacaoPrincipal);
      setForm((prev) => ({
        ...prev,
        produto_id: produtoExato?.aptidao.apta ? produtoExato.id : "",
        produto_nome: valor,
        categoria_racao: produtoExato?.aptidao.apta ? produtoExato.categoria_racao || "" : "",
      }));
    },
    [opcoesRacaoPrincipal],
  );

  const alterarBuscaRacaoComparativo = useCallback(
    (valor) => {
      const produtoExato = escolherRacaoAptaPorTexto(valor, opcoesRacaoComparativo);
      setForm((prev) => ({
        ...prev,
        produto_comparar_id: produtoExato?.aptidao.apta ? produtoExato.id : "",
        produto_comparar_nome: valor,
        classificacao: "",
      }));
    },
    [opcoesRacaoComparativo],
  );

  const selecionarPet = useCallback(
    (petId) => {
      const petSelecionado = pets.find((pet) => pet.id === parseInt(petId));
      if (!petSelecionado) {
        setForm((prev) => ({ ...prev, pet_id: "", peso_pet_kg: "", idade_meses: "" }));
        return;
      }

      setForm((prev) => ({
        ...prev,
        pet_id: String(petId),
        pet_nome: getPetLabel(petSelecionado),
        peso_pet_kg: petSelecionado.peso || "",
        idade_meses: calcularIdadeMeses(petSelecionado.data_nascimento),
        especies: getEspecieRacaoPorPet(petSelecionado, prev.especies),
      }));
      toast.success(`Pet ${petSelecionado.nome} selecionado!`);
    },
    [pets],
  );

  const alterarPetNome = useCallback(
    (nomePet) => {
      setCampo("pet_nome", nomePet);
      const petEncontrado = pets.find((pet) => getPetLabel(pet) === nomePet);
      if (petEncontrado) selecionarPet(petEncontrado.id);
    },
    [pets, selecionarPet, setCampo],
  );

  const calcular = useCallback(async () => {
    if (!form.peso_pet_kg) {
      toast.error("Informe o peso do pet");
      return;
    }

    let produtoSelecionado = form.produto_id ? buscarProdutoComAptidao(form.produto_id) : null;
    if (!produtoSelecionado && form.produto_nome) {
      produtoSelecionado = await resolverRacaoPrincipalDigitada();
    }

    const produtoIdCalculo = produtoSelecionado?.id ? parseInt(produtoSelecionado.id) : null;
    const categoriaRacaoCalculo = produtoSelecionado?.categoria_racao || form.categoria_racao;

    if (!produtoIdCalculo) {
      toast.error("Selecione uma racao apta para analise.");
      return;
    }
    if (!produtoSelecionado.aptidao.apta) {
      toast.error(camposIncompletosTexto(produtoSelecionado.aptidao.faltantes));
      return;
    }
    if (categoriaRacaoCalculo === "filhote" && !form.idade_meses) {
      toast.error("Idade e obrigatoria para racoes de filhote!");
      return;
    }

    if (String(form.produto_id) !== String(produtoIdCalculo)) {
      setForm((prev) => ({
        ...prev,
        produto_id: produtoIdCalculo,
        produto_nome: formatarRacaoLabel(produtoSelecionado),
        categoria_racao: categoriaRacaoCalculo || "",
      }));
    }

    try {
      setLoading(true);
      const data = await calcularRacao(montarPayloadCalculo(form, produtoIdCalculo));
      setResultado(data);
      setComparativo([]);
      toast.success("Calculo realizado!");
    } catch (error) {
      console.error("Erro:", error);
      toast.error(error.response?.data?.detail || "Erro ao calcular");
    } finally {
      setLoading(false);
    }
  }, [buscarProdutoComAptidao, form, resolverRacaoPrincipalDigitada]);

  const compararRacoes = useCallback(async () => {
    if (!form.peso_pet_kg) {
      toast.error("Informe o peso do pet");
      return;
    }
    if (form.produto_id && !validarProdutoApto(form.produto_id)) return;
    if (form.produto_comparar_nome && !form.produto_comparar_id) {
      toast.error("Selecione uma racao de comparacao apta ou limpe o campo.");
      return;
    }
    if (
      form.produto_comparar_id &&
      !validarProdutoApto(form.produto_comparar_id, "racao de comparacao")
    ) {
      return;
    }

    try {
      setLoading(true);
      if (form.produto_comparar_id) {
        const racaoComparar = await calcularRacao(
          montarPayloadCalculo(form, form.produto_comparar_id),
        );
        if (!form.produto_id) {
          setComparativo([racaoComparar]);
          toast.success("Mostrando calculo da racao selecionada");
          return;
        }

        const racaoPrincipal = await calcularRacao(montarPayloadCalculo(form, form.produto_id));
        const racoes =
          racaoPrincipal.produto_id === racaoComparar.produto_id
            ? [racaoPrincipal]
            : [racaoPrincipal, racaoComparar];
        setComparativo(racoes);
        toast.success(
          racoes.length === 1
            ? "Mostrando calculo da racao selecionada"
            : "Comparando 2 racoes selecionadas!",
        );
        return;
      }

      let todasRacoes = await compararRacoesPorFiltros(montarParamsComparacao(form));
      if (form.produto_id) {
        const racaoPrincipal = await calcularRacao(montarPayloadCalculo(form, form.produto_id));
        todasRacoes = ordenarComparativoComPrincipal(todasRacoes, form.produto_id, racaoPrincipal);
      }

      setComparativo(todasRacoes.slice(0, 10));
      if (todasRacoes.length === 0) {
        toast.error("Nenhuma racao encontrada com esses filtros. Tente outros criterios.");
      }
    } catch (error) {
      console.error("Erro:", error);
      toast.error(error.response?.data?.detail || "Erro ao comparar");
    } finally {
      setLoading(false);
    }
  }, [form, validarProdutoApto]);

  return {
    form,
    pets,
    loading,
    loadingBuscaPrincipal,
    loadingBuscaComparativo,
    resultado,
    comparativo,
    opcoesRacaoPrincipal,
    opcoesRacaoComparativo,
    resumoAptidao,
    setCampo,
    alterarPetNome,
    selecionarPet,
    selecionarRacaoPrincipal,
    selecionarRacaoComparativo,
    alterarBuscaRacaoPrincipal,
    alterarBuscaRacaoComparativo,
    limparRacaoPrincipal: () =>
      setForm((prev) => ({ ...prev, produto_id: "", produto_nome: "", categoria_racao: "" })),
    limparRacaoComparativo: () =>
      setForm((prev) => ({ ...prev, produto_comparar_id: "", produto_comparar_nome: "" })),
    alterarClassificacao: (classificacao) =>
      setForm((prev) => ({
        ...prev,
        classificacao,
        produto_comparar_id: "",
        produto_comparar_nome: "",
      })),
    limparClassificacao: () => setCampo("classificacao", ""),
    calcular,
    compararRacoes,
  };
}
