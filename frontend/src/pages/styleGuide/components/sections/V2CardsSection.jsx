import { BarChart3, ShoppingBag, TrendingUp, Users, WalletCards } from "lucide-react";
import { useState } from "react";
import BotaoLink from "../../../../components/v2/BotaoLink/BotaoLink";
import CartaoIndicador from "../../../../components/v2/CartaoIndicador/CartaoIndicador";
import EstadoVazio from "../../../../components/v2/EstadoVazio/EstadoVazio";
import SeletorOpcoes from "../../../../components/v2/SeletorOpcoes/SeletorOpcoes";
import StyleGuideExample from "../StyleGuideExample";

const PERIODOS_EXEMPLO = [
  { valor: 7, rotulo: "7 dias" },
  { valor: 30, rotulo: "30 dias" },
  { valor: 90, rotulo: "90 dias" },
];

function Grupo({ label, note, children }) {
  return (
    <StyleGuideExample label={label} note={note}>
      <div className="w-full">{children}</div>
    </StyleGuideExample>
  );
}

export default function V2CardsSection() {
  const [periodo, setPeriodo] = useState(30);

  return (
    <>
      <Grupo
        label="CartaoIndicador — substitui MetricCard/CompactMetricCard/PriorityCard do dashboard, um único formato para cartão clicável de indicador"
        note='Prop "tom" usa o mesmo vocabulário de BotaoBase.variante (neutro/sucesso/perigo/informativo/atencao) — o ícone à esquerda muda de cor conforme o tom; a seta à direita só aparece quando o cartão tem "aoClicar" e é sempre o mesmo ícone (antes cada cartão da tela usava um ícone diferente pra dizer a mesma coisa). O miolo (children) é livre: quem chama formata o valor como quiser.'
      >
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-5">
          <CartaoIndicador
            icone={TrendingUp}
            tom="informativo"
            titulo="Faturamento"
            detalhe="Últimos 30 dias"
            aoClicar={() => {}}
          >
            <p className="text-lg font-bold text-slate-950 dark:text-white">R$ 12.480,00</p>
          </CartaoIndicador>
          <CartaoIndicador
            icone={TrendingUp}
            tom="sucesso"
            titulo="Total a receber"
            detalhe="Valores ainda em aberto"
            aoClicar={() => {}}
          >
            <p className="text-lg font-bold text-slate-950 dark:text-white">R$ 3.200,00</p>
          </CartaoIndicador>
          <CartaoIndicador
            icone={WalletCards}
            tom="perigo"
            titulo="Total a pagar"
            detalhe="Compromissos ainda em aberto"
            aoClicar={() => {}}
          >
            <p className="text-lg font-bold text-slate-950 dark:text-white">R$ 1.150,00</p>
          </CartaoIndicador>
          <CartaoIndicador
            icone={Users}
            tom="atencao"
            titulo="VIPs em risco"
            detalhe="R$ 890,00 em impacto estimado"
            aoClicar={() => {}}
          >
            <p className="text-lg font-bold text-slate-950 dark:text-white">4</p>
          </CartaoIndicador>
          <CartaoIndicador icone={BarChart3} tom="neutro" titulo="Ticket médio" detalhe="30 dias">
            <p className="text-lg font-bold text-slate-950 dark:text-white">R$ 87,50</p>
          </CartaoIndicador>
        </div>
        <p className="mt-2 text-xs text-slate-400 dark:text-slate-500">
          O último cartão não tem "aoClicar" — vira uma &lt;div&gt; estática, sem seta e sem efeito
          de hover (útil quando o número não leva a lugar nenhum).
        </p>
      </Grupo>

      <Grupo
        label="EstadoVazio — placeholder para painéis sem dado no período"
        note="Não define altura própria — quem chama controla o espaço (gráfico, lista) por fora."
      >
        <div className="h-40">
          <EstadoVazio
            icone={ShoppingBag}
            titulo="Sem produtos vendidos no período"
            descricao="Escolha outro período ou registre novas vendas."
          />
        </div>
      </Grupo>

      <Grupo
        label="SeletorOpcoes — grupo de opções únicas em formato de pill (filtro de período, alternância de visão)"
        note="Não é campo de formulário (por isso não é o InputRadio): as opções têm largura pelo conteúdo e ficam numa barra de ferramentas, sem label/erro/obrigatoriedade."
      >
        <SeletorOpcoes
          rotulo="Período"
          opcoes={PERIODOS_EXEMPLO}
          valorSelecionado={periodo}
          aoSelecionar={setPeriodo}
        />
      </Grupo>

      <Grupo
        label="BotaoLink — link de navegação secundário dentro de um painel (ex.: 'Ver produtos')"
        note="Sempre o mesmo texto simples — sem tamanho nem variante, não usa BotaoBase."
      >
        <BotaoLink onClick={() => {}}>Ver produtos</BotaoLink>
      </Grupo>
    </>
  );
}
