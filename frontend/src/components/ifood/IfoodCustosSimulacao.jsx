import { RotateCcw } from "lucide-react";
import BotaoInteracao from "../v2/BotaoInteracao/BotaoInteracao";
import InputRadio from "../v2/InputRadio/InputRadio";
import IfoodCustosCampos from "./IfoodCustosCampos";

export default function IfoodCustosSimulacao({ calculadora: c, produtoId }) {
  if (!c.podeSimularCustos) return null;
  return (
    <section className="space-y-4 rounded-xl border border-blue-200 p-4 dark:border-blue-500/30">
      <div>
        <h3 className="v2-titulo-secao">Taxas usadas na simulação</h3>
        <p className="v2-texto-ajuda mt-1">
          Experimente as condições do contrato sem alterar as regras da loja. O custo do produto
          continua vindo do cadastro.
        </p>
      </div>
      <InputRadio
        name={`ifood-simulacao-custos-${produtoId}`}
        label="Origem das taxas"
        disabled={c.salvando}
        value={c.custosAtivos ? "temporarios" : "loja"}
        onChange={c.alterarModoCustos}
        opcoes={[
          { value: "loja", label: "Usar taxas da loja" },
          { value: "temporarios", label: "Experimentar taxas temporárias" },
        ]}
        help="Nenhuma taxa digitada aqui é salva no produto ou nas regras da loja."
      />
      {c.custosAtivos ? (
        <>
          <p role="status" className="text-sm font-semibold text-blue-800 dark:text-blue-200">
            Taxas temporárias · não salvas
          </p>
          <IfoodCustosCampos
            prefixo={`ifood-simulacao-${produtoId}`}
            valores={c.custosSimulados}
            onChange={c.alterarCusto}
            disabled={c.salvando}
            className="grid gap-3 xl:grid-cols-2"
          />
          <p className="v2-texto-ajuda">
            Deixe como não informado quando ainda não souber a taxa. Informe zero somente quando
            esse custo não se aplicar. A meta é opcional.
          </p>
          <BotaoInteracao
            icon={RotateCcw}
            tamanho="pequeno"
            disabled={c.salvando}
            onClick={c.restaurarCustos}
          >
            Restaurar taxas da loja
          </BotaoInteracao>
        </>
      ) : (
        <p className="v2-texto-ajuda">
          O cálculo usa as taxas atualmente salvas nas regras da loja.
        </p>
      )}
    </section>
  );
}
