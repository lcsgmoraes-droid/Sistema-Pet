import OpenAIIntegracaoCard from "./OpenAIIntegracaoCard";
import StoneIntegracao from "./StoneIntegracao";

export default function Integracoes() {
  return (
    <div className="space-y-6">
      <OpenAIIntegracaoCard />
      <StoneIntegracao />
    </div>
  );
}
