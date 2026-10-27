import { FilePlus2, Settings2 } from "lucide-react";
import InputCombobox from "../v2/InputCombobox/InputCombobox";
import InputTexto from "../v2/InputTexto/InputTexto";
import BotaoInteracao from "../v2/BotaoInteracao/BotaoInteracao";
import BotaoSalva from "../v2/BotaoSalva/BotaoSalva";
import ComissaoGrupoConfiguracaoModal from "../../pages/comissoes/ComissaoGrupoConfiguracaoModal";

export default function VendasGruposProdutosPanel({
  controle,
  produtosSelecionados,
  vendedorSelecionado,
}) {
  return (
    <div className="mt-4 space-y-3 rounded-lg border border-slate-200 p-3 dark:border-slate-700">
      <div className="grid gap-3 sm:grid-cols-2">
        <InputCombobox
          id="vendas-grupo-produtos"
          label="Grupo de produtos salvo"
          placeholder="Escolha um grupo"
          value={controle.grupoSelecionado}
          onChange={controle.selecionarGrupo}
          opcoes={controle.gruposSalvos.map((grupo) => ({
            value: String(grupo.id),
            label: grupo.nome,
          }))}
        />
        <InputTexto
          id="vendas-nome-grupo"
          label="Nome do grupo"
          value={controle.nomeGrupo}
          onChange={controle.setNomeGrupo}
          maxLength={120}
        />
      </div>
      {controle.erroGrupos && (
        <p role="alert" className="text-sm text-red-600 dark:text-red-400">
          {controle.erroGrupos}
        </p>
      )}
      <div className="flex flex-wrap gap-2">
        <BotaoSalva
          type="button"
          onClick={() => controle.salvar(false)}
          disabled={controle.ocupado || !produtosSelecionados.length}
        >
          Salvar como novo grupo
        </BotaoSalva>
        {controle.grupo && (
          <BotaoInteracao
            onClick={() => controle.salvar(true)}
            disabled={controle.ocupado || !controle.grupoAlterado || !produtosSelecionados.length}
          >
            Atualizar grupo
          </BotaoInteracao>
        )}
        <BotaoInteracao
          icon={Settings2}
          onClick={() => controle.setConfigurando(true)}
          disabled={!controle.grupo || controle.grupoAlterado || controle.ocupado}
        >
          Configurar comissão do grupo
        </BotaoInteracao>
        <BotaoInteracao
          icon={FilePlus2}
          onClick={controle.provisionar}
          disabled={
            !controle.grupo ||
            controle.grupoAlterado ||
            controle.ocupado ||
            vendedorSelecionado === "sem-vendedor"
          }
        >
          Gerar contas a pagar
        </BotaoInteracao>
      </div>
      <p className="text-xs text-slate-500 dark:text-slate-400">
        O grupo fica salvo para os próximos períodos. A geração considera somente comissões já
        calculadas, ainda sem conta a pagar, respeitando período e vendedor. Configurar o grupo vale
        para as próximas vendas.
      </p>
      {controle.configurando && controle.grupo && (
        <ComissaoGrupoConfiguracaoModal
          grupo={controle.grupo}
          onClose={() => controle.setConfigurando(false)}
        />
      )}
    </div>
  );
}
