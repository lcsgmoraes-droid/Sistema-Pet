import PessoaFormularioModal from "../clientes/PessoaFormularioModal";
import { validarCpf } from "../../utils/cpf";

function inferirPrefill(valorBuscaInicial) {
  const base = { is_cliente: true, tipo_pessoa: "PF", origem_cliente: "loja_fisica" };

  const texto = String(valorBuscaInicial || "").trim();
  if (!texto) return base;

  const digitos = texto.replace(/\D/g, "");
  const temLetras = /[a-zA-ZÀ-ÿ]/.test(texto);

  if (texto.includes("@")) return { ...base, email: texto };
  if (temLetras) return { ...base, nome: texto };
  if (digitos.length === 11 && validarCpf(digitos)) return { ...base, cpf: texto };
  if (digitos.length >= 10) return { ...base, celular: texto };
  if (digitos.length > 0) return { ...base, nome: texto };

  return base;
}

// Wrapper fino: cadastro rápido de cliente no PDV (e no painel de orçamentos de grupo,
// que reusa este mesmo componente) usa a modal única de Pessoa, pré-marcada como cliente
// PF com o termo buscado já encaixado no campo mais provável.
export default function ModalCadastroCliente({ onClose, onClienteCriado, valorBuscaInicial }) {
  return (
    <PessoaFormularioModal
      onFechar={onClose}
      onSalvo={onClienteCriado}
      prefill={inferirPrefill(valorBuscaInicial)}
    />
  );
}
