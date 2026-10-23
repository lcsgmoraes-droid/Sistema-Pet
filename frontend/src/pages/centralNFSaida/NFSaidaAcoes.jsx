import {
  Download,
  Eye,
  FileInput,
  Printer,
  RotateCcw,
  Share2,
  Trash2,
  Unlock,
  XCircle,
  Zap,
} from "lucide-react";
import BotaoMenuAcoes from "../../components/v2/BotaoMenuAcoes/BotaoMenuAcoes";
import { rejeicaoResponsavelTecnico } from "../../utils/fiscalRejectionGuidance.mjs";
import { notaPermiteAcompanharEstorno, obterSituacaoEstorno } from "../../utils/nfeEstorno";

export default function NFSaidaAcoes({
  nota,
  setModalCancelar,
  excluirNota,
  reconciliarFluxoNota,
  reconciliandoNotaId,
  corrigirEReemitir,
  corrigindoNotaId,
  liberarVendaComRejeicao,
  liberandoVendaId,
  baixarDanfe,
  baixarXml,
  abrirDetalhes,
  compartilharNota,
  documentoEmCurso,
  abrirEstorno,
}) {
  const status = String(nota.status || "").toLowerCase();
  const intnfe = nota.provedor === "intnfe";
  const rejeitadaCorrigivel =
    intnfe &&
    status === "rejeitada" &&
    !rejeicaoResponsavelTecnico({ codigo: nota.codigo_erro, motivo: nota.motivo_rejeicao });
  const documentoIndisponivel =
    documentoEmCurso === String(nota.venda_id || nota.id) || (intnfe && status !== "autorizada");
  // FileInput identifica a emissão de uma NF-e de entrada/estorno; reutilizar para esta ação.
  const acoes = [
    notaPermiteAcompanharEstorno(nota) && {
      key: "estorno",
      icon: FileInput,
      label: obterSituacaoEstorno(nota) ? "Ver NF-e de estorno" : "Emitir NF-e de estorno",
      onClick: () => abrirEstorno(nota),
    },
    ["autorizada", "emitida danfe"].includes(status) && {
      key: "cancelar",
      icon: XCircle,
      label: "Cancelar NF-e",
      tom: "perigo",
      onClick: () => setModalCancelar(nota),
    },
    !intnfe && {
      key: "excluir",
      icon: Trash2,
      label: "Excluir nota do sistema",
      tom: "perigo",
      onClick: () => excluirNota(nota.venda_id, nota.numero),
    },
    rejeitadaCorrigivel && {
      key: "liberar",
      icon: Unlock,
      label: "Liberar venda para escolher outro modelo de nota",
      disabled: liberandoVendaId === String(nota.venda_id),
      onClick: () => liberarVendaComRejeicao(nota),
    },
    rejeitadaCorrigivel && {
      key: "reemitir",
      icon: RotateCcw,
      label: `Tentar novamente como ${Number(nota.modelo) === 55 ? "NF-e" : "NFC-e"}`,
      disabled: corrigindoNotaId === String(nota.venda_id),
      onClick: () => corrigirEReemitir(nota),
    },
    {
      key: "reconciliar",
      icon: Zap,
      label: "Forçar reconciliação desta NF",
      disabled: reconciliandoNotaId === String(nota.id),
      onClick: () => reconciliarFluxoNota(nota),
    },
    {
      key: "danfe",
      icon: Printer,
      label: "Baixar DANFE",
      disabled: documentoIndisponivel,
      onClick: () => baixarDanfe(nota),
    },
    {
      key: "xml",
      icon: Download,
      label: "Baixar XML",
      disabled: documentoIndisponivel,
      onClick: () => baixarXml(nota),
    },
    status === "autorizada" && {
      key: "compartilhar",
      icon: Share2,
      label: "Compartilhar nota",
      onClick: () => compartilharNota(nota),
    },
    { key: "detalhes", icon: Eye, label: "Ver Detalhes", onClick: () => abrirDetalhes(nota) },
  ];
  return <BotaoMenuAcoes acoes={acoes} rotulo={`Ações da nota ${nota.numero}`} />;
}
