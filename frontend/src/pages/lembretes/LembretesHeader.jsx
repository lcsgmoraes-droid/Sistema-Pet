import { AlertCircle, Bell, Clock, MessageCircle } from "lucide-react";
import CartaoIndicador from "../../components/v2/CartaoIndicador/CartaoIndicador";

export default function LembretesHeader({ controller }) {
  const contacted = controller.lembretes.filter((item) => item.contatos_total > 0).length;
  const cards = [
    {
      icon: Bell,
      label: "Oportunidades ativas",
      value: controller.lembretes.length,
      tom: "neutro",
    },
    { icon: AlertCircle, label: "Atrasadas", value: controller.vencidos.length, tom: "perigo" },
    {
      icon: Clock,
      label: "Hoje até 7 dias",
      value: controller.proximosEmBreve.length,
      tom: "atencao",
    },
    { icon: MessageCircle, label: "Já contatadas", value: contacted, tom: "sucesso" },
  ];

  return (
    <section className="mb-5 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
      {cards.map(({ icon, label, tom, value }) => (
        <CartaoIndicador icone={icon} key={label} titulo={label} tom={tom}>
          <p className="text-2xl font-bold text-slate-950 dark:text-white">{value}</p>
        </CartaoIndicador>
      ))}
    </section>
  );
}
