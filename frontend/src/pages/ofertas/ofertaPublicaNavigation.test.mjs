import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const pasta = path.dirname(fileURLToPath(import.meta.url));
const ofertaPublica = fs.readFileSync(path.join(pasta, "OfertaPublica.jsx"), "utf8");
const ecommerce = fs.readFileSync(
  path.resolve(pasta, "../ecommerce/EcommerceStorefrontChrome.jsx"),
  "utf8",
);
const estudio = fs.readFileSync(path.join(pasta, "EstudioOfertas.jsx"), "utf8");
const publicacoes = fs.readFileSync(path.join(pasta, "OfertaPublicacoes.jsx"), "utf8");

assert.match(ofertaPublica, /const \[paginaAtual, setPaginaAtual\]/);
assert.match(ofertaPublica, /ArrowLeft/);
assert.match(ofertaPublica, /ArrowRight/);
assert.match(ofertaPublica, /onTouchStart=\{iniciarDeslize\}/);
assert.match(ofertaPublica, /requestFullscreen/);
assert.match(ofertaPublica, /\{paginaExibida \+ 1\} de \{totalPaginas\}/);
assert.match(ecommerce, /1 de \{banner\.pageCount\}/);
assert.match(ecommerce, /banner\.ctaLabel/);
assert.match(ecommerce, /hasPublishedCampaign/);
assert.match(ecommerce, /clamp\(420px, 42vw, 560px\)/);
assert.match(ecommerce, /objectFit:\s*useExpandedDesktopCanvas\s*\?\s*"contain"/);
assert.match(estudio, /Nova campanha/);
assert.match(estudio, /Salvar campanha e gerar link/);
assert.match(estudio, /setSelecionados\(\[\]\)/);
assert.match(estudio, /formData\.append\("imagem_url", imagemOrigem\)/);
assert.doesNotMatch(
  estudio.slice(
    estudio.indexOf("async function gerarImagemProfissional"),
    estudio.indexOf("async function salvarImagemGeradaNoProduto"),
  ),
  /fetch\(/,
);
assert.match(publicacoes, /Campanhas salvas/);
assert.match(publicacoes, /várias ativas ao mesmo tempo/);

console.log("ofertaPublicaNavigation: ok");
