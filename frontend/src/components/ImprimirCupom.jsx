import { Printer } from 'lucide-react';
import PropTypes from 'prop-types';
import { formatMoneyBRL } from '../utils/formatters';

const RECEIPT_WIDTH = 42;

function toAscii(texto) {
  return String(texto || '')
    .normalize('NFD')
    .replaceAll(/[\u0300-\u036f]/g, '')
    .replaceAll(/[^\x20-\x7E]/g, ' ')
    .replaceAll(/\s+/g, ' ')
    .trim();
}

function clip(texto, max = RECEIPT_WIDTH) {
  const limpo = toAscii(texto);
  return limpo.length > max ? `${limpo.slice(0, max - 3)}...` : limpo;
}

function center(texto, width = RECEIPT_WIDTH) {
  const valor = clip(texto, width);
  const total = Math.max(0, width - valor.length);
  const left = Math.floor(total / 2);
  const right = total - left;
  return `${' '.repeat(left)}${valor}${' '.repeat(right)}`;
}

function linePair(label, valor, width = RECEIPT_WIDTH) {
  const right = clip(valor, Math.max(8, Math.floor(width / 2)));
  const maxLeft = Math.max(0, width - right.length - 1);
  const left = clip(label, maxLeft);
  return `${left}${' '.repeat(Math.max(1, width - left.length - right.length))}${right}`;
}

function wrap(texto, width = RECEIPT_WIDTH) {
  const palavras = toAscii(texto).split(' ');
  const linhas = [];
  let atual = '';

  for (const palavra of palavras) {
    if (!palavra) continue;
    const proposta = atual ? `${atual} ${palavra}` : palavra;
    if (proposta.length <= width) {
      atual = proposta;
      continue;
    }
    if (atual) linhas.push(atual);
    if (palavra.length <= width) {
      atual = palavra;
      continue;
    }
    for (let i = 0; i < palavra.length; i += width) {
      linhas.push(palavra.slice(i, i + width));
    }
    atual = '';
  }

  if (atual) linhas.push(atual);
  return linhas.length ? linhas : [''];
}

function renderItens(itens = []) {
  const linhas = [];
  for (const item of itens) {
    const nome = item?.produto_nome || item?.descricao || 'Item';
    linhas.push(...wrap(nome, RECEIPT_WIDTH));

    const qtd = Number(item?.quantidade || 0);
    const unit = formatMoneyBRL(Number(item?.preco_unitario || 0));
    const subtotal = formatMoneyBRL(Number(item?.subtotal || 0));
    linhas.push(linePair(`${qtd} x ${unit}`, subtotal));

    const desconto = Number(item?.desconto_valor || 0);
    if (desconto > 0) {
      linhas.push(linePair('Desconto item', `-${formatMoneyBRL(desconto)}`));
    }
    linhas.push('');
  }
  return linhas;
}

function montarCupom(venda) {
  const agora = new Date();
  const dataVenda = venda?.data_venda ? new Date(venda.data_venda) : agora;
  const numeroVenda = venda?.numero_venda || venda?.id || '-';
  const subtotal = Number(venda?.subtotal || 0);
  const descontoTotal = Number(venda?.desconto_valor || 0);
  const totalBruto = subtotal + descontoTotal;
  const taxaEntrega = Number(venda?.entrega?.taxa_entrega_total || 0);
  const total = Number(venda?.total || 0);
  const enderecoEntrega = venda?.entrega?.endereco_completo || venda?.endereco_entrega || '';
  const observacoesEntrega =
    venda?.entrega?.observacoes_entrega || venda?.observacoes_entrega || '';
  const telefoneCliente =
    venda?.cliente?.celular ||
    venda?.cliente?.telefone ||
    venda?.cliente?.celular_whatsapp ||
    venda?.telefone_cliente ||
    null;
  const enderecoCliente = [
    venda?.cliente?.endereco,
    venda?.cliente?.numero,
    venda?.cliente?.bairro,
    venda?.cliente?.cidade,
    venda?.cliente?.estado,
  ]
    .filter(Boolean)
    .join(', ');

  const linhas = [
    center('PET SHOP PRO'),
    center('Central de Gestao'),
    center(dataVenda.toLocaleString('pt-BR')),
    '-'.repeat(RECEIPT_WIDTH),
    clip(`VENDA #${numeroVenda}`),
    clip(`Data: ${dataVenda.toLocaleString('pt-BR')}`),
  ];

  if (venda?.cliente?.nome || venda?.cliente_nome) {
    linhas.push(...wrap(`Cliente: ${venda.cliente?.nome || venda.cliente_nome}`, RECEIPT_WIDTH));
  }

  if (telefoneCliente) {
    linhas.push(...wrap(`Telefone: ${telefoneCliente}`, RECEIPT_WIDTH));
  }

  if (enderecoCliente) {
    linhas.push(...wrap(`Endereco: ${enderecoCliente}`, RECEIPT_WIDTH));
  }

  if (venda?.pet?.nome) {
    linhas.push(...wrap(`Pet: ${venda.pet.nome}`, RECEIPT_WIDTH));
  }

  linhas.push(
    '-'.repeat(RECEIPT_WIDTH),
    clip('ITENS'),
    '-'.repeat(RECEIPT_WIDTH),
    ...renderItens(venda?.itens || []),
    '-'.repeat(RECEIPT_WIDTH),
    linePair('Total bruto:', formatMoneyBRL(totalBruto)),
  );

  if (descontoTotal > 0) {
    linhas.push(linePair('Desconto:', `-${formatMoneyBRL(descontoTotal)}`));
  }

  if (venda?.tem_entrega) {
    linhas.push(linePair('Taxa entrega:', formatMoneyBRL(taxaEntrega)));
  }

  linhas.push(
    '-'.repeat(RECEIPT_WIDTH),
    linePair('TOTAL:', formatMoneyBRL(total)),
    '-'.repeat(RECEIPT_WIDTH),
  );

  if (Array.isArray(venda?.pagamentos) && venda.pagamentos.length > 0) {
    linhas.push('PAGAMENTOS');
    for (const pag of venda.pagamentos) {
      const forma = pag?.forma_pagamento || 'Pagamento';
      const valor = formatMoneyBRL(Number(pag?.valor || 0));
      linhas.push(linePair(forma, valor));
    }
    linhas.push('-'.repeat(RECEIPT_WIDTH));
  }

  if (venda?.tem_entrega && (enderecoEntrega || observacoesEntrega)) {
    linhas.push('ENTREGA:');
    if (enderecoEntrega) {
      linhas.push(...wrap(enderecoEntrega, RECEIPT_WIDTH));
    }
    if (observacoesEntrega) {
      linhas.push(...wrap(`Obs: ${observacoesEntrega}`, RECEIPT_WIDTH));
    }
    linhas.push('-'.repeat(RECEIPT_WIDTH));
  }

  if (venda?.observacoes) {
    linhas.push('OBSERVACOES:', ...wrap(venda.observacoes, RECEIPT_WIDTH), '-'.repeat(RECEIPT_WIDTH));
  }

  linhas.push(center('Obrigado pela preferencia!'), center('Volte sempre!'));

  return linhas.join('\n');
}

export default function ImprimirCupom({ venda }) {
  const imprimir = () => {
    globalThis.print();
  };

  if (!venda) return null;

  return (
    <>
      {/* Bot\u00e3o Imprimir (vis\u00edvel na tela) */}
      <button
        onClick={imprimir}
        className="flex items-center gap-2 px-4 py-2 bg-gray-700 hover:bg-gray-800 text-white rounded-lg transition-colors print:hidden"
      >
        <Printer className="w-5 h-5" />
        <span>Imprimir Cupom</span>
      </button>

      {/* Estilos espec\u00edficos para impress\u00e3o */}
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

          @page {
            size: 80mm auto;
            margin: 2mm;
          }
        }
      `}</style>

      <pre
        className="cupom-impressao hidden print:block"
        style={{
          width: '76mm',
          fontFamily: 'Consolas, "Courier New", monospace',
          fontSize: '13px',
          lineHeight: 1.28,
          letterSpacing: '0.1px',
          fontWeight: 800,
          whiteSpace: 'pre',
          margin: 0,
          padding: 0,
          textTransform: 'none',
          textRendering: 'geometricPrecision',
        }}
      >
        {montarCupom(venda)}
      </pre>
    </>
  );
}

ImprimirCupom.propTypes = {
  venda: PropTypes.shape({
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
        forma_pagamento: PropTypes.string,
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
  }),
};
