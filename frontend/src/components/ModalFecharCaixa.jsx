import { useState, useEffect } from "react";
import { AlertCircle, X } from "lucide-react";
import { fecharCaixa, obterResumoCaixa, obterVendasCaixa, validarCaixaAtual } from "../api/caixa";
import ModalFecharCaixaContent from "./caixa/ModalFecharCaixaContent";

export default function ModalFecharCaixa({ caixaId, onClose, onSuccess }) {
  const [resumo, setResumo] = useState(null);
  const [valorContado, setValorContado] = useState(0);
  const [observacoes, setObservacoes] = useState("");
  const [loading, setLoading] = useState(true);
  const [salvando, setSalvando] = useState(false);
  const [erro, setErro] = useState(null);
  const [sucesso, setSucesso] = useState(false);
  const [mostrarContagem, setMostrarContagem] = useState(false);
  const [formaExpandida, setFormaExpandida] = useState(null);
  const [vendasDetalhe, setVendasDetalhe] = useState({});
  const [loadingVendas, setLoadingVendas] = useState(null);
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

  useEffect(() => {
    carregarResumo();
  }, [caixaId]);

  const carregarResumo = async () => {
    try {
      setErro(null);
      await validarCaixaAtual(caixaId);
      const data = await obterResumoCaixa(caixaId);
      setResumo(data);
      // Campo vazio — o funcionário deve contar e preencher manualmente
      setValorContado(0);
    } catch (error) {
      console.error("Erro ao carregar resumo:", error);
      setErro("Não foi possível carregar os dados do caixa. Feche e tente novamente.");
    } finally {
      setLoading(false);
    }
  };

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
    const somenteDecimal = String(valor || "")
      .replace(",", ".")
      .replace(/[^\d.]/g, "");
    const [inteiros, ...decimais] = somenteDecimal.split(".");
    const casasDecimais = decimais.join("").slice(0, 2);

    setNotas((prev) => ({
      ...prev,
      moedas: decimais.length ? `${inteiros}.${casasDecimais}` : inteiros,
    }));
  };

  const carregarVendasForma = async (forma) => {
    if (formaExpandida === forma) {
      setFormaExpandida(null);
      return;
    }
    setFormaExpandida(forma);
    if (vendasDetalhe[forma]) return;
    setLoadingVendas(forma);
    try {
      await validarCaixaAtual(caixaId);
      const data = await obterVendasCaixa(caixaId, forma);
      setVendasDetalhe((prev) => ({ ...prev, [forma]: data }));
    } catch (err) {
      console.error("Erro ao carregar vendas:", err);
      setVendasDetalhe((prev) => ({ ...prev, [forma]: [] }));
      setErro(
        (prev) =>
          prev || err.response?.data?.detail || err.message || "Erro ao carregar vendas do caixa.",
      );
    } finally {
      setLoadingVendas(null);
    }
  };

  const aplicarContagem = () => {
    const total = calcularTotalNotas();
    setValorContado(total);
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

    const dif = calcularDiferenca();
    if (Math.abs(dif) > 0.01 && !confirmandoDiferenca) {
      setConfirmandoDiferenca(true);
      return;
    }

    await executarFechamento();
  };

  const executarFechamento = async () => {
    setSalvando(true);
    setErro(null);
    try {
      await validarCaixaAtual(caixaId);
      await fecharCaixa(caixaId, {
        valor_informado: valorContado,
        observacoes_fechamento: observacoes || null,
      });

      setSucesso(true);
      // Aguarda 1s mostrando sucesso antes de fechar
      setTimeout(() => {
        onSuccess();
      }, 800);
    } catch (error) {
      console.error("Erro ao fechar caixa:", error);
      const mensagem =
        error.response?.data?.detail || error.message || "Erro ao fechar caixa. Tente novamente.";
      setErro(mensagem);
    } finally {
      setSalvando(false);
    }
  };

  if (loading) {
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
        : erro;

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
    <ModalFecharCaixaContent
      {...{
        calcularTotalNotas,
        atualizarQuantidadeNota,
        atualizarValorMoedas,
        aplicarContagem,
        limparContagem,
        carregarVendasForma,
        confirmandoDiferenca,
        diferenca,
        erro,
        executarFechamento,
        formaExpandida,
        handleFechar,
        loadingVendas,
        mostrarContagem,
        mostrarDicasDiferenca,
        notas,
        observacoes,
        onClose,
        resumo,
        salvando,
        setConfirmandoDiferenca,
        setFormaExpandida,
        setMostrarContagem,
        setMostrarDicasDiferenca,
        setObservacoes,
        setValorContado,
        sucesso,
        valorContado,
        vendasDetalhe,
      }}
    />
  );
}
