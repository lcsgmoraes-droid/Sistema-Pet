import type { AppProfileType, EcommerceDeliveryAddress, EcommerceUser } from "../../../types";

export interface RequiredDeliveryAddressFields {
  entregaNome: string;
  entregaEndereco: string;
  entregaNumero: string;
  entregaBairro: string;
  entregaCidade: string;
  entregaEstado: string;
}

export function formatCepInput(value: string): string {
  const numeros = value.replace(/\D/g, "");
  return numeros.length <= 5 ? numeros : `${numeros.slice(0, 5)}-${numeros.slice(5, 8)}`;
}

export function buildDefaultAddress(user: EcommerceUser | null): string | null {
  if (!user?.cidade) return null;
  const complementoEndereco = user.complemento ? ` - ${user.complemento}` : "";
  return `${user.endereco ?? ""}, ${user.numero ?? "s/n"}${complementoEndereco} - ${user.bairro ?? ""} - ${user.cidade}/${user.estado ?? ""}`;
}

export function buildDeliveryAddress(
  user: EcommerceUser | null,
  entregaDetalhada: EcommerceDeliveryAddress,
): string | null {
  if (!user?.usar_endereco_entrega_diferente || !entregaDetalhada.entrega_cidade) return null;
  const complementoEnderecoEntrega = entregaDetalhada.entrega_complemento
    ? ` - ${entregaDetalhada.entrega_complemento}`
    : "";
  return `${entregaDetalhada.entrega_endereco ?? ""}, ${entregaDetalhada.entrega_numero ?? "s/n"}${complementoEnderecoEntrega} - ${entregaDetalhada.entrega_bairro ?? ""} - ${entregaDetalhada.entrega_cidade}/${entregaDetalhada.entrega_estado ?? ""}`;
}

export function getCurrentProfile(user: EcommerceUser | null): AppProfileType {
  return user?.selected_profile ?? user?.perfil_operacional ?? "cliente";
}

export function hasRequiredDeliveryAddress(fields: RequiredDeliveryAddressFields): boolean {
  return Object.values(fields).every((valor) => valor.trim());
}
