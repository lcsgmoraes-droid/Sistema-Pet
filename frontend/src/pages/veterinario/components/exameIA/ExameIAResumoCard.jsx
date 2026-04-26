import ExameIAAlertas from "./ExameIAAlertas";
import ExameIAArquivoCard from "./ExameIAArquivoCard";
import ExameIACabecalho from "./ExameIACabecalho";
import ExameIAListas from "./ExameIAListas";
import ExameIAResumoTriagem from "./ExameIAResumoTriagem";
import ExameIAValoresEstruturados from "./ExameIAValoresEstruturados";

export default function ExameIAResumoCard({ dadosIA, exame, resumo }) {
  const {
    achadosImagem,
    alertasIA,
    condutasSugeridas,
    limitacoesIA,
    resultadoEstruturado,
    temAnaliseIA,
    temArquivo,
    temResultadoBase,
  } = dadosIA;

  return (
    <div className="space-y-3 rounded-xl border border-indigo-200 bg-white px-3 py-3 text-xs text-indigo-700">
      <ExameIACabecalho
        exame={exame}
        resumo={resumo}
        temAnaliseIA={temAnaliseIA}
        temArquivo={temArquivo}
        temResultadoBase={temResultadoBase}
      />

      <ExameIAArquivoCard exame={exame} />
      <ExameIAResumoTriagem exame={exame} />
      <ExameIAAlertas alertasIA={alertasIA} />
      <ExameIAListas
        achadosImagem={achadosImagem}
        condutasSugeridas={condutasSugeridas}
        limitacoesIA={limitacoesIA}
      />
      <ExameIAValoresEstruturados resultadoEstruturado={resultadoEstruturado} />

      {!temArquivo && !temResultadoBase && (
        <p className="text-xs text-amber-700">
          Este exame ainda nao tem arquivo nem resultado em texto. Cadastre o anexo para a IA conseguir analisar
          hemograma, bioquimica, laudos em PDF e imagens.
        </p>
      )}
    </div>
  );
}
