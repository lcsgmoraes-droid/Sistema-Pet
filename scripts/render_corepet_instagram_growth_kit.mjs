import { copyFileSync, existsSync, mkdirSync, rmSync, writeFileSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import { spawnSync } from "node:child_process";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const instagramDir = join(root, "docs", "marketing", "instagram");
const outputDir = resolve(
  process.env.COREPET_INSTAGRAM_OUTPUT_DIR || join(instagramDir, "growth"),
);
const sourceDir = join(instagramDir, "source");
const marketingDir = join(root, "frontend", "public", "marketing");
const shotsDir = join(marketingDir, "product-shots");
const workDir = join(root, "runtime", "marketing-instagram-growth");
const chrome =
  process.env.CHROME_PATH ||
  "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";
const ffmpeg = process.env.FFMPEG_PATH || "ffmpeg";
const ffprobe = process.env.FFPROBE_PATH || "ffprobe";
const edgeTts = process.env.EDGE_TTS_PATH || "edge-tts";
const rebuildReels = process.env.COREPET_REBUILD_REELS === "1";
const onlyReel = process.env.COREPET_ONLY_REEL?.trim() || "";
const reuseReelAudio = process.env.COREPET_REUSE_REEL_AUDIO === "1";
const customReelAudio = process.env.COREPET_REEL_AUDIO_PATH
  ? resolve(process.env.COREPET_REEL_AUDIO_PATH)
  : "";
const reelMotion = process.env.COREPET_REEL_MOTION?.trim().toLowerCase() || "stable";

if (!["stable", "zoom"].includes(reelMotion)) {
  throw new Error("COREPET_REEL_MOTION deve ser 'stable' ou 'zoom'.");
}
if (customReelAudio && !onlyReel) {
  throw new Error(
    "Use COREPET_REEL_AUDIO_PATH junto com COREPET_ONLY_REEL para evitar reutilizar a mesma voz em vários Reels.",
  );
}

const logoPath = join(
  root,
  "frontend",
  "public",
  "brand",
  "corepet",
  "corepet-icon-192.png",
);

const assets = {
  night: join(sourceDir, "corepet-petshop-venda-noturna.png"),
  owner: join(sourceDir, "corepet-atendimento-inteligente.png"),
  appHome: join(shotsDir, "app-inicio.png"),
  appProducts: join(shotsDir, "app-produtos.png"),
  ecommerce: join(shotsDir, "ecommerce-catalogo.png"),
  recurrence: join(shotsDir, "erp-recorrencia.png"),
  waitlist: join(shotsDir, "pdv-lista-espera.png"),
  retention: join(shotsDir, "erp-campanhas-retencao.png"),
  campaigns: join(shotsDir, "erp-campanhas.png"),
  results: join(shotsDir, "erp-resultado.png"),
  sale: join(shotsDir, "erp-venda-expandida.png"),
};

const feedCards = [
  {
    file: "04-o-que-seu-sistema-nao-entrega.png",
    layout: "screen",
    eyebrow: "DIRETO AO PONTO",
    title: "O que o seu sistema de pet shop não entrega?",
    accentTitle: "O CorePet entrega.",
    body: "Gestão, automação e venda ativa em uma única operação.",
    image: assets.campaigns,
    badge: "TELA REAL DO COREPET",
    accent: "#34d399",
  },
  {
    file: "05-venda-mesmo-fechado.png",
    layout: "lifestyle",
    eyebrow: "LOJA FECHADA. CANAIS ABERTOS.",
    title: "Venda, mesmo fechado.",
    body: "App e e-commerce mantêm seu catálogo disponível 24 horas por dia.",
    image: assets.night,
    chip: "ERP + APP + E-COMMERCE",
    accent: "#34d399",
  },
  {
    file: "06-sistema-conversa-com-cliente.png",
    layout: "lifestyle",
    eyebrow: "RELACIONAMENTO AUTOMÁTICO",
    title: "Dono de pet shop: seu sistema conversa com o cliente?",
    body: "O CorePet identifica oportunidades e ativa o cliente pelo app.",
    image: assets.owner,
    notification: "A ração pode estar acabando. Que tal pedir novamente?",
    accent: "#2dd4bf",
  },
  {
    file: "07-venda-24-horas.png",
    layout: "channels",
    eyebrow: "VENDA DISPONÍVEL 24 HORAS",
    title: "Já pensou em vender 24 horas por dia?",
    body: "Um catálogo. Três canais. Estoque centralizado.",
    accent: "#60a5fa",
  },
  {
    file: "08-estoque-voltou-cliente-sabe.png",
    layout: "screen",
    eyebrow: "LISTA DE ESPERA AUTOMÁTICA",
    title: "O estoque voltou. Seu cliente já sabe?",
    body: "O CorePet reconhece a reposição e avisa pelo app.",
    image: assets.waitlist,
    badge: "OPORTUNIDADE RECUPERADA",
    accent: "#f59e0b",
  },
  {
    file: "09-pare-de-esperar.png",
    layout: "screen",
    eyebrow: "VENDA ATIVA",
    title: "Chega de esperar o cliente voltar.",
    accentTitle: "O CorePet identifica a hora de agir.",
    body: "Recompra, retenção e campanhas sem depender da memória da equipe.",
    image: assets.retention,
    badge: "AUTOMAÇÃO REAL",
    accent: "#a78bfa",
    titleSize: 72,
    accentTitleSize: 64,
    bodySize: 27,
    screenHeight: 470,
  },
];

const carousels = [
  {
    slug: "01-seu-sistema-so-registra",
    accent: "#34d399",
    slides: [
      {
        eyebrow: "PROVOCAÇÃO PARA O GESTOR",
        title: "Seu sistema só registra vendas?",
        accentTitle: "O CorePet trabalha para vender de novo.",
        body: "Arraste para ver o que muda quando o sistema entende o cliente.",
        image: assets.campaigns,
      },
      {
        step: "01",
        title: "Registrar a venda é o começo.",
        body: "O CorePet usa o histórico para reconhecer padrões de consumo e novas oportunidades.",
        image: assets.recurrence,
      },
      {
        step: "02",
        title: "A próxima compra deixa sinais.",
        body: "O sistema calcula a data provável da recompra de itens recorrentes.",
        image: assets.recurrence,
      },
      {
        step: "03",
        title: "Cliente parado não precisa ser esquecido.",
        body: "Regras de retenção identificam quem deixou de comprar e preparam uma ação.",
        image: assets.retention,
      },
      {
        step: "04",
        title: "Produto sem estoque não precisa virar venda perdida.",
        body: "Quando o item volta, a lista de espera pode avisar o cliente automaticamente.",
        image: assets.waitlist,
      },
      {
        step: "05",
        title: "Seu sistema registra. O CorePet entende, conversa e vende.",
        body: "Peça uma demonstração preparada para a realidade da sua loja.",
        cta: "FALE COM A COREPET",
      },
    ],
  },
  {
    slug: "02-venda-mesmo-fechado",
    accent: "#60a5fa",
    slides: [
      {
        eyebrow: "VAREJO PET SEM PAUSA",
        title: "A loja fechou.",
        accentTitle: "As vendas não precisam.",
        body: "Veja como o CorePet mantém sua operação disponível ao cliente.",
        image: assets.night,
      },
      {
        step: "01",
        title: "O mesmo catálogo no app e no e-commerce.",
        body: "Produtos, preços e disponibilidade partem de um cadastro central.",
        layout: "channels",
      },
      {
        step: "02",
        title: "O cliente compra no canal que preferir.",
        body: "A experiência continua depois que a porta física fecha.",
        image: assets.appProducts,
        phone: true,
      },
      {
        step: "03",
        title: "Os pedidos voltam para uma única operação.",
        body: "Sua equipe acompanha tudo no CorePet, sem espalhar a gestão.",
        image: assets.ecommerce,
      },
      {
        step: "04",
        title: "Venda, mesmo fechado.",
        body: "Conheça o ecossistema CorePet em uma demonstração guiada.",
        cta: "SOLICITE UMA DEMO",
      },
    ],
  },
];

const highlights = [
  ["comece", "Comece aqui", '<path d="M5 12h14M13 6l6 6-6 6"/>'],
  ["sistema", "Sistema", '<rect x="4" y="5" width="16" height="14" rx="2"/><path d="M4 9h16M8 9v10"/>'],
  ["vendas24h", "Vendas 24h", '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>'],
  ["automacao", "Automação", '<path d="M20 11a8 8 0 1 0-2.3 5.7M20 4v7h-7"/>'],
  ["resultados", "Resultados", '<path d="M4 19V9M10 19V5M16 19v-7M22 19H2"/>'],
  ["duvidas", "Dúvidas", '<circle cx="12" cy="12" r="9"/><path d="M9.8 9a2.4 2.4 0 1 1 3.7 2c-.9.5-1.5 1-1.5 2M12 17h.01"/>'],
  ["demo", "Demo", '<circle cx="12" cy="12" r="9"/><path d="m10 8 6 4-6 4Z"/>'],
];

const storyGroups = [
  {
    slug: "comece",
    slides: [
      ["COMECE AQUI", "O CorePet é um sistema completo para negócios pet.", "ERP, app, e-commerce e automações em uma única operação."],
      ["PARA QUEM É", "Pet shops que querem vender e gerir melhor.", "Da operação física ao relacionamento com o cliente."],
      ["PRÓXIMO PASSO", "Quer ver funcionando na sua loja?", "Solicite uma demonstração pelo link do perfil.", "PEDIR DEMONSTRAÇÃO"],
    ],
  },
  {
    slug: "sistema",
    slides: [
      ["GESTÃO CENTRALIZADA", "PDV, estoque, compras e financeiro.", "Uma visão única da operação."],
      ["RESULTADO REAL", "Margem e lucro venda por venda.", "Faturamento sozinho não conta a história inteira."],
      ["CANAIS CONECTADOS", "ERP + app + e-commerce.", "Catálogo e estoque trabalhando juntos."],
    ],
  },
  {
    slug: "automacao",
    slides: [
      ["RECOMPRA", "O CorePet reconhece quando o cliente pode precisar comprar novamente.", "Menos dependência da memória da equipe."],
      ["RETENÇÃO", "O sistema identifica clientes que pararam de comprar.", "Cada regra pode preparar uma ação diferente."],
      ["LISTA DE ESPERA", "O produto voltou ao estoque?", "O cliente pode ser avisado automaticamente pelo app."],
    ],
  },
  {
    slug: "vendas24h",
    slides: [
      ["VENDA 24H", "A loja física fecha. O app e o e-commerce continuam.", "Seu catálogo permanece disponível ao cliente."],
      ["CATÁLOGO ÚNICO", "Cadastre uma vez.", "Produtos e preços seguem para todos os canais."],
      ["UMA OPERAÇÃO", "Pedidos de todos os canais em uma única gestão.", "Sem espalhar estoque e rotina."],
    ],
  },
  {
    slug: "resultados",
    slides: [
      ["VENDA NÃO É SÓ FATURAMENTO", "O CorePet mostra o que realmente ficou.", "Taxas, impostos, custos, comissão, lucro e margem."],
      ["DETALHE POR ITEM", "Abra a venda e veja o resultado de cada produto.", "Decisões com informação, não sensação."],
      ["EM TEMPO REAL", "Acompanhe o negócio sem esperar o fim do mês.", "Gestão para agir enquanto ainda há tempo."],
    ],
  },
  {
    slug: "duvidas",
    slides: [
      ["PRECISO TROCAR TUDO?", "A demonstração começa entendendo sua operação atual.", "A migração é avaliada de acordo com seu cenário."],
      ["FUNCIONA PARA LOJA PET?", "Sim. O CorePet integra venda, estoque, clientes e canais digitais.", "Clínica e banho & tosa terão conteúdos próprios."],
      ["COMO CONHECER?", "Clique em Falar no WhatsApp no perfil.", "Conte sua principal dor e agende uma demonstração.", "FALAR COM A COREPET"],
    ],
  },
  {
    slug: "demo",
    slides: [
      ["DEMONSTRAÇÃO GUIADA", "Nada de apresentação genérica.", "Mostramos o CorePet a partir das dores da sua operação."],
      ["AGENDAR DEMO", "Quer ver o sistema funcionando?", "Use o link do perfil e fale diretamente com a CorePet.", "QUERO CONHECER"],
    ],
  },
];

const reels = [
  {
    slug: "venda-mesmo-fechado",
    narration:
      "A loja fechou. As vendas não precisam. Com o CorePet, o mesmo catálogo fica disponível no app e no e-commerce, e os pedidos voltam para uma única operação. Venda, mesmo fechado. Conheça o CorePet.",
    scenes: [
      ["LOJA FECHADA", "As vendas não precisam.", "Venda, mesmo fechado.", assets.night],
      ["CATÁLOGO DISPONÍVEL", "App e e-commerce 24 horas.", "Um cadastro. Todos os canais.", assets.ecommerce],
      ["OPERAÇÃO CENTRALIZADA", "Pedidos e estoque no mesmo sistema.", "Sem espalhar a gestão.", assets.appProducts],
      ["COREPET", "Venda, mesmo fechado.", "Solicite uma demonstração.", null, "DEMONSTRAÇÃO"],
    ],
  },
  {
    slug: "seu-sistema-conversa",
    narration:
      "Dono de pet shop: seu sistema conversa com o cliente? O CorePet reconhece a provável recompra, identifica quem parou de comprar e avisa quando o produto volta ao estoque. Seu sistema não deveria apenas registrar vendas. Conheça o CorePet.",
    scenes: [
      ["PERGUNTA PARA O DONO", "Seu sistema conversa com o cliente?", "Ou só registra a venda?", assets.owner],
      ["RECOMPRA INTELIGENTE", "A próxima compra deixa sinais.", "O CorePet identifica a hora provável.", assets.recurrence],
      ["RETENÇÃO AUTOMÁTICA", "Quem parou de comprar não fica invisível.", "O sistema reconhece a oportunidade.", assets.retention],
      ["LISTA DE ESPERA", "O estoque voltou. O cliente fica sabendo.", "Aviso automático pelo app.", assets.waitlist],
      ["COREPET", "Entende. Conversa. Vende.", "Solicite uma demonstração.", null, "QUERO CONHECER"],
    ],
  },
  {
    slug: "sistema-que-vende",
    narration:
      "O que o seu sistema de pet shop não entrega? O CorePet conecta venda, estoque, resultado, app, e-commerce e automações. Faturamento vira análise. Histórico vira recompra. Estoque vira oportunidade. CorePet. Um sistema que trabalha para vender de novo.",
    scenes: [
      ["DIRETO AO PONTO", "O que seu sistema não entrega?", "O CorePet entrega.", assets.campaigns],
      ["RESULTADO", "Faturamento não é lucro.", "Veja margem e resultado venda por venda.", assets.results],
      ["VENDA ATIVA", "Histórico vira oportunidade.", "Recompra e retenção automáticas.", assets.recurrence],
      ["VENDA 24H", "App e e-commerce integrados.", "O cliente compra onde preferir.", assets.ecommerce],
      ["COREPET", "Seu sistema registra. O CorePet vende com você.", "Peça uma demonstração.", null, "PEDIR DEMO"],
    ],
  },
];

function escapeHtml(value = "") {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function fileUrl(path) {
  return pathToFileURL(path).href;
}

function brand(compact = false) {
  return `<div class="brand${compact ? " compact" : ""}"><img src="${fileUrl(logoPath)}"><strong>CorePet</strong></div>`;
}

function backgroundImage(image, position = "center") {
  if (!image) return "";
  return `<img class="background" src="${fileUrl(image)}" style="object-position:${position}"><div class="shade"></div>`;
}

function channelsMarkup() {
  return `<div class="channels"><figure class="browser"><img src="${fileUrl(assets.ecommerce)}"></figure><figure class="phone"><img src="${fileUrl(assets.appProducts)}"></figure></div>`;
}

function notificationMarkup(text) {
  if (!text) return "";
  return `<div class="notification"><span>C</span><div><b>CorePet</b><p>${escapeHtml(text)}</p></div></div>`;
}

function feedHtml(card) {
  const isLifestyle = card.layout === "lifestyle";
  const media =
    card.layout === "channels"
      ? channelsMarkup()
      : card.image
        ? `<figure class="screen${card.phone ? " phone-shot" : ""}"><img src="${fileUrl(card.image)}"><figcaption>${escapeHtml(card.badge || "TELA REAL DO COREPET")}</figcaption></figure>`
        : "";
  const lifestyle = isLifestyle ? backgroundImage(card.image, "center") : "";
  const titleSize = card.titleSize || (card.title.length > 42 ? 72 : 88);
  const accentTitleSize = card.accentTitleSize || (card.title.length > 42 ? 64 : 76);
  const bodySize = card.bodySize || 31;
  const screenHeight = card.screenHeight || 540;
  return `<!doctype html><html lang="pt-BR"><head><meta charset="utf-8"><style>${baseCss(1080, 1350)}
    .feed-copy{position:absolute;z-index:5;left:64px;right:64px;top:${isLifestyle ? 260 : 180}px;max-width:${isLifestyle ? 660 : 950}px}
    .feed-copy h1{font-size:${titleSize}px}.feed-copy .accent-title{font-size:${accentTitleSize}px}.feed-copy .body{font-size:${bodySize}px}
    .screen{left:64px;right:64px;bottom:72px;height:${screenHeight}px}.channels{left:84px;right:58px;bottom:92px;height:600px}
    ${isLifestyle ? ".shade{background:linear-gradient(90deg,#020817f8 0%,#031124e8 45%,#03112455 72%,transparent 100%),linear-gradient(0deg,#020817d8 0%,transparent 50%)}" : ""}
  </style></head><body>${lifestyle}${brand()}<main class="feed-copy"><p class="eyebrow" style="color:${card.accent}">${escapeHtml(card.eyebrow)}</p><h1>${escapeHtml(card.title)}</h1>${card.accentTitle ? `<h2 class="accent-title" style="color:${card.accent}">${escapeHtml(card.accentTitle)}</h2>` : ""}<p class="body">${escapeHtml(card.body)}</p>${card.chip ? `<span class="chip">${escapeHtml(card.chip)}</span>` : ""}</main>${isLifestyle ? notificationMarkup(card.notification) : media}<div class="footer">corepet.com.br</div></body></html>`;
}

function carouselHtml(slide, accent, index, total) {
  const media = slide.layout === "channels" ? channelsMarkup() : slide.image ? `<figure class="screen${slide.phone ? " phone-shot" : ""}"><img src="${fileUrl(slide.image)}"><figcaption>TELA REAL DO COREPET</figcaption></figure>` : "";
  const lifestyle = index === 0 && slide.image === assets.night ? backgroundImage(slide.image, "center") : "";
  return `<!doctype html><html lang="pt-BR"><head><meta charset="utf-8"><style>${baseCss(1080, 1350)}
    .carousel-copy{position:absolute;z-index:6;left:64px;right:64px;top:${lifestyle ? 245 : 188}px;max-width:950px}.carousel-copy h1{font-size:${slide.title.length > 46 ? 67 : 82}px}.carousel-copy .accent-title{font-size:63px}.screen{left:64px;right:64px;bottom:90px;height:510px}.channels{left:82px;right:54px;bottom:90px;height:560px}.step{display:inline-grid;place-items:center;width:72px;height:72px;border-radius:50%;background:${accent};color:#03251d;font-size:28px;font-weight:950;margin-bottom:22px}.progress{position:absolute;z-index:12;left:64px;right:64px;bottom:32px;display:flex;gap:8px}.progress i{height:5px;flex:1;border-radius:9px;background:#ffffff28}.progress i.on{background:${accent}}
  </style></head><body>${lifestyle}${brand()}<main class="carousel-copy">${slide.step ? `<span class="step">${slide.step}</span>` : `<p class="eyebrow" style="color:${accent}">${escapeHtml(slide.eyebrow)}</p>`}<h1>${escapeHtml(slide.title)}</h1>${slide.accentTitle ? `<h2 class="accent-title" style="color:${accent}">${escapeHtml(slide.accentTitle)}</h2>` : ""}<p class="body">${escapeHtml(slide.body)}</p>${slide.cta ? `<span class="cta" style="background:${accent}">${escapeHtml(slide.cta)}</span>` : ""}</main>${media}<div class="progress">${Array.from({ length: total }, (_, i) => `<i class="${i === index ? "on" : ""}"></i>`).join("")}</div></body></html>`;
}

function highlightHtml(label, icon) {
  return `<!doctype html><html lang="pt-BR"><head><meta charset="utf-8"><style>*{box-sizing:border-box}html,body{margin:0;width:1080px;height:1080px;overflow:hidden;font-family:Inter,"Segoe UI",Arial,sans-serif;color:#fff}body{display:grid;place-items:center;background:radial-gradient(circle at 75% 20%,#14b8a655,transparent 36%),radial-gradient(circle at 18% 82%,#7c3aed33,transparent 36%),linear-gradient(145deg,#020617,#0b1d2b 62%,#102a2c)}.ring{width:710px;height:710px;border:8px solid #34d399;border-radius:50%;display:grid;place-items:center;background:#061521ee;box-shadow:0 0 0 28px #ffffff0d,0 42px 120px #0009}.content{text-align:center}svg{width:250px;height:250px;fill:none;stroke:#d6ab35;stroke-width:1.7;stroke-linecap:round;stroke-linejoin:round}.label{margin-top:34px;font-size:53px;font-weight:900;letter-spacing:-1.4px}</style></head><body><div class="ring"><div class="content"><svg viewBox="0 0 24 24">${icon}</svg><div class="label">${escapeHtml(label)}</div></div></div></body></html>`;
}

function storyHtml(group, slide, index, total) {
  const [eyebrow, title, body, cta] = slide;
  return `<!doctype html><html lang="pt-BR"><head><meta charset="utf-8"><style>${baseCss(1080, 1920)}
    .story-copy{position:absolute;z-index:5;left:72px;right:72px;top:350px}.story-copy h1{font-size:${title.length > 48 ? 80 : 94}px}.story-copy .body{font-size:40px;max-width:880px}.story-number{position:absolute;right:74px;top:190px;color:#ffffff55;font-size:150px;font-weight:950}.story-accent{position:absolute;left:72px;top:270px;width:130px;height:8px;border-radius:8px;background:#34d399}.story-panel{position:absolute;left:72px;right:72px;bottom:420px;padding:38px;border:1px solid #ffffff22;border-radius:28px;background:#ffffff0a;box-shadow:0 28px 90px #0007}.story-panel p{margin:0;color:#dbeafe;font-size:31px;line-height:1.42}.story-progress{position:absolute;left:28px;right:28px;top:24px;display:flex;gap:7px}.story-progress i{height:6px;flex:1;border-radius:9px;background:#ffffff26}.story-progress i.on{background:#34d399}.safe-note{position:absolute;left:72px;bottom:250px;color:#93a4bc;font-size:22px;font-weight:700}.cta{font-size:25px;padding:20px 28px;margin-top:36px}
  </style></head><body>${brand()}<div class="story-progress">${Array.from({ length: total }, (_, i) => `<i class="${i === index ? "on" : ""}"></i>`).join("")}</div><span class="story-number">${String(index + 1).padStart(2, "0")}</span><span class="story-accent"></span><main class="story-copy"><p class="eyebrow">${escapeHtml(eyebrow)}</p><h1>${escapeHtml(title)}</h1><p class="body">${escapeHtml(body)}</p>${cta ? `<span class="cta">${escapeHtml(cta)}</span>` : ""}</main><div class="story-panel"><p>${escapeHtml(group.slug === "demo" ? "Demonstração guiada para donos e gestores de negócios pet." : "CorePet • ERP • App • E-commerce • Automação")}</p></div><div class="safe-note">@corepet.erp</div></body></html>`;
}

function reelFrameHtml(scene, index, total) {
  const [eyebrow, title, body, image, cta] = scene;
  const lifestyle = image === assets.night || image === assets.owner;
  const bg = image ? backgroundImage(image, lifestyle ? "center" : "center") : "";
  const screen = image && !lifestyle ? `<figure class="reel-screen"><img src="${fileUrl(image)}"><figcaption>TELA REAL DO COREPET</figcaption></figure>` : "";
  return `<!doctype html><html lang="pt-BR"><head><meta charset="utf-8"><style>${baseCss(1080, 1920)}
    ${lifestyle ? ".shade{background:linear-gradient(0deg,#020817f5 0%,#020817dc 54%,#02081738 100%),linear-gradient(90deg,#020817cc,transparent 78%)}" : ""}
    .reel-copy{position:absolute;z-index:7;left:72px;right:72px;top:500px}.reel-copy h1{font-size:${title.length > 42 ? 78 : 96}px}.reel-copy .body{font-size:38px;max-width:900px}.reel-screen{position:absolute;z-index:4;left:56px;right:56px;bottom:390px;height:640px;margin:0;padding:44px 12px 12px;border:2px solid #334155;border-radius:30px;background:#f8fafc;overflow:hidden;box-shadow:0 35px 100px #000a}.reel-screen img{width:100%;height:100%;object-fit:cover;border-radius:15px}.reel-screen figcaption{position:absolute;right:26px;top:15px;color:#334155;font-size:15px;font-weight:900;letter-spacing:.11em}.reel-steps{position:absolute;z-index:9;left:72px;right:72px;bottom:300px;display:flex;gap:9px}.reel-steps i{height:7px;flex:1;border-radius:8px;background:#ffffff2d}.reel-copy .cta{font-size:25px;padding:20px 28px;margin-top:36px}
  </style></head><body>${bg}${brand()}<main class="reel-copy"><p class="eyebrow">${escapeHtml(eyebrow)}</p><h1>${escapeHtml(title)}</h1><p class="body">${escapeHtml(body)}</p>${cta ? `<span class="cta">${escapeHtml(cta)}</span>` : ""}</main>${screen}<div class="reel-steps">${Array.from({ length: total }, (_, i) => `<i class="${i === index ? "on" : ""}"></i>`).join("")}</div><div class="footer">corepet.com.br</div></body></html>`;
}

function baseCss(width, height) {
  return `*{box-sizing:border-box}html,body{margin:0;width:${width}px;height:${height}px;overflow:hidden;font-family:Inter,"Segoe UI",Arial,sans-serif;background:#020817;color:#fff}body{position:relative;background:radial-gradient(circle at 82% 16%,#0f766e55,transparent 34%),radial-gradient(circle at 12% 88%,#7c3aed2b,transparent 38%),linear-gradient(145deg,#020617 0%,#081426 60%,#111827 100%)}body:after{content:"";position:absolute;inset:0;pointer-events:none;background-image:linear-gradient(#ffffff08 1px,transparent 1px),linear-gradient(90deg,#ffffff08 1px,transparent 1px);background-size:54px 54px;mask-image:linear-gradient(to bottom,#000,transparent 90%)}.background{position:absolute;inset:0;width:100%;height:100%;object-fit:cover}.shade{position:absolute;inset:0;background:linear-gradient(0deg,#020817f7 0%,#020817c9 46%,#02081738 100%)}.brand{position:absolute;z-index:20;left:64px;top:56px;display:flex;align-items:center;gap:15px}.brand img{width:62px;height:62px;border-radius:16px;box-shadow:0 18px 50px #0008}.brand strong{font-size:38px;letter-spacing:-1.2px}.brand.compact img{width:50px;height:50px}.brand.compact strong{font-size:31px}.eyebrow{margin:0;color:#34d399;font-size:22px;font-weight:950;letter-spacing:.14em}.feed-copy h1,.carousel-copy h1,.story-copy h1,.reel-copy h1{margin:18px 0 0;line-height:.98;letter-spacing:-4px}.accent-title{margin:12px 0 0;line-height:1.02;letter-spacing:-3px}.body{margin:26px 0 0;color:#dbeafe;font-size:31px;line-height:1.34;font-weight:650}.chip,.cta{display:inline-block;margin-top:34px;padding:17px 25px;border-radius:14px;background:#34d399;color:#03251d;font-size:18px;font-weight:950;letter-spacing:.07em}.screen{position:absolute;z-index:4;margin:0;padding:47px 12px 12px;border:3px solid #27364b;border-radius:27px;background:#f8fafc;overflow:hidden;box-shadow:0 34px 100px #000a}.screen:before{content:"";position:absolute;left:22px;top:20px;width:12px;height:12px;border-radius:50%;background:#fb7185;box-shadow:22px 0 #fbbf24,44px 0 #34d399}.screen img{width:100%;height:100%;object-fit:cover;border-radius:12px}.screen figcaption{position:absolute;right:25px;top:17px;color:#334155;font-size:15px;font-weight:950;letter-spacing:.11em}.phone-shot img{object-fit:contain;background:#eef2f7}.channels{position:absolute;z-index:4}.browser{position:absolute;right:0;top:0;width:78%;height:82%;margin:0;padding:16px;border:2px solid #334155;border-radius:24px;background:#f8fafc;box-shadow:0 35px 90px #0009;overflow:hidden}.browser img{width:100%;height:100%;object-fit:cover;border-radius:12px}.phone{position:absolute;z-index:3;left:0;bottom:0;width:34%;height:84%;margin:0;padding:9px;border:7px solid #101827;border-radius:48px;background:#0f172a;box-shadow:0 35px 90px #000b;overflow:hidden}.phone img{width:100%;height:100%;object-fit:cover;border-radius:36px}.notification{position:absolute;z-index:8;left:64px;right:64px;bottom:120px;display:flex;gap:18px;align-items:center;padding:26px;border:1px solid #ffffff24;border-radius:23px;background:#111c31e8;box-shadow:0 28px 80px #0009}.notification>span{display:grid;place-items:center;width:66px;height:66px;border-radius:18px;background:#34d399;color:#05392e;font-size:31px;font-weight:950}.notification b{font-size:25px}.notification p{margin:5px 0 0;color:#dbeafe;font-size:23px;line-height:1.25}.footer{position:absolute;z-index:20;right:48px;bottom:30px;color:#ffffffb5;font-size:18px;font-weight:850;letter-spacing:.04em}`;
}

function capture(html, outputPath, width, height) {
  mkdirSync(dirname(outputPath), { recursive: true });
  const htmlPath = join(workDir, `${outputPath.replaceAll(/[\\/:]/g, "-")}.html`);
  writeFileSync(htmlPath, html, "utf8");
  const result = spawnSync(
    chrome,
    [
      "--headless=new",
      "--hide-scrollbars",
      "--disable-gpu",
      "--allow-file-access-from-files",
      `--window-size=${width},${height}`,
      "--force-device-scale-factor=1",
      `--screenshot=${outputPath}`,
      fileUrl(htmlPath),
    ],
    { encoding: "utf8", stdio: "pipe" },
  );
  if (result.status !== 0 || !existsSync(outputPath)) {
    throw new Error(result.stderr || result.stdout || `Falha ao gerar ${outputPath}`);
  }
}

function run(command, args, label) {
  const result = spawnSync(command, args, { encoding: "utf8", stdio: "pipe" });
  if (result.status !== 0) {
    throw new Error(`${label}: ${result.stderr || result.stdout}`);
  }
}

function mediaDuration(path) {
  const result = spawnSync(
    ffprobe,
    ["-v", "error", "-show_entries", "format=duration", "-of", "default=nw=1:nk=1", path],
    { encoding: "utf8", stdio: "pipe" },
  );
  const value = Number.parseFloat(result.stdout.trim());
  if (result.status !== 0 || !Number.isFinite(value)) {
    throw new Error(`Não foi possível medir a duração de ${path}`);
  }
  return value;
}

function renderReel(reel) {
  const reelWork = join(workDir, "reels", reel.slug);
  mkdirSync(reelWork, { recursive: true });
  const output = join(outputDir, "reels", `reel-${reel.slug}.mp4`);
  const frames = reel.scenes.map((scene, index) => {
    const frame = join(reelWork, `frame-${String(index + 1).padStart(2, "0")}.png`);
    capture(reelFrameHtml(scene, index, reel.scenes.length), frame, 1080, 1920);
    return frame;
  });
  const audio =
    customReelAudio ||
    join(reelWork, reuseReelAudio ? "narracao.m4a" : "narracao.mp3");
  if (customReelAudio) {
    if (!existsSync(customReelAudio)) {
      throw new Error(`Narração personalizada não encontrada: ${customReelAudio}`);
    }
  } else if (reuseReelAudio && existsSync(output)) {
    run(
      ffmpeg,
      ["-y", "-i", output, "-vn", "-c:a", "copy", audio],
      `Áudio existente de ${reel.slug}`,
    );
  } else {
    run(
      edgeTts,
      [
        "--voice",
        "pt-BR-AntonioNeural",
        "--rate=+5%",
        "--text",
        reel.narration,
        "--write-media",
        audio,
      ],
      `Narração de ${reel.slug}`,
    );
  }
  const audioSeconds = mediaDuration(audio);
  const sceneSeconds = Math.max(3.1, audioSeconds / reel.scenes.length + 0.18);
  const segments = frames.map((frame, index) => {
    const segment = join(reelWork, `segment-${String(index + 1).padStart(2, "0")}.mp4`);
    const frameCount = Math.ceil(sceneSeconds * 30);
    const fadeOut = Math.max(0.2, sceneSeconds - 0.24).toFixed(2);
    const motionFilter =
      reelMotion === "zoom"
        ? `zoompan=z='min(zoom+0.00028,1.035)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=${frameCount}:s=1080x1920:fps=30`
        : "scale=1080:1920:flags=lanczos,fps=30";
    run(
      ffmpeg,
      [
        "-y",
        "-loop",
        "1",
        "-framerate",
        "30",
        "-i",
        frame,
        "-t",
        sceneSeconds.toFixed(2),
        "-vf",
        `${motionFilter},fade=t=in:st=0:d=0.18,fade=t=out:st=${fadeOut}:d=0.22,format=yuv420p`,
        "-an",
        "-c:v",
        "libx264",
        "-preset",
        "medium",
        "-crf",
        "19",
        "-pix_fmt",
        "yuv420p",
        segment,
      ],
      `Cena ${index + 1} de ${reel.slug}`,
    );
    return segment;
  });
  const concatFile = join(reelWork, "concat.txt");
  writeFileSync(
    concatFile,
    segments.map((segment) => `file '${segment.replaceAll("'", "'\\''")}'`).join("\n"),
    "utf8",
  );
  mkdirSync(dirname(output), { recursive: true });
  run(
    ffmpeg,
    [
      "-y",
      "-f",
      "concat",
      "-safe",
      "0",
      "-i",
      concatFile,
      "-i",
      audio,
      "-c:v",
      "copy",
      "-c:a",
      "aac",
      "-b:a",
      "192k",
      "-shortest",
      "-movflags",
      "+faststart",
      output,
    ],
    `Vídeo ${reel.slug}`,
  );
  copyFileSync(frames[0], join(outputDir, "reels", `reel-${reel.slug}-poster.png`));
}

for (const required of [chrome, logoPath, ...Object.values(assets)]) {
  if (!existsSync(required)) throw new Error(`Arquivo obrigatório não encontrado: ${required}`);
}

rmSync(workDir, { recursive: true, force: true });
mkdirSync(workDir, { recursive: true });
mkdirSync(outputDir, { recursive: true });

if (!onlyReel) {
  for (const card of feedCards) {
    capture(feedHtml(card), join(outputDir, "feed", card.file), 1080, 1350);
  }

  for (const carousel of carousels) {
    carousel.slides.forEach((slide, index) => {
      capture(
        carouselHtml(slide, carousel.accent, index, carousel.slides.length),
        join(
          outputDir,
          "carousels",
          carousel.slug,
          `${String(index + 1).padStart(2, "0")}.png`,
        ),
        1080,
        1350,
      );
    });
  }

  for (const [slug, label, icon] of highlights) {
    capture(
      highlightHtml(label, icon),
      join(outputDir, "highlights", `destaque-${slug}.png`),
      1080,
      1080,
    );
  }

  for (const group of storyGroups) {
    group.slides.forEach((slide, index) => {
      capture(
        storyHtml(group, slide, index, group.slides.length),
        join(
          outputDir,
          "stories",
          group.slug,
          `${String(index + 1).padStart(2, "0")}.png`,
        ),
        1080,
        1920,
      );
    });
  }
}

for (const reel of reels) {
  if (onlyReel && reel.slug !== onlyReel) continue;
  const videoPath = join(outputDir, "reels", `reel-${reel.slug}.mp4`);
  const posterPath = join(outputDir, "reels", `reel-${reel.slug}-poster.png`);
  if (!rebuildReels && existsSync(videoPath) && existsSync(posterPath)) {
    console.log(`Reel existente preservado: ${reel.slug}`);
    continue;
  }
  renderReel(reel);
}

console.log(`Kit profissional do Instagram gerado em ${outputDir}`);
