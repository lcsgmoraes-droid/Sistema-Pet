import { alterarQuantidadeDoses, criarRegraRecorrencia } from "../utils/produtoRecorrencia";

export default function useProdutosNovoRecorrencia({ formData, handleChange }) {
  const atualizarLista = (atualizador) => {
    const atual = formData.protocolos_recorrencia || [];
    handleChange("protocolos_recorrencia", atualizador(atual));
  };

  const adicionarRegraRecorrencia = (tipo) => {
    atualizarLista((atual) => [...atual, criarRegraRecorrencia(tipo)]);
  };

  const atualizarRegraRecorrencia = (index, campo, valor) => {
    atualizarLista((atual) =>
      atual.map((regra, regraIndex) =>
        regraIndex === index ? { ...regra, [campo]: valor } : regra,
      ),
    );
  };

  const atualizarDoseRecorrencia = (regraIndex, doseIndex, valor) => {
    atualizarLista((atual) =>
      atual.map((regra, index) =>
        index === regraIndex
          ? {
              ...regra,
              doses: regra.doses.map((dose, indexDose) =>
                indexDose === doseIndex ? { ...dose, dias_desde_inicio: valor } : dose,
              ),
            }
          : regra,
      ),
    );
  };

  const atualizarQuantidadeDosesRecorrencia = (index, quantidade) => {
    atualizarLista((atual) =>
      atual.map((regra, regraIndex) =>
        regraIndex === index ? alterarQuantidadeDoses(regra, quantidade) : regra,
      ),
    );
  };

  const removerRegraRecorrencia = (index) => {
    atualizarLista((atual) => atual.filter((_, regraIndex) => regraIndex !== index));
  };

  return {
    adicionarRegraRecorrencia,
    atualizarDoseRecorrencia,
    atualizarQuantidadeDosesRecorrencia,
    atualizarRegraRecorrencia,
    removerRegraRecorrencia,
  };
}
