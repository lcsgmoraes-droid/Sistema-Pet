export default function useProdutosNovoTributacao({ setFormData }) {
  const handleChangeTributacao = (campo, valor) => {
    setFormData((prev) => ({
      ...prev,
      tributacao: {
        ...prev.tributacao,
        [campo]: valor,
      },
    }));
  };

  const handlePersonalizarFiscal = () => {
    setFormData((prev) => ({
      ...prev,
      tributacao: {
        ...prev.tributacao,
        herdado_da_empresa: false,
      },
    }));
  };

  return {
    handleChangeTributacao,
    handlePersonalizarFiscal,
  };
}
