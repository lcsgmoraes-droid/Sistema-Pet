import BuscaEntidade from "../BuscaEntidade/BuscaEntidade";
import { obterCodigoPessoaPublico } from "../../../utils/codigosPublicos";
import { formatarEnderecoPrincipalCliente } from "../../../utils/enderecoCliente";
import useBuscaPessoaResultados from "./useBuscaPessoaResultados";

export default function BuscaPessoa({
  mostrarEndereco = false,
  suggestions,
  autoSearch,
  searchParams,
  loading,
  error,
  ...props
}) {
  const resultados = useBuscaPessoaResultados({
    value: props.value,
    minChars: props.minChars ?? 1,
    searchParams,
    enabled: autoSearch ?? (suggestions === undefined && typeof props.onSelect === "function"),
  });
  return (
    <BuscaEntidade
      tipo="pessoa"
      placeholder="Código, nome, CPF/CNPJ ou telefone..."
      {...props}
      suggestions={suggestions ?? resultados.suggestions}
      loading={loading ?? resultados.loading}
      error={error || resultados.error}
      renderDefault={(pessoa, busca) => {
        const codigo = obterCodigoPessoaPublico(pessoa);
        const digitos = String(busca).replace(/\D/g, "");
        const contato = (pessoa.contatos_adicionais || []).find(
          (item) =>
            (digitos.length >= 4 &&
              String(item.numero || "")
                .replace(/\D/g, "")
                .includes(digitos)) ||
            (String(busca).trim().length >= 2 &&
              String(item.vinculo || "")
                .toLocaleLowerCase("pt-BR")
                .includes(String(busca).trim().toLocaleLowerCase("pt-BR"))),
        );
        return (
          <>
            <span className="flex items-center justify-between gap-2">
              <span className="min-w-0 truncate font-medium text-slate-900 dark:text-slate-100">
                {pessoa.nome || pessoa.razao_social || pessoa.fantasia || "Pessoa"}
              </span>
              {codigo && (
                <span className="rounded bg-slate-100 px-1.5 py-0.5 font-mono text-xs text-slate-600 dark:bg-slate-800 dark:text-slate-300">
                  #{codigo}
                </span>
              )}
            </span>
            <span className="block text-sm text-slate-500 dark:text-slate-400">
              {contato
                ? `Celular de ${contato.vinculo}: ${contato.numero} · cadastro principal`
                : [pessoa.cpf || pessoa.cnpj, pessoa.telefone || pessoa.celular]
                    .filter(Boolean)
                    .join(" - ")}
            </span>
            {mostrarEndereco && formatarEnderecoPrincipalCliente(pessoa) && (
              <span className="mt-1 block text-xs text-slate-500 dark:text-slate-400">
                Endereço: {formatarEnderecoPrincipalCliente(pessoa)}
              </span>
            )}
            {pessoa.pets?.length > 0 && (
              <span className="block text-xs text-blue-600 dark:text-cyan-400">
                {pessoa.pets.length} pet(s)
              </span>
            )}
          </>
        );
      }}
    />
  );
}
