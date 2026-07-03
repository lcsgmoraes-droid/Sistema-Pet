export type PagamentoTipo = "pix" | "debito" | "credito" | "";
export type ModoRecebimento = "retirada" | "entrega";
export type TipoRetirada = "proprio" | "terceiro";

export type CartAddressFields = {
  cep: string;
  rua: string;
  numero: string;
  complemento: string;
  bairro: string;
  cidade: string;
  estado: string;
};

export function montarEnderecoInicial(user: any): CartAddressFields {
  const entregaDetalhada = user?.endereco_entrega_detalhado;
  const usarEntregaDetalhada = Boolean(
    user?.usar_endereco_entrega_diferente && entregaDetalhada?.entrega_cidade,
  );

  if (usarEntregaDetalhada) {
    return {
      cep: entregaDetalhada?.entrega_cep ?? "",
      rua: entregaDetalhada?.entrega_endereco ?? "",
      numero: entregaDetalhada?.entrega_numero ?? "",
      complemento: entregaDetalhada?.entrega_complemento ?? "",
      bairro: entregaDetalhada?.entrega_bairro ?? "",
      cidade: entregaDetalhada?.entrega_cidade ?? "",
      estado: entregaDetalhada?.entrega_estado ?? "",
    };
  }

  return {
    cep: user?.cep ?? "",
    rua: user?.endereco ?? "",
    numero: user?.numero ?? "",
    complemento: user?.complemento ?? "",
    bairro: user?.bairro ?? "",
    cidade: user?.cidade ?? "",
    estado: user?.estado ?? "",
  };
}

export function formatarEnderecoEntrega(endereco: CartAddressFields): string {
  return `${endereco.rua}, ${endereco.numero}${endereco.complemento ? ` ${endereco.complemento}` : ""} - ${
    endereco.bairro
  } - ${endereco.cidade}/${endereco.estado} - CEP: ${endereco.cep}`;
}

export function formatarEnderecoSalvo(
  endereco: CartAddressFields,
): string | null {
  if (!endereco.cidade) return null;

  return `${endereco.rua}${endereco.numero ? `, ${endereco.numero}` : ""}${
    endereco.complemento ? ` - ${endereco.complemento}` : ""
  } - ${endereco.bairro} - ${endereco.cidade}/${endereco.estado}`;
}

export function formatarCep(value: string) {
  const numeros = value.replace(/\D/g, "");
  return {
    numeros,
    cep:
      numeros.length <= 5
        ? numeros
        : `${numeros.slice(0, 5)}-${numeros.slice(5, 8)}`,
  };
}

export function buildPagamentoLabel(
  pagamentoTipo: PagamentoTipo,
  pagamentoBandeira: string,
  pagamentoParcelas: number,
): string {
  if (pagamentoTipo === "pix") return "PIX";
  if (pagamentoTipo === "debito") return `Débito ${pagamentoBandeira}`;
  if (pagamentoTipo === "credito")
    return `Crédito ${pagamentoBandeira} ${pagamentoParcelas}x`;
  return "";
}

export function buildRecebimentoLabel({
  modo,
  tipoRetirada,
  isDrive,
  enderecoFormatado,
}: {
  modo: ModoRecebimento;
  tipoRetirada: TipoRetirada;
  isDrive: boolean;
  enderecoFormatado?: string;
}) {
  if (modo === "entrega") return `Entrega em: ${enderecoFormatado}`;
  if (tipoRetirada === "terceiro")
    return "Retirada por terceiro (senha será gerada)";
  return isDrive
    ? "Drive-thru (aguardar no carro)"
    : "Retirada na loja por mim";
}
