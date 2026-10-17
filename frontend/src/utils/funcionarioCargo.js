// `cargo` de um funcionario vem em formatos diferentes dependendo do endpoint:
// string em GET /comissoes/configuracoes/funcionarios (tipos_cadastro juntados,
// ex. "cliente / funcionario"), objeto {id, nome, ...} em GET /funcionarios e
// GET /funcionarios/:id (CargoSimples, o cargo real de RH). Normaliza os dois
// formatos num texto exibivel, preferindo o nome real do cargo quando
// disponivel - sem isso, renderizar o objeto cru quebra o React.
export function formatarCargoFuncionario(cargo) {
  if (typeof cargo === "string") return cargo;
  if (cargo && typeof cargo === "object") return cargo.nome || "";
  return "";
}
