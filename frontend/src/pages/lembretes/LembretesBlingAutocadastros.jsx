import { PackageCheck } from "lucide-react";
import EstadoVazio from "../../components/v2/EstadoVazio/EstadoVazio";
import Etiqueta from "../../components/v2/Etiqueta/Etiqueta";
import FaixaAviso from "../../components/v2/FaixaAviso/FaixaAviso";
import LinkPadrao from "../../components/v2/LinkPadrao/LinkPadrao";
import { formatarDataHora } from "./lembretesFormatters";

export default function LembretesBlingAutocadastros({ autocadastrosBling }) {
  if (autocadastrosBling.total <= 0) {
    return (
      <EstadoVazio
        icone={PackageCheck}
        titulo="Nenhum produto cadastrado automaticamente nas últimas 24 horas."
      />
    );
  }

  return (
    <div className="grid gap-3">
      <FaixaAviso
        icone={PackageCheck}
        titulo="Auto cadastro Bling · últimas 24 horas"
        tom="sucesso"
      >
        O sistema identificou SKU sem cadastro, criou o produto e seguiu com a baixa
        automaticamente. Este aviso desaparece após 1 dia.
      </FaixaAviso>
      <div className="flex items-center gap-2">
        <Etiqueta tom="sucesso">{autocadastrosBling.total} itens</Etiqueta>
      </div>
      <ul className="m-0 grid list-none gap-2 p-0">
        {autocadastrosBling.items.map((item) => (
          <li
            className="flex flex-wrap items-center justify-between gap-2 rounded-xl border border-slate-200 bg-white px-4 py-3 text-sm dark:border-slate-700 dark:bg-slate-900"
            key={item.produto_id}
          >
            <LinkPadrao to={`/produtos/${item.produto_id}/editar`}>
              {item.codigo} - {item.nome}
            </LinkPadrao>
            <span className="v2-texto-ajuda">{formatarDataHora(item.created_at)}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}
