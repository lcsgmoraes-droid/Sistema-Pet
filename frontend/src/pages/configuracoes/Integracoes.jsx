import OpenAIIntegracaoCard from "./OpenAIIntegracaoCard";
import EcommerceAIIntegracaoCard from "./EcommerceAIIntegracaoCard";

export default function Integracoes() {
  return (
    <div className="space-y-6">
      <EcommerceAIIntegracaoCard />
      <OpenAIIntegracaoCard />
    </div>
  );
}
