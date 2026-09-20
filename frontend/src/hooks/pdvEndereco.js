export function criarPayloadEnderecoAdicional(clienteAtual, novoEndereco) {
  const enderecosAtuais = Array.isArray(clienteAtual?.enderecos_adicionais)
    ? clienteAtual.enderecos_adicionais
    : [];

  return {
    enderecos_adicionais: [...enderecosAtuais, { ...novoEndereco }],
  };
}
