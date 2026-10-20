import assert from "node:assert/strict";
import { test } from "node:test";
import {
  buildProductUrl,
  buildProductWhatsappUrl,
  copyProductUrl,
  shareProductUrl,
} from "./ecommerceProductLinks.js";

test("link do produto mantém a loja e descarta parâmetros da sessão", () => {
  assert.equal(
    buildProductUrl(
      {
        origin: "https://corepet.com.br",
        pathname: "/ecommerce",
        search: "?tenant=pet-amigo&produto=1&busca=racao&token=privado&view=checkout",
      },
      42,
    ),
    "https://corepet.com.br/ecommerce?tenant=pet-amigo&produto=42",
  );
  assert.equal(
    buildProductUrl({ origin: "https://corepet.com.br", pathname: "/pet-amigo" }, 42),
    "https://corepet.com.br/pet-amigo?produto=42",
  );
  assert.equal(
    buildProductUrl({ origin: "https://corepet.com.br", pathname: "/ecommerce" }, 42, "loja-id"),
    "https://corepet.com.br/ecommerce?tenant=loja-id&produto=42",
  );
});

test("WhatsApp inclui nome com acentos e URL exata do produto", () => {
  const product = { nome: "Ração cães & gatos" };
  const url = "https://corepet.com.br/ecommerce?tenant=amigo&produto=42";
  const whatsapp = new URL(buildProductWhatsappUrl(product, url));
  assert.equal(whatsapp.origin, "https://wa.me");
  assert.equal(whatsapp.searchParams.get("text"), `${product.nome}\n${url}`);
});

test("cópia só informa sucesso após a confirmação do navegador", async () => {
  let copied;
  assert.equal(
    await copyProductUrl("https://loja/?produto=42", {
      clipboard: {
        writeText: async (url) => {
          copied = url;
        },
      },
    }),
    true,
  );
  assert.equal(copied, "https://loja/?produto=42");
  assert.equal(await copyProductUrl("url", {}), false);
  assert.equal(
    await copyProductUrl("url", {
      clipboard: {
        writeText: async () => {
          throw new Error("Bloqueado");
        },
      },
    }),
    false,
  );
});

test("compartilhamento nativo recebe o produto e diferencia cancelamento de falha", async () => {
  const product = { nome: "Ração cães & gatos" };
  const url = "https://loja/?produto=42";
  let shared;
  assert.equal(
    await shareProductUrl(product, url, {
      share: async (data) => {
        shared = data;
      },
    }),
    "shared",
  );
  assert.deepEqual(shared, { title: product.nome, text: product.nome, url });
  assert.equal(await shareProductUrl(product, url, {}), "fallback");
  assert.equal(
    await shareProductUrl(product, url, {
      share: async () => {
        throw Object.assign(new Error(), { name: "AbortError" });
      },
    }),
    "cancelled",
  );
  assert.equal(
    await shareProductUrl(product, url, {
      share: async () => {
        throw new Error("Indisponível");
      },
    }),
    "fallback",
  );
});
