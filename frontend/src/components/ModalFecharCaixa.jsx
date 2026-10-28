import { useRef, useState } from "react";
import { AlertCircle, X } from "lucide-react";
import { baixarPdfCaixa, fecharCaixa, obterResumoCaixa, validarCaixaAtual } from "../api/caixa";
import ModalFecharCaixaContent from "./caixa/ModalFecharCaixaContent";
import ImpressaoTermicaCaixa from "./caixa/ImpressaoTermicaCaixa";
import { atualizarObservacaoComContagem } from "../utils/caixaContagem";
import useConferenciaFechamento from "./caixa/useConferenciaFechamento";

export default function ModalFecharCaixa({ caixaId, onClose, onSuccess }) {
  const [leitura, setLeitura] = useState(null);
  const resumo = leitura?.id === caixaId ? leitura.resumo : null;
  const setResumo = (dados) => setLeitura({ id: caixaId, resumo: dados });
  const [valorContado, setValorContado] = useState(0);
  const [observacoes, setObservacoes] = useState("");
  const [salvando, setSalvando] = useState(false);
  const fechamentoEmAndamento = useRef(false);
  const [erro, setErro] = useState(null);
  const [sucesso, setSucesso] = useState(false);
  const [imprimirRelatorio, setImprimirRelatorio] = useState(false);
  const [mostrarContagem, setMostrarContagem] = useState(false);
  const [confirmandoDiferenca, setConfirmandoDiferenca] = useState(false);
  const [mostrarDicasDiferenca, setMostrarDicasDiferenca] = useState(false);
  const [notas, setNotas] = useState({
    n100: "",
    n50: "",
    n20: "",
    n10: "",
    n5: "",
    n2: "",
    moedas: "",
  });

  const conferencia = useConferenciaFechamento(caixaId, {
    onResumo: setResumo,
    bloqueado: salvando || sucesso,
  });

  const calcularDiferenca = () => {
    if (!resumo || valorContado === null || valorContado === undefined) return 0;
    return valorContado - resumo.totais.saldo_atual;
  };

  const calcularTotalNotas = () => {
    return (
      (parseInt(notas.n100) || 0) * 100 +
      (parseInt(notas.n50) || 0) * 50 +
      (parseInt(notas.n20) || 0) * 20 +
      (parseInt(notas.n10) || 0) * 10 +
      (parseInt(notas.n5) || 0) * 5 +
      (parseInt(notas.n2) || 0) * 2 +
      parseFloat(notas.moedas || 0)
    );
  };

  const atualizarQuantidadeNota = (campo, valor) => {
    setNotas((prev) => ({
      ...prev,
      [campo]: String(valor || "").replace(/\D/g, ""),
    }));
  };

  const atualizarValorMoedas = (valor) => {
    setNotas((prev) => ({ ...prev, moedas: valor }));
  };

  const aplicarContagem = () => {
    const total = calcularTotalNotas();
    setValorContado(total);
    setObservacoes((atual) => atualizarObservacaoComContagem(atual, notas));
    setMostrarContagem(false);
  };

  const limparContagem = () => {
    setNotas({
      n100: "",
      n50: "",
      n20: "",
      n10: "",
      n5: "",
      n2: "",
      moedas: "",
    });
  };

  const handleFechar = async () => {
    if (valorContado === null || valorContado === undefined || valorContado === "") {
      setErro("Informe o valor contado no caixa (pode ser R$ 0,00 se tiver zerado após sangrias)");
      return;
    }

    await executarFechamento();
  };

  const executarFechamento = async () => {
    if (
      fechamentoEmAndamento.current ||
      salvando ||
      conferencia.salvando ||
      conferencia.atualizando
    )
      return;
    fechamentoEmAndamento.current = true;
    setSalvando(true);
    setErro(null);
    try {
      // Conferir o saldo atual antes de confirmar a diferença ou fechar.
      const leitura = await conferencia.atualizar();
      if (!leitura) {
        setErro("Não foi possível atualizar o caixa antes do fechamento. Tente novamente.");
        return;
      }
      const resumoAtual = leitura.resumo;
      const saldoMudou = resumoAtual.totais.saldo_atual !== resumo.totais.saldo_atual;
      if (
        Math.abs(valorContado - resumoAtual.totais.saldo_atual) > 0.01 &&
        (!confirmandoDiferenca || saldoMudou)
      ) {
        setConfirmandoDiferenca(true);
        return;
      }
      await validarCaixaAtual(caixaId);
      const caixaFechado = await fecharCaixa(caixaId, {
        valor_informado: valorContado,
        observacoes_fechamento: observacoes || null,
      });

      const resumoFechado = await obterResumoCaixa(caixaId).catch(() => ({
        ...resumoAtual,
        caixa: caixaFechado,
      }));
      setResumo(resumoFechado);
      setSucesso(true);
    } catch (error) {
      console.error("Erro ao fechar caixa:", error);
      const mensagem =
        error.response?.data?.detail || error.message || "Erro ao fechar caixa. Tente novamente.";
      setErro(mensagem);
    } finally {
      fechamentoEmAndamento.current = false;
      setSalvando(false);
    }
  };

  if (conferencia.inicial) {
    return (
      <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
        <div className="bg-white rounded-lg p-6 w-full max-w-2xl">
          <div className="flex items-center justify-center py-12">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
          </div>
        </div>
      </div>
    );
  }

  if (!resumo) {
    const mensagemErroResumo =
      erro && /Ã|â/.test(erro)
        ? "Nao foi possivel carregar os dados do caixa. Feche e tente novamente."
        : erro || conferencia.erro;

    return (
      <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
        <div className="bg-white rounded-lg w-full max-w-lg shadow-xl">
          <div className="p-6 border-b">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="w-12 h-12 rounded-full bg-red-100 flex items-center justify-center">
                  <AlertCircle className="w-6 h-6 text-red-600" />
                </div>
                <div>
                  <h2 className="text-xl font-bold text-gray-900">
                    Nao foi possivel abrir o fechamento
                  </h2>
                  <p className="text-sm text-gray-500">
                    Confira o status do caixa e tente novamente.
                  </p>
                </div>
              </div>
              <button
                onClick={onClose}
                className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
          </div>

          <div className="p-6">
            <div className="bg-red-50 border border-red-200 rounded-lg px-4 py-3 text-sm text-red-700">
              {mensagemErroResumo || "Nao foi possivel carregar os dados do caixa."}
            </div>
          </div>

          <div className="px-6 pb-6 flex justify-end">
            <button
              onClick={onClose}
              className="px-5 py-2.5 bg-gray-900 hover:bg-black text-white rounded-lg font-medium transition-colors"
            >
              Fechar
            </button>
          </div>
        </div>
      </div>
    );
  }

  const diferenca = calcularDiferenca();

  return (
    <>
      <ModalFecharCaixaContent
        {...{
          calcularTotalNotas,
          conferencia,
          atualizarQuantidadeNota,
          atualizarValorMoedas,
          aplicarContagem,
          limparContagem,
          confirmandoDiferenca,
          diferenca,
          erro,
          executarFechamento,
          handleFechar,
          mostrarContagem,
          mostrarDicasDiferenca,
          notas,
          observacoes,
          onClose,
          onSuccess,
          baixarPdf: () =>
            baixarPdfCaixa(caixaId, resumo.caixa.numero_caixa).catch(() =>
              setErro("Não foi possível gerar o PDF."),
            ),
          imprimirTermico: () => setImprimirRelatorio(true),
          resumo,
          salvando,
          setConfirmandoDiferenca,
          setMostrarContagem,
          setMostrarDicasDiferenca,
          setObservacoes,
          setValorContado,
          sucesso,
          valorContado,
        }}
      />
      <ImpressaoTermicaCaixa
        documento={imprimirRelatorio ? { resumo } : null}
        onAfterPrint={() => setImprimirRelatorio(false)}
      />
    </>
  );
}
