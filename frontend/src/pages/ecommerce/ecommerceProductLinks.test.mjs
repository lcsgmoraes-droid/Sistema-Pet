import assert from "node:assert/strict";
import { test } from "node:test";
import {
  buildProductUrl,
  buildProductShareUrl,
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

test("link de prévia identifica produto e loja sem carregar dados da sessão", () => {
  const expected = "https://corepet.com.br/api/ecommerce/compartilhar/produtos/42?tenant=pet-amigo";
  assert.equal(buildProductShareUrl("https://corepet.com.br/pet-amigo?produto=42"), expected);
  assert.equal(
    buildProductShareUrl("https://corepet.com.br/ecommerce?tenant=pet-amigo&produto=42&token=privado&view=checkout#carrinho"),
    expected,
  );
  assert.equal(
    buildProductShareUrl("https://corepet.com.br/pet-amigo/?produto=42"),
    expected,
  );
  const tenantId = "12345678-1234-4123-8123-123456789012";
  assert.equal(
    buildProductShareUrl(`https://corepet.com.br/ecommerce?tenant=${tenantId}&produto=99`),
    `https://corepet.com.br/api/ecommerce/compartilhar/produtos/99?tenant=${tenantId}`,
  );
});

test("link de prévia não transforma navegação sem produto ou loja válida", () => {
  for (const url of [
    "https://corepet.com.br/pet-amigo",
    "https://corepet.com.br/ecommerce?produto=42",
    "https://corepet.com.br/ecommerce?tenant=outra%2Floja&produto=42",
    "https://corepet.com.br/pet-amigo?produto=-1",
    "https://corepet.com.br/pet-amigo?produto=42%2Foutro",
    "https://corepet.com.br/%E0%A4%A?produto=42",
    "endereço inválido",
  ]) assert.equal(buildProductShareUrl(url), url);
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
