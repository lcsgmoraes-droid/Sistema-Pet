import { Printer } from "lucide-react";
import PropTypes from "prop-types";
import { createPortal } from "react-dom";
import { useDadosCupomEmpresa } from "../hooks/useDadosCupomEmpresa";
import { ehVendaCrediario, montarConteudoCupom } from "../utils/pdvReceipt";
import ActionButton from "./ui/ActionButton";

export function CupomImpressao({ empresa = {}, portal = false, venda }) {
  if (!venda) return null;
  const paginas = montarConteudoCupom(venda, empresa).split("\f");

  const conteudo = (
    <>
      <style>{`
        @media print {
          body * {
            visibility: hidden;
          }
          .cupom-impressao, .cupom-impressao * {
            visibility: visible;
          }
          .cupom-impressao {
            position: absolute;
            left: 0;
            top: 0;
            width: 76mm;
            margin: 0;
            padding: 0 1mm;
            color: #000 !important;
            -webkit-print-color-adjust: exact;
            print-color-adjust: exact;
          }
          .cupom-impressao * {
            color: #000 !important;
          }
          .cupom-folha {
            break-after: page;
            page-break-after: always;
            break-inside: avoid;
            page-break-inside: avoid;
          }
          .cupom-folha:last-child {
            break-after: auto;
            page-break-after: auto;
          }

          @page {
            size: 80mm auto;
            margin: 2mm;
          }
        }
      `}</style>

      <div className="cupom-impressao hidden print:block">
        {paginas.map((pagina, index) => (
          <pre
            className="cupom-folha"
            key={`${index}-${pagina.slice(0, 16)}`}
            style={{
              width: "76mm",
              fontFamily: 'Consolas, "Courier New", monospace',
              fontSize: "13px",
              lineHeight: 1.28,
              letterSpacing: "0.1px",
              fontWeight: 800,
              whiteSpace: "pre",
              margin: 0,
              padding: 0,
              textTransform: "none",
              textRendering: "geometricPrecision",
            }}
          >
            {pagina}
          </pre>
        ))}
      </div>
    </>
  );

  const portalTarget = globalThis.document?.body;
  if (portal && portalTarget) {
    return createPortal(conteudo, portalTarget);
  }

  return conteudo;
}

export default function ImprimirCupom({ className = "", size = "md", venda }) {
  const { carregandoEmpresa, dadosEmpresa } = useDadosCupomEmpresa();

  if (!venda) return null;

  const crediario = ehVendaCrediario(venda);

  return (
    <>
      <ActionButton
        onClick={() => globalThis.print()}
        disabled={carregandoEmpresa}
        icon={Printer}
        intent="neutral"
        size={size}
        className={["print:hidden", className].filter(Boolean).join(" ")}
        title={carregandoEmpresa ? "Carregando dados da empresa para o recibo" : undefined}
      >
        <span>{crediario ? "Imprimir cupom + 2 vias" : "Imprimir Recibo"}</span>
      </ActionButton>

      <CupomImpressao empresa={dadosEmpresa} venda={venda} />
    </>
  );
}

const empresaPropType = PropTypes.shape({
  cnpj: PropTypes.string,
  cupom_cabecalho: PropTypes.string,
  cupom_mensagem_final: PropTypes.string,
  email: PropTypes.string,
  endereco: PropTypes.string,
  logradouro: PropTypes.string,
  nome_fantasia: PropTypes.string,
  razao_social: PropTypes.string,
  telefone: PropTypes.string,
});

const vendaPropType = PropTypes.shape({
  id: PropTypes.oneOfType([PropTypes.string, PropTypes.number]),
  numero_venda: PropTypes.oneOfType([PropTypes.string, PropTypes.number]),
  data_venda: PropTypes.string,
  subtotal: PropTypes.number,
  desconto_valor: PropTypes.number,
  total: PropTypes.number,
  cliente_nome: PropTypes.string,
  telefone_cliente: PropTypes.string,
  endereco_entrega: PropTypes.string,
  observacoes_entrega: PropTypes.string,
  cliente: PropTypes.shape({
    nome: PropTypes.string,
    telefone: PropTypes.string,
    celular: PropTypes.string,
    celular_whatsapp: PropTypes.string,
    endereco: PropTypes.string,
    numero: PropTypes.string,
    bairro: PropTypes.string,
    cidade: PropTypes.string,
    estado: PropTypes.string,
    uf: PropTypes.string,
  }),
  pet: PropTypes.shape({ nome: PropTypes.string }),
  itens: PropTypes.arrayOf(
    PropTypes.shape({
      produto_nome: PropTypes.string,
      descricao: PropTypes.string,
      quantidade: PropTypes.number,
      preco_unitario: PropTypes.number,
      subtotal: PropTypes.number,
      desconto_valor: PropTypes.number,
    }),
  ),
  pagamentos: PropTypes.arrayOf(
    PropTypes.shape({
      data_recebimento_prevista: PropTypes.string,
      forma_pagamento: PropTypes.string,
      forma_pagamento_tipo: PropTypes.string,
      intervalo_crediario: PropTypes.string,
      numero_parcelas: PropTypes.number,
      valor: PropTypes.number,
    }),
  ),
  tem_entrega: PropTypes.bool,
  entrega: PropTypes.shape({
    taxa_entrega_total: PropTypes.number,
    endereco_completo: PropTypes.string,
    observacoes_entrega: PropTypes.string,
  }),
  observacoes: PropTypes.string,
  eh_crediario: PropTypes.bool,
});

CupomImpressao.propTypes = {
  empresa: empresaPropType,
  portal: PropTypes.bool,
  venda: vendaPropType,
};

ImprimirCupom.propTypes = {
  className: PropTypes.string,
  size: PropTypes.oneOf(["xs", "sm", "md", "lg"]),
  venda: vendaPropType,
};
