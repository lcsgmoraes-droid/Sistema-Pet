import PedidosCompraView from "./compras/PedidosCompraView";
import usePedidosCompraController from "./compras/usePedidosCompraController";

const PedidosCompra = () => {
  const controller = usePedidosCompraController();

  return <PedidosCompraView controller={controller} />;
};

export default PedidosCompra;
