import ProdutosNovoDadosBasicosSection from './ProdutosNovoDadosBasicosSection';
import ProdutosNovoEstruturaSection from './ProdutosNovoEstruturaSection';
import ProdutosNovoPrecosSection from './ProdutosNovoPrecosSection';

export default function ProdutosNovoCaracteristicasTab(props) {
  const {
    buscaPredecessor,
    camposEmEdicao,
    categoriasHierarquicas,
    departamentos,
    formData,
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
    parseNumber,
    predecessorSelecionado,
    produtosBusca,
    setAbaAtiva,
    setCamposEmEdicao,
    setFormData,
  } = props;

  return (
    <div className="space-y-6">
      <ProdutosNovoDadosBasicosSection
        categoriasHierarquicas={categoriasHierarquicas}
        departamentos={departamentos}
        formData={formData}
        handleChange={handleChange}
        handleGerarCodigoBarras={handleGerarCodigoBarras}
        handleGerarSKU={handleGerarSKU}
        marcas={marcas}
      />

      <ProdutosNovoPrecosSection
        camposEmEdicao={camposEmEdicao}
        formData={formData}
        handleChange={handleChange}
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
