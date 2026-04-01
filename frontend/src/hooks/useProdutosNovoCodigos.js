import { gerarCodigoBarras, gerarSKU } from '../api/produtos';

export default function useProdutosNovoCodigos({ formData, setFormData }) {
  const handleGerarSKU = async () => {
    try {
      const response = await gerarSKU('PROD');
      setFormData((prev) => ({
        ...prev,
        sku: response.data.sku,
        codigo: response.data.sku,
      }));
      alert('SKU gerado com sucesso!');
    } catch (error) {
      console.error('Erro ao gerar SKU:', error);
      alert('Erro ao gerar SKU');
    }
  };

  const handleGerarCodigoBarras = async () => {
    if (!formData.sku) {
      alert('Gere ou informe um SKU primeiro!');
      return;
    }

    try {
      const response = await gerarCodigoBarras(formData.sku);
      setFormData((prev) => ({
        ...prev,
        codigo_barras: response.data.codigo_barras,
      }));
      alert('Código de barras gerado com sucesso!');
    } catch (error) {
      console.error('Erro ao gerar código de barras:', error);
      alert('Erro ao gerar código de barras');
    }
  };

  return {
    handleGerarSKU,
    handleGerarCodigoBarras,
  };
}
