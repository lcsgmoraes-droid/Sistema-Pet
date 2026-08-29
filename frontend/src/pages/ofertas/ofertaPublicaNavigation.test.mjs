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

assert.match(ofertaPublica, /const \[paginaAtual, setPaginaAtual\]/);
assert.match(ofertaPublica, /ArrowLeft/);
assert.match(ofertaPublica, /ArrowRight/);
assert.match(ofertaPublica, /onTouchStart=\{iniciarDeslize\}/);
assert.match(ofertaPublica, /requestFullscreen/);
assert.match(ofertaPublica, /\{paginaExibida \+ 1\} de \{totalPaginas\}/);
assert.match(ecommerce, /1 de \{banner\.pageCount\}/);
assert.match(ecommerce, /banner\.ctaLabel/);

console.log("ofertaPublicaNavigation: ok");
