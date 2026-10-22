import ProdutosNovoDadosBasicosSection from "./ProdutosNovoDadosBasicosSection";
import ProdutosNovoEstruturaSection from "./ProdutosNovoEstruturaSection";
import ProdutosNovoPrecosSection from "./ProdutosNovoPrecosSection";
import { useNavigate } from "react-router-dom";

export default function ProdutosNovoCaracteristicasTab(props) {
  const {
    buscaPredecessor,
    camposEmEdicao,
    categoriasHierarquicas,
    departamentos,
    formData,
    imagens,
    handleBuscaPredecessorChange,
    handleChange,
    handleGerarCodigoBarras,
    handleGerarSKU,
    handleRemoverPredecessor,
    handleSelecionarPredecessor,
    handleToggleBuscaPredecessor,
    isEdicao,
    marcas,
    mostrarBuscaPredecessor,
    onNovoCatalogo,
    assistenteIAAviso,
    onPreencherComIA,
    preenchendoComIA,
    parseNumber,
    predecessorSelecionado,
    produtosBusca,
    setAbaAtiva,
    setCamposEmEdicao,
    setFormData,
  } = props;
  const navigate = useNavigate();
  const corrigirPendenciaIfood = (campo) => {
    if (
      ["config", "configuracao", "taxas", "ifood_config", "margin_config"].includes(campo) ||
      campo.startsWith("config.")
    ) {
      navigate("/ifood");
      return;
    }
    const aba = ["imagem_principal", "imagens", "image"].includes(campo)
      ? 2
      : ["estoque", "estoque_atual", "estoque_disponivel", "available_stock"].includes(campo)
        ? 3
        : 1;
    setAbaAtiva(aba);
    requestAnimationFrame(() => {
      const ids = {
        nome: "produto-campo-nome",
        codigo: "produto-campo-sku",
        sku: "produto-campo-sku",
        codigo_barras: "produto-campo-codigo-barras",
        unidade: "produto-campo-unidade",
        descricao_curta: "produto-campo-descricao",
        descricao_completa: "produto-campo-descricao",
        tipo: "produto-campo-tipo",
        preco_custo: "produto-preco-custo",
        preco_venda: "produto-preco-venda",
        preco_ifood: "produto-preco-ifood",
        preco_ifood_promo: "produto-preco-ifood-promo",
        preco_ifood_promo_inicio: "produto-ifood-promo-inicio",
        preco_ifood_promo_fim: "produto-ifood-promo-fim",
        ifood_pausado: "produto-ifood-pausado",
      };
      const alvo = document.getElementById(
        ids[campo] || (aba === 1 ? "produto-dados-basicos" : "produto-formulario-abas"),
      );
      const detalhes = alvo?.closest("details");
      if (detalhes) detalhes.open = true;
      alvo?.scrollIntoView({ block: "center", behavior: "smooth" });
      const controle = alvo?.matches("input,textarea,select,button")
        ? alvo
        : alvo?.querySelector("input,textarea,select,button");
      controle?.focus({ preventScroll: true });
    });
  };

  return (
    <div className="space-y-6">
      <div id="produto-dados-basicos">
        <ProdutosNovoDadosBasicosSection
          categoriasHierarquicas={categoriasHierarquicas}
          departamentos={departamentos}
          formData={formData}
          handleChange={handleChange}
          handleGerarCodigoBarras={handleGerarCodigoBarras}
          handleGerarSKU={handleGerarSKU}
          marcas={marcas}
          onNovoCatalogo={onNovoCatalogo}
          assistenteIAAviso={assistenteIAAviso}
          onPreencherComIA={onPreencherComIA}
          preenchendoComIA={preenchendoComIA}
        />
      </div>

      <ProdutosNovoPrecosSection
        camposEmEdicao={camposEmEdicao}
        formData={formData}
        handleChange={handleChange}
        imagens={imagens}
        onCorrigirIfood={corrigirPendenciaIfood}
        parseNumber={parseNumber}
        setCamposEmEdicao={setCamposEmEdicao}
      />

      <ProdutosNovoEstruturaSection
        buscaPredecessor={buscaPredecessor}
        formData={formData}
        handleBuscaPredecessorChange={handleBuscaPredecessorChange}
        handleChange={handleChange}
        handleRemoverPredecessor={handleRemoverPredecessor}
        handleSelecionarPredecessor={handleSelecionarPredecessor}
        handleToggleBuscaPredecessor={handleToggleBuscaPredecessor}
        isEdicao={isEdicao}
        mostrarBuscaPredecessor={mostrarBuscaPredecessor}
        predecessorSelecionado={predecessorSelecionado}
        produtosBusca={produtosBusca}
        setAbaAtiva={setAbaAtiva}
        setFormData={setFormData}
      />
    </div>
  );
}
