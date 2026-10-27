import { useEffect, useRef } from "react";
import AmazonFiscalOrderDialog from "../configuracoes/amazonFiscal/AmazonFiscalOrderDialog";
import useAmazonFiscal from "../configuracoes/amazonFiscal/useAmazonFiscal";

export default function NFSaidaFiscalExterna({ nota, aoFechar, aoAtualizar }) {
  const fiscal = useAmazonFiscal({ loadLists: false, onChanged: aoAtualizar });
  const abrirRef = useRef(fiscal.openOrder);
  abrirRef.current = fiscal.openOrder;
  useEffect(() => {
    void abrirRef.current({ id: nota.fiscal_order_id });
  }, [nota.fiscal_order_id]);
  return (
    <AmazonFiscalOrderDialog
      fiscal={{
        ...fiscal,
        closeOrder: () => {
          if (!fiscal.busy) {
            fiscal.closeOrder();
            aoFechar();
          }
        },
      }}
    />
  );
}
