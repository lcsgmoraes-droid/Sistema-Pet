import StyleGuideExample from "../StyleGuideExample";

export default function TypographySection() {
  return (
    <StyleGuideExample
      label="Classes Tailwind (src/styles/v2-tipografia.css) — não são componentes React"
      note="Mudar o tamanho de um papel em toda a tela: edita a classe uma vez (ex.: .v2-titulo-secao) e todo lugar que usa essa classe muda junto. Escolha deliberada em vez de componente: título/subtítulo não têm comportamento, só estilo — não precisam de composição, só precisam de um único ponto de ajuste. A tag (h1, h2, p, span) continua sendo escolhida por quem usa a classe."
    >
      <div className="w-full space-y-2">
        <div className="v2-titulo-pagina">Título de página (.v2-titulo-pagina)</div>
        <div className="v2-titulo-secao">Título de bloco/seção (.v2-titulo-secao)</div>
        <div className="v2-subtitulo">Linha de apoio abaixo de um título (.v2-subtitulo)</div>
        <p className="v2-texto">Parágrafo padrão de conteúdo (.v2-texto)</p>
        <div className="v2-texto-ajuda">
          Texto de ajuda pequeno, abaixo de um campo ou seção (.v2-texto-ajuda)
        </div>
        <div className="v2-rotulo">Rótulo pequeno em caixa alta (.v2-rotulo)</div>
        <div className="v2-menu-secao">Divisor de seção do menu lateral (.v2-menu-secao)</div>
        <div className="text-gray-700 dark:text-slate-300">
          <span className="v2-menu-item font-medium">
            Item do menu lateral (.v2-menu-item — sem cor própria, herda do container)
          </span>
        </div>
      </div>
    </StyleGuideExample>
  );
}
