import { existsSync, mkdirSync, rmSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import { spawnSync } from "node:child_process";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const outputDir = join(root, "docs", "marketing", "instagram", "assets");
const sourceDir = join(root, "docs", "marketing", "instagram", "source");
const workDir = join(root, "runtime", "marketing-instagram-kit");
const chrome =
  process.env.CHROME_PATH ||
  "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";

const logoPath = join(
  root,
  "frontend",
  "public",
  "brand",
  "corepet",
  "corepet-icon-192.png",
);

const cards = [
  {
    fileName: "01-corepet-lancamento.png",
    variant: "lifestyle",
    image: join(sourceDir, "corepet-lancamento-gestor-petshop.png"),
    eyebrow: "TECNOLOGIA PARA NEGÓCIOS PET",
    title: "Sua operação. Mais simples. Mais inteligente.",
    body: "Gestão, app e automações para pet shops, clínicas veterinárias e banho & tosa.",
  },
  {
    fileName: "02-corepet-ecossistema.png",
    variant: "product",
    image: join(
      root,
      "frontend",
      "public",
      "marketing",
      "corepet-demo-ecossistema-integrado-poster.jpg",
    ),
    eyebrow: "UM ÚNICO ECOSSISTEMA",
    title: "ERP + App + E-commerce",
    body: "Venda em todos os canais com estoque e operação centralizados.",
  },
  {
    fileName: "03-corepet-resultados.png",
    variant: "product",
    image: join(
      root,
      "frontend",
      "public",
      "marketing",
      "corepet-resultado-venda-por-venda-poster.jpg",
    ),
    eyebrow: "GESTÃO EM TEMPO REAL",
    title: "Venda não é só faturamento. É resultado.",
    body: "Acompanhe custos, margem e lucro venda por venda.",
  },
];

const highlights = [
  {
    fileName: "destaque-sistema.png",
    label: "Sistema",
    icon: '<rect x="5" y="6" width="14" height="12" rx="2"/><path d="M5 10h14M9 10v8"/>',
  },
  {
    fileName: "destaque-app.png",
    label: "App",
    icon: '<rect x="7" y="2" width="10" height="20" rx="2"/><path d="M11 18h2"/>',
  },
  {
    fileName: "destaque-automacao.png",
    label: "Automação",
    icon: '<path d="M20 11a8 8 0 1 0-2.34 5.66"/><path d="M20 4v7h-7"/>',
  },
  {
    fileName: "destaque-clientes.png",
    label: "Clientes",
    icon: '<path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78L12 21.23l8.84-8.84a5.5 5.5 0 0 0 0-7.78Z"/>',
  },
  {
    fileName: "destaque-demo.png",
    label: "Demo",
    icon: '<circle cx="12" cy="12" r="9"/><path d="m10 8 6 4-6 4Z"/>',
  },
];

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function brand() {
  return `<div class="brand"><img src="${pathToFileURL(logoPath).href}" alt=""><strong>CorePet</strong></div>`;
}

function cardHtml(card) {
  const imageUrl = pathToFileURL(card.image).href;
  const title = escapeHtml(card.title);
  const eyebrow = escapeHtml(card.eyebrow);
  const body = escapeHtml(card.body);
  const content =
    card.variant === "lifestyle"
      ? `<img class="lifestyle-image" src="${imageUrl}" alt=""><div class="lifestyle-shade"></div>
         <main class="copy lifestyle-copy"><p class="eyebrow">${eyebrow}</p><h1>${title}</h1><p class="body">${body}</p><span class="cta">CONHEÇA O COREPET</span></main>`
      : `<main class="copy product-copy${card.title.length > 35 ? " long-title" : ""}"><p class="eyebrow">${eyebrow}</p><h1>${title}</h1><p class="body">${body}</p></main>
         <figure class="product-frame"><img src="${imageUrl}" alt="Tela real do CorePet"><figcaption>TELA REAL DO SISTEMA</figcaption></figure>`;

  return `<!doctype html><html lang="pt-BR"><head><meta charset="utf-8"><style>
    *{box-sizing:border-box}html,body{margin:0;width:1080px;height:1080px;overflow:hidden;font-family:Inter,"Segoe UI",Arial,sans-serif;background:#020817;color:#fff}
    body{position:relative;background:radial-gradient(circle at 84% 14%,#0f766e66 0,transparent 34%),radial-gradient(circle at 8% 92%,#7c3aed33 0,transparent 35%),linear-gradient(145deg,#020617 0%,#081426 58%,#111827 100%)}
    body:after{content:"";position:absolute;inset:0;pointer-events:none;background-image:linear-gradient(#ffffff09 1px,transparent 1px),linear-gradient(90deg,#ffffff09 1px,transparent 1px);background-size:54px 54px;mask-image:linear-gradient(to bottom,#000,transparent 92%)}
    .brand{position:absolute;z-index:20;left:64px;top:56px;display:flex;align-items:center;gap:16px}.brand img{width:62px;height:62px;border-radius:16px;box-shadow:0 18px 50px #0008}.brand strong{font-size:38px;letter-spacing:-1.2px}
    .copy{position:absolute;z-index:12}.eyebrow{margin:0;color:#34d399;font-size:21px;font-weight:900;letter-spacing:.16em}.copy h1{margin:18px 0 0;font-size:64px;line-height:1.02;letter-spacing:-3px}.body{margin:24px 0 0;color:#dbeafe;font-size:28px;line-height:1.32;font-weight:600}.cta{display:inline-block;margin-top:34px;padding:17px 24px;border-radius:14px;background:#34d399;color:#03251d;font-size:18px;font-weight:950;letter-spacing:.08em}
    .lifestyle-image{position:absolute;inset:0;width:100%;height:100%;object-fit:cover}.lifestyle-shade{position:absolute;inset:0;background:linear-gradient(90deg,#020817f7 0%,#041225e8 37%,#04122555 64%,transparent 100%)}.lifestyle-copy{left:64px;top:292px;width:560px}.lifestyle-copy h1{font-size:72px}
    .product-copy{left:64px;top:168px;width:920px}.product-copy h1{font-size:61px}.product-copy.long-title h1{font-size:53px;max-width:900px}.product-copy .body{font-size:25px;max-width:820px}.product-frame{position:absolute;z-index:10;left:64px;right:64px;bottom:70px;height:510px;margin:0;padding:48px 12px 12px;border:3px solid #243349;border-radius:26px;background:#f8fafc;overflow:hidden;box-shadow:0 32px 90px #0009}.product-frame:before{content:"";position:absolute;left:22px;top:20px;width:12px;height:12px;border-radius:50%;background:#fb7185;box-shadow:22px 0 #fbbf24,44px 0 #34d399}.product-frame img{width:100%;height:100%;object-fit:cover;border-radius:12px}.product-frame figcaption{position:absolute;right:26px;top:17px;color:#334155;font-size:15px;font-weight:900;letter-spacing:.12em}
    .footer{position:absolute;z-index:20;right:54px;bottom:30px;color:#ffffffb0;font-size:18px;font-weight:800;letter-spacing:.05em}
  </style></head><body>${brand()}${content}<div class="footer">corepet.com.br</div></body></html>`;
}

function highlightHtml(highlight) {
  return `<!doctype html><html lang="pt-BR"><head><meta charset="utf-8"><style>
    *{box-sizing:border-box}html,body{margin:0;width:1080px;height:1080px;overflow:hidden;font-family:Inter,"Segoe UI",Arial,sans-serif;color:#fff}
    body{display:grid;place-items:center;background:radial-gradient(circle at 76% 18%,#14b8a655 0,transparent 36%),radial-gradient(circle at 18% 82%,#d4a72c33 0,transparent 32%),linear-gradient(145deg,#020617,#0b1d2b 62%,#102a2c)}
    .ring{width:690px;height:690px;display:grid;place-items:center;border:7px solid #34d399;border-radius:50%;background:#061521cc;box-shadow:0 0 0 26px #ffffff10,0 44px 120px #0009}
    .content{text-align:center;transform:translateY(-4px)}svg{width:260px;height:260px;fill:none;stroke:#d6ab35;stroke-width:1.65;stroke-linecap:round;stroke-linejoin:round}.label{margin-top:34px;font-size:54px;font-weight:900;letter-spacing:-1.5px}
  </style></head><body><div class="ring"><div class="content"><svg viewBox="0 0 24 24" aria-hidden="true">${highlight.icon}</svg><div class="label">${escapeHtml(highlight.label)}</div></div></div></body></html>`;
}

function capture(html, fileName) {
  const htmlPath = join(workDir, `${fileName}.html`);
  const outputPath = join(outputDir, fileName);
  writeFileSync(htmlPath, html, "utf8");
  const result = spawnSync(
    chrome,
    [
      "--headless=new",
      "--hide-scrollbars",
      "--disable-gpu",
      "--allow-file-access-from-files",
      "--window-size=1080,1080",
      "--force-device-scale-factor=1",
      `--screenshot=${outputPath}`,
      pathToFileURL(htmlPath).href,
    ],
    { encoding: "utf8", stdio: "pipe" },
  );
  if (result.status !== 0 || !existsSync(outputPath)) {
    throw new Error(result.stderr || result.stdout || `Falha ao gerar ${fileName}`);
  }
}

for (const required of [chrome, logoPath, ...cards.map((card) => card.image)]) {
  if (!existsSync(required)) throw new Error(`Arquivo obrigatório não encontrado: ${required}`);
}

rmSync(workDir, { recursive: true, force: true });
mkdirSync(workDir, { recursive: true });
mkdirSync(outputDir, { recursive: true });

for (const card of cards) capture(cardHtml(card), card.fileName);
for (const highlight of highlights) capture(highlightHtml(highlight), highlight.fileName);

console.log(`Kit do Instagram gerado em ${outputDir}`);
