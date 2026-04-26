import { formatarDataExame } from "./exameIAUtils";

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
      <CabecalhoExame
        exame={exame}
        resumo={resumo}
        temAnaliseIA={temAnaliseIA}
        temArquivo={temArquivo}
        temResultadoBase={temResultadoBase}
      />

      <ArquivoExame exame={exame} />

      <ResumoTriagem exame={exame} />

      <AlertasIA alertasIA={alertasIA} />

      <ListasIA
        achadosImagem={achadosImagem}
        condutasSugeridas={condutasSugeridas}
        limitacoesIA={limitacoesIA}
      />

      <ValoresEstruturados resultadoEstruturado={resultadoEstruturado} />

      {!temArquivo && !temResultadoBase && (
        <p className="text-xs text-amber-700">
          Este exame ainda nao tem arquivo nem resultado em texto. Cadastre o anexo para a IA conseguir analisar
          hemograma, bioquimica, laudos em PDF e imagens.
        </p>
      )}
    </div>
  );
}

function CabecalhoExame({ exame, resumo, temAnaliseIA, temArquivo, temResultadoBase }) {
  return (
    <div className="flex flex-wrap items-start justify-between gap-3">
      <div>
        <div className="font-semibold text-indigo-900">
          Exame #{exame.id} - {exame.nome || exame.tipo || "Exame"}
        </div>
        <p className="mt-1 text-indigo-600">
          Tipo: {exame.tipo || "nao informado"}
          {exame.data_solicitacao ? ` - solicitado em ${formatarDataExame(exame.data_solicitacao)}` : ""}
        </p>
        {resumo && (
          <p className="mt-1 text-indigo-600">
            Tutor: {resumo.tutor_nome || "-"} | Pet: {resumo.pet_nome || "-"}
          </p>
        )}
      </div>
      <div className="flex flex-wrap gap-2">
        <StatusBadge
          ativo={temArquivo}
          ativoClass="bg-emerald-100 text-emerald-700"
          ativoLabel="Arquivo anexado"
          inativoClass="bg-amber-100 text-amber-700"
          inativoLabel="Sem arquivo"
        />
        <StatusBadge
          ativo={temAnaliseIA}
          ativoClass="bg-indigo-100 text-indigo-700"
          ativoLabel="IA pronta"
          inativoClass="bg-gray-100 text-gray-600"
          inativoLabel="IA pendente"
        />
        <StatusBadge
          ativo={temResultadoBase}
          ativoClass="bg-blue-100 text-blue-700"
          ativoLabel="Resultado carregado"
          inativoClass="bg-gray-100 text-gray-600"
          inativoLabel="Sem resultado base"
        />
      </div>
    </div>
  );
}

function StatusBadge({ ativo, ativoClass, ativoLabel, inativoClass, inativoLabel }) {
  return (
    <span
      className={`rounded-full px-2 py-1 font-medium ${ativo ? ativoClass : inativoClass}`}
    >
      {ativo ? ativoLabel : inativoLabel}
    </span>
  );
}

function ArquivoExame({ exame }) {
  if (!exame.arquivo_nome) return null;

  return (
    <div className="rounded-lg border border-indigo-100 bg-indigo-50 px-3 py-2">
      <p className="font-medium text-indigo-800">Arquivo</p>
      <div className="mt-1 flex flex-wrap items-center gap-3">
        <span>{exame.arquivo_nome}</span>
        {exame.arquivo_url && (
          <a href={exame.arquivo_url} target="_blank" rel="noreferrer" className="text-indigo-700 underline">
            abrir arquivo
          </a>
        )}
      </div>
    </div>
  );
}

function ResumoTriagem({ exame }) {
  if (!exame.interpretacao_ia_resumo && !exame.interpretacao_ia) return null;

  return (
    <div className="rounded-lg border border-indigo-100 bg-indigo-50 px-3 py-3">
      <p className="font-medium text-indigo-900">Resumo da triagem</p>
      <p className="mt-1 text-sm text-indigo-800">
        {exame.interpretacao_ia_resumo || exame.interpretacao_ia}
      </p>
      {exame.interpretacao_ia && exame.interpretacao_ia !== exame.interpretacao_ia_resumo && (
        <p className="mt-2 text-xs text-indigo-700">
          <strong>Conclusao:</strong> {exame.interpretacao_ia}
        </p>
      )}
      {exame.interpretacao_ia_confianca != null && (
        <p className="mt-2 text-[11px] text-indigo-600">
          Confianca estimada: {Math.round(Number(exame.interpretacao_ia_confianca || 0) * 100)}%
        </p>
      )}
    </div>
  );
}

function AlertasIA({ alertasIA }) {
  if (alertasIA.length === 0) return null;

  return (
    <div className="space-y-2">
      <p className="font-medium text-indigo-900">Alertas automaticos</p>
      <div className="flex flex-wrap gap-2">
        {alertasIA.map((alerta, index) => {
          const status = String(alerta.status || "atencao").toLowerCase();
          const classes =
            status === "alto" || status === "baixo"
              ? "border-red-200 bg-red-50 text-red-700"
              : "border-amber-200 bg-amber-50 text-amber-700";
          return (
            <span
              key={`${alerta.campo || "alerta"}_${index}`}
              className={`rounded-full border px-2 py-1 text-[11px] ${classes}`}
            >
              {alerta.mensagem || alerta.campo}
            </span>
          );
        })}
      </div>
    </div>
  );
}

function ListasIA({ achadosImagem, condutasSugeridas, limitacoesIA }) {
  if (achadosImagem.length === 0 && condutasSugeridas.length === 0 && limitacoesIA.length === 0) {
    return null;
  }

  return (
    <div className="grid gap-3 md:grid-cols-3">
      <ListaIA titulo="Achados da imagem" itens={achadosImagem} vazio="Sem achados visuais destacados." />
      <ListaIA titulo="Condutas sugeridas" itens={condutasSugeridas} vazio="Sem conduta sugerida automaticamente." />
      <ListaIA titulo="Limitacoes" itens={limitacoesIA} vazio="Sem limitacoes especiais registradas." />
    </div>
  );
}

function ListaIA({ itens, titulo, vazio }) {
  return (
    <div className="rounded-lg border border-indigo-100 bg-gray-50 px-3 py-3">
      <p className="font-medium text-gray-800">{titulo}</p>
      {itens.length > 0 ? (
        <ul className="mt-2 space-y-1 text-gray-600">
          {itens.map((item, index) => (
            <li key={`${titulo}_${index}`}>- {item}</li>
          ))}
        </ul>
      ) : (
        <p className="mt-2 text-gray-500">{vazio}</p>
      )}
    </div>
  );
}

function ValoresEstruturados({ resultadoEstruturado }) {
  if (resultadoEstruturado.length === 0) return null;

  return (
    <div className="space-y-2">
      <p className="font-medium text-indigo-900">Valores estruturados</p>
      <div className="flex flex-wrap gap-2">
        {resultadoEstruturado.slice(0, 12).map(([chave, valor]) => (
          <span
            key={chave}
            className="rounded-full border border-indigo-200 bg-white px-2 py-1 text-[11px] text-indigo-700"
          >
            {chave}: {String(valor)}
          </span>
        ))}
      </div>
    </div>
  );
}
