import { Printer } from 'lucide-react';
import { formatMoneyBRL } from '../utils/formatters';

export default function ImprimirCupom({ venda, onClose }) {
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
          /* Esconder tudo exceto o cupom */
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
            width: 80mm;
            margin: 0;
            padding: 0;
            color: #000 !important;
            print-color-adjust: exact;
            -webkit-print-color-adjust: exact;
            text-rendering: geometricPrecision;
          }
          .cupom-impressao * {
            color: #000 !important;
          }
          
          /* Reset de margens para impress\u00e3o */
          @page {
            size: 80mm auto;
            margin: 4mm;
          }
        }
      `}</style>

      {/* Cupom (hidden na tela, vis\u00edvel na impress\u00e3o) */}
      <div className="cupom-impressao hidden print:block" style={{ width: '80mm', fontFamily: 'monospace', fontWeight: 500, lineHeight: 1.35 }}>
        <div style={{ textAlign: 'center', marginBottom: '10px' }}>
          <div style={{ fontSize: '19px', fontWeight: 'bold' }}>PET SHOP PRO</div>
          <div style={{ fontSize: '12px', fontWeight: 'bold' }}>Central de Gest\u00e3o</div>
          <div style={{ fontSize: '11px', marginTop: '5px', fontWeight: 600 }}>
            {new Date().toLocaleString('pt-BR')}
          </div>
        </div>

        <div style={{ borderTop: '1px dashed #000', marginBottom: '10px', paddingTop: '10px' }}>
          <div style={{ fontSize: '14px', fontWeight: 'bold', marginBottom: '5px' }}>
            VENDA #{venda.numero_venda || venda.id}
          </div>
          <div style={{ fontSize: '11px', fontWeight: 600 }}>
            <div>Data: {venda.data_venda ? new Date(venda.data_venda).toLocaleString('pt-BR') : new Date().toLocaleString('pt-BR')}</div>
            {venda.cliente && (
              <div>Cliente: {venda.cliente.nome || venda.cliente_nome}</div>
            )}
            {venda.pet && (
              <div>Pet: {venda.pet.nome}</div>
            )}
          </div>
        </div>

        <div style={{ borderTop: '1px dashed #000', marginBottom: '10px', paddingTop: '10px' }}>
          <table style={{ width: '100%', fontSize: '11px', borderCollapse: 'collapse' }}>
            <thead>
              <tr style={{ borderBottom: '1px solid #000' }}>
                <th style={{ textAlign: 'left', paddingBottom: '5px' }}>Item</th>
                <th style={{ textAlign: 'center', paddingBottom: '5px' }}>Qtd</th>
                <th style={{ textAlign: 'right', paddingBottom: '5px' }}>Valor</th>
              </tr>
            </thead>
            <tbody>
              {venda.itens?.map((item, index) => (
                <tr key={index}>
                  <td style={{ paddingTop: '5px', paddingBottom: '5px' }}>
                    {item.produto_nome}
                    <br />
                    <span style={{ fontSize: '10px', fontWeight: 600 }}>
                      {item.quantidade} x {formatMoneyBRL(item.preco_unitario)}
                      {item.desconto_valor > 0 && (
                        <span>
                          {' '}com {formatMoneyBRL(item.desconto_valor)} de desconto
                        </span>
                      )}
                    </span>
                  </td>
                  <td style={{ textAlign: 'center', paddingTop: '5px', paddingBottom: '5px' }}>
                    {item.quantidade}
                  </td>
                  <td style={{ textAlign: 'right', paddingTop: '5px', paddingBottom: '5px' }}>
                    {formatMoneyBRL(item.subtotal)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div style={{ borderTop: '1px dashed #000', paddingTop: '10px', fontSize: '11px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '5px' }}>
            <span>Total bruto:</span>
            <span>{formatMoneyBRL(venda.subtotal + venda.desconto_valor)}</span>
          </div>
          
          {venda.desconto_valor > 0 && (
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '5px' }}>
              <span>
                {((venda.desconto_valor / (venda.subtotal + venda.desconto_valor)) * 100).toFixed(2)}% de desconto:
              </span>
              <span>{formatMoneyBRL(venda.desconto_valor)}</span>
            </div>
          )}

          {venda.tem_entrega && (
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '5px' }}>
              <span>Taxa de Entrega:</span>
              <span>{formatMoneyBRL(venda.entrega?.taxa_entrega_total || 0)}</span>
            </div>
          )}

          <div style={{ 
            display: 'flex', 
            justifyContent: 'space-between', 
            marginTop: '10px', 
            paddingTop: '10px',
            borderTop: '1px solid #000',
            fontSize: '14px',
            fontWeight: 'bold'
          }}>
            <span>TOTAL:</span>
            <span>{formatMoneyBRL(venda.total)}</span>
          </div>
        </div>

        {venda.pagamentos && venda.pagamentos.length > 0 && (
          <div style={{ borderTop: '1px dashed #000', marginTop: '10px', paddingTop: '10px', fontSize: '10px' }}>
            <div style={{ fontWeight: 'bold', marginBottom: '5px' }}>PAGAMENTOS:</div>
            {venda.pagamentos.map((pag, index) => (
              <div key={index} style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '3px' }}>
                <span>{pag.forma_pagamento}</span>
                <span>{formatMoneyBRL(pag.valor)}</span>
              </div>
            ))}
          </div>
        )}

        {venda.tem_entrega && venda.entrega && (
          <div style={{ borderTop: '1px dashed #000', marginTop: '10px', paddingTop: '10px', fontSize: '10px' }}>
            <div style={{ fontWeight: 'bold', marginBottom: '5px' }}>ENTREGA:</div>
            <div>{venda.entrega.endereco_completo}</div>
            {venda.entrega.observacoes_entrega && (
              <div style={{ marginTop: '3px', fontStyle: 'italic' }}>
                Obs: {venda.entrega.observacoes_entrega}
              </div>
            )}
          </div>
        )}

        {venda.observacoes && (
          <div style={{ borderTop: '1px dashed #000', marginTop: '10px', paddingTop: '10px', fontSize: '10px' }}>
            <div style={{ fontWeight: 'bold', marginBottom: '5px' }}>OBSERVA\u00c7\u00d5ES:</div>
            <div>{venda.observacoes}</div>
          </div>
        )}

        <div style={{ 
          textAlign: 'center', 
          marginTop: '15px', 
          paddingTop: '10px',
          borderTop: '1px dashed #000',
          fontSize: '10px'
        }}>
          <div>Obrigado pela preferencia!</div>
          <div style={{ marginTop: '5px' }}>Volte sempre!</div>
        </div>
      </div>
    </>
  );
}
