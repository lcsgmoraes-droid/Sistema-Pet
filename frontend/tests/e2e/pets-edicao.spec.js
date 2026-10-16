import { expect, test } from "@playwright/test";
import process from "node:process";
import { setTimeout as delay } from "node:timers/promises";
import { URL } from "node:url";
import { credenciaisDoAmbiente, login } from "./helpers.js";

const env = credenciaisDoAmbiente();
const petId = process.env.E2E_PET_ID;
const ambienteLocal =
  env && ["localhost", "127.0.0.1", "[::1]"].includes(new URL(env.baseURL).hostname);

test.use({ channel: "chrome" });

const petPath = `/api/pets/${petId}`;
const respostaPet = (response, method = "GET") =>
  new URL(response.url()).pathname === petPath && response.request().method() === method;

async function abrirEdicao(page) {
  const responsePromise = page.waitForResponse((response) => respostaPet(response));
  await page.goto(`/pets/${petId}/editar`, { waitUntil: "networkidle" });
  const response = await responsePromise;
  expect(response.status()).toBe(200);
  const pet = await response.json();
  expect(pet.nome).toMatch(/^QA-CAD-/);
  return { pet, authorization: response.request().headers().authorization };
}

async function salvarEdicao(page) {
  const responsePromise = page.waitForResponse((response) => respostaPet(response, "PUT"));
  await page.getByRole("button", { name: "Salvar Alterações", exact: true }).click();
  const response = await responsePromise;
  expect(response.status()).toBe(200);
  await expect(page).toHaveURL(new RegExp(`/pets/${petId}$`));
  return { enviado: response.request().postDataJSON(), salvo: await response.json() };
}

test.describe("Pet — carregamento direto da edição", () => {
  test.skip(!ambienteLocal || !petId, "requer stack local e E2E_PET_ID de um pet sintético");
  test.describe.configure({ mode: "serial" });
  let page;

  test.beforeAll(async ({ browser }) => {
    page = await browser.newPage({ baseURL: env.baseURL, viewport: { width: 1440, height: 900 } });
    await login(page, env);
    await expect(page).not.toHaveURL(/\/login(?:[?#]|$)/);
  });

  test.afterAll(async () => {
    await page?.close();
  });

  test("mostra a espécie cadastrada ao entrar direto e ao recarregar, sem salvar", async () => {
    const testInfo = test.info();
    const escritasPet = [];
    page.on("request", (request) => {
      if (
        new URL(request.url()).pathname.startsWith("/api/pets") &&
        ["POST", "PUT", "PATCH", "DELETE"].includes(request.method())
      ) {
        escritasPet.push(request.method());
      }
    });

    const { pet } = await abrirEdicao(page);

    await expect(page.locator("#pet-nome")).toHaveValue(pet.nome);
    await expect.poll(() => page.locator("#pet-cliente").inputValue()).toContain(pet.cliente_nome);
    await expect(page.locator("#pet-especie")).toHaveValue("Canina");
    await expect(page.getByText("Selecione a espécie.", { exact: true })).toHaveCount(0);

    await page.reload({ waitUntil: "networkidle" });
    await expect(page.locator("#pet-nome")).toHaveValue(pet.nome);
    await expect(page.locator("#pet-especie")).toHaveValue("Canina");
    await expect(page.getByText("Selecione a espécie.", { exact: true })).toHaveCount(0);
    expect(escritasPet).toEqual([]);
    await page.screenshot({ path: testInfo.outputPath("pet-edicao-especie-carregada.png") });
  });

  for (const nomeLegado of ["Cão", "Cachorro"]) {
    test(`preserva ${nomeLegado} ao editar observação e só troca após seleção explícita`, async () => {
      const testInfo = test.info();
      const { pet: antes, authorization } = await abrirEdicao(page);
      const headers = { authorization };
      // Somente o pet sintético validado acima é preparado e restaurado.
      const preparar = await page.request.put(petPath, {
        headers,
        data: { especie: nomeLegado },
      });
      expect(preparar.status()).toBe(200);
      try {
        await page.route("**/api/cadastros/especies?**", async (route) => {
          const response = await route.fetch();
          await delay(250);
          await route.fulfill({ response });
        });
        const { pet } = await abrirEdicao(page);
        expect(pet.especie).toBe(nomeLegado);
        await expect(page.locator("#pet-especie")).toHaveValue("Canina");
        await expect
          .poll(() => page.locator("#pet-cliente").inputValue())
          .toContain(pet.cliente_nome);
        await page.locator("#pet-observacoes").fill(`QA-CAD-20261016 Edição ${nomeLegado}`);
        const semTroca = await salvarEdicao(page);
        expect(semTroca.enviado.especie).toBe(nomeLegado);
        expect(semTroca.salvo.especie).toBe(nomeLegado);

        const { pet: depoisObservacao } = await abrirEdicao(page);
        expect(depoisObservacao.especie).toBe(nomeLegado);
        await page.locator("#pet-especie").click({ position: { x: 12, y: 18 } });
        await page.getByRole("option", { name: "Canina", exact: true }).click();
        const comTroca = await salvarEdicao(page);
        expect(comTroca.enviado.especie).toBe("Canina");
        expect(comTroca.salvo.especie).toBe("Canina");
        const { pet: depoisSelecao } = await abrirEdicao(page);
        expect(depoisSelecao.especie).toBe("Canina");
        await testInfo.attach("especie-antes-depois", {
          body: JSON.stringify({
            id: antes.id,
            antes: antes.especie,
            preparado: nomeLegado,
            aposObservacao: depoisObservacao.especie,
            aposSelecao: depoisSelecao.especie,
            restauradoPara: antes.especie,
          }),
          contentType: "application/json",
        });
      } finally {
        testInfo.setTimeout(testInfo.timeout + 10_000);
        const restaurar = await page.request.put(petPath, {
          headers,
          data: { especie: antes.especie, observacoes: antes.observacoes, raca: antes.raca },
        });
        expect(restaurar.status()).toBe(200);
      }
    });
  }
});
