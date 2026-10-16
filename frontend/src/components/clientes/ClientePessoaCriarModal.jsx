import PessoaFormularioModal from "./PessoaFormularioModal";

const FLAG_POR_TIPO = {
  cliente: "is_cliente",
  fornecedor: "is_fornecedor",
  veterinario: "is_veterinario",
  funcionario: "is_funcionario",
};

function prefillParaTipo(tipoInicial) {
  const flag = FLAG_POR_TIPO[tipoInicial];
  return flag ? { [flag]: true } : undefined;
}

// Wrapper fino: a listagem de Pessoas ("+ Nova pessoa") usa a modal única de
// cadastro/edição (`PessoaFormularioModal`), só traduzindo `tipoInicial` (vindo do filtro
// de aba ativo) pro `prefill` que ela entende.
export default function ClientePessoaCriarModal({ aberto, tipoInicial, onCriado, onFechar }) {
  if (!aberto) return null;

  return (
    <PessoaFormularioModal
      onFechar={onFechar}
      onSalvo={onCriado}
      prefill={prefillParaTipo(tipoInicial)}
    />
  );
}
