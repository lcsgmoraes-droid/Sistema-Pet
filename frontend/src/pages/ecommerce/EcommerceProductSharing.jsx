import { useState } from "react";
import { Link, MessageCircle, Share2 } from "lucide-react";
import BotaoInteracao from "../../components/v2/BotaoInteracao/BotaoInteracao";
import InputTexto from "../../components/v2/InputTexto/InputTexto";
import LinkPadrao from "../../components/v2/LinkPadrao/LinkPadrao";
import {
  buildProductShareUrl,
  buildProductWhatsappUrl,
  copyProductUrl,
  shareProductUrl,
} from "./ecommerceProductLinks";

export default function EcommerceProductSharing({ product, url }) {
  const [message, setMessage] = useState("");
  const [showManualLink, setShowManualLink] = useState(false);
  const shareUrl = buildProductShareUrl(url);

  async function copyLink() {
    const copied = await copyProductUrl(shareUrl);
    setShowManualLink(!copied);
    setMessage(copied ? "Link do produto copiado!" : "Selecione e copie o link abaixo.");
  }

  async function shareLink() {
    const result = await shareProductUrl(product, shareUrl);
    if (result === "fallback") await copyLink();
  }

  return (
    <div style={{ display: "grid", gap: 10 }}>
      <div style={{ display: "flex", flexWrap: "wrap", alignItems: "center", gap: 12 }}>
        <BotaoInteracao icon={Share2} onClick={shareLink} tamanho="pequeno">
          Compartilhar
        </BotaoInteracao>
        <LinkPadrao href={buildProductWhatsappUrl(product, shareUrl)} novaJanela>
          <MessageCircle size={16} aria-hidden="true" /> WhatsApp
        </LinkPadrao>
        <BotaoInteracao icon={Link} onClick={copyLink} tamanho="pequeno">
          Copiar link do produto
        </BotaoInteracao>
      </div>
      {message && (
        <p role="status" style={{ margin: 0, fontSize: 13 }}>
          {message}
        </p>
      )}
      {showManualLink && (
        <InputTexto
          label="Link do produto"
          readOnly
          value={shareUrl}
          onFocus={(event) => event.target.select()}
        />
      )}
    </div>
  );
}
