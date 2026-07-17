import { existsSync, mkdirSync, rmSync, writeFileSync } from "node:fs";
import { basename, dirname, join } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import { spawnSync } from "node:child_process";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const publicDir = join(root, "frontend", "public", "marketing");
const shotsDir = join(publicDir, "product-shots");
const capturesDir = join(root, "runtime", "marketing-captures");
const workDir = join(root, "runtime", "marketing-feature-series");
const chrome =
  process.env.CHROME_PATH ||
  "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";
const ffmpeg = process.env.FFMPEG_PATH || "ffmpeg";
const ffprobe = process.env.FFPROBE_PATH || "ffprobe";
const edgeTts = process.env.EDGE_TTS_PATH || "edge-tts";
const logoPath = join(
  root,
  "frontend",
  "public",
  "brand",
  "corepet",
  "corepet-icon-192.png",
);

const videos = [
  {
    slug: "recorrencia-inteligente",
    voice:
      "Quando o cliente compra ração ou outro produto recorrente, a próxima venda já deixa sinais. O CorePet aprende o intervalo de consumo, identifica a data provável da recompra e prepara o lembrete automaticamente. No momento certo, o cliente recebe a notificação pelo app e pode comprar novamente. Sua equipe não precisa lembrar de tudo. O CorePet trabalha para vender de novo.",
    scenes: [
      {
        mode: "screen",
        image: join(shotsDir, "erp-recorrencia.png"),
        eyebrow: "Recorrência inteligente",
        title: "A próxima venda já deixou sinais.",
        body: "O histórico de consumo mostra quando a recompra deve acontecer.",
        accent: "#34d399",
      },
      {
        mode: "screen",
        image: join(shotsDir, "erp-recorrencia.png"),
        eyebrow: "Automação",
        title: "O CorePet identifica a data provável da recompra.",
        body: "Rações, antipulgas e protocolos deixam de depender da memória da equipe.",
        accent: "#8b5cf6",
        focus: {
          left: 5,
          top: 59,
          width: 90,
          height: 13,
          label: "Próxima oportunidade",
        },
      },
      {
        mode: "notification",
        background: join(shotsDir, "erp-recorrencia.png"),
        phone: join(shotsDir, "app-inicio.png"),
        eyebrow: "Notificação automática pelo app",
        title: "O produto certo. No momento certo.",
        body: "O cliente recebe o lembrete e pode comprar novamente pelo app.",
        notificationTitle: "Sua ração está acabando?",
        notificationBody: "Peça novamente pelo app.",
        accent: "#34d399",
      },
    ],
  },
  {
    slug: "lista-espera-automatica",
    voice:
      "Produto sem estoque não precisa ser venda perdida. No PDV, o atendente registra o interesse do cliente na lista de espera. Quando o produto volta ao estoque, o CorePet identifica a reposição e avisa o cliente automaticamente pelo app. A loja recupera uma oportunidade que normalmente seria esquecida, sem depender de anotações ou tarefas manuais.",
    scenes: [
      {
        mode: "screen",
        image: join(shotsDir, "pdv-lista-espera.png"),
        eyebrow: "Lista de espera no PDV",
        title: "Sem estoque não precisa ser venda perdida.",
        body: "O atendente registra o produto que o cliente quer comprar.",
        accent: "#f59e0b",
      },
      {
        mode: "screen",
        image: join(shotsDir, "pdv-lista-espera.png"),
        eyebrow: "Processo automático",
        title: "Quando o produto entra, o sistema reconhece.",
        body: "A reposição ativa o aviso sem criar mais uma tarefa para a equipe.",
        accent: "#f59e0b",
        copyStyle: "top:90px;bottom:auto;width:650px",
        focus: {
          left: 32.5,
          top: 70.5,
          width: 35,
          height: 9,
          label: "Aviso automático pelo app",
        },
      },
      {
        mode: "notification",
        background: join(shotsDir, "pdv-lista-espera.png"),
        phone: join(shotsDir, "app-inicio.png"),
        eyebrow: "A oportunidade volta para a loja",
        title: "O estoque voltou. O cliente fica sabendo.",
        body: "O CorePet transforma reposição de estoque em nova chance de venda.",
        notificationTitle: "O produto que você queria chegou!",
        notificationBody: "Abra o app e faça seu pedido.",
        accent: "#f59e0b",
      },
    ],
  },
  {
    slug: "ecossistema-integrado",
    voice:
      "No CorePet, produto não precisa ser cadastrado três vezes. Você cadastra no ERP e ele fica disponível no app e no e-commerce. Pedidos feitos em qualquer canal entram na mesma operação, e o estoque é atualizado automaticamente. Seu cliente compra vinte e quatro horas por dia, enquanto o gestor mantém tudo centralizado em um único sistema.",
    scenes: [
      {
        mode: "screen",
        image: join(capturesDir, "02-produtos-canais-estoque.png"),
        eyebrow: "Cadastro único",
        title: "Cadastre uma vez no ERP.",
        body: "Produtos, preços e disponibilidade partem de uma única operação.",
        accent: "#3b82f6",
        focus: {
          left: 83.5,
          top: 62,
          width: 7.5,
          height: 34,
          label: "App + E-commerce",
        },
      },
      {
        mode: "channels",
        ecommerce: join(shotsDir, "ecommerce-catalogo.png"),
        app: join(shotsDir, "app-produtos.png"),
        eyebrow: "Venda disponível 24 horas",
        title: "O mesmo catálogo no app e no e-commerce.",
        body: "O cliente escolhe onde comprar. A loja continua com uma única gestão.",
        accent: "#3b82f6",
      },
      {
        mode: "ecosystem",
        erp: join(capturesDir, "02-produtos-canais-estoque.png"),
        app: join(shotsDir, "app-produtos.png"),
        ecommerce: join(shotsDir, "ecommerce-catalogo.png"),
        eyebrow: "Um único ecossistema",
        title: "ERP + App + E-commerce. Tudo integrado.",
        body: "Cada pedido atualiza a operação e o estoque, independentemente do canal.",
        accent: "#34d399",
      },
    ],
  },
  {
    slug: "resultado-venda-por-venda",
    outputName: "corepet-resultado-venda-por-venda.mp4",
    posterName: "corepet-resultado-venda-por-venda-poster.jpg",
    posterScene: 2,
    voice:
      "Faturamento sozinho não mostra se a venda deu resultado. No CorePet, cada venda apresenta o valor líquido, os impostos, as comissões, o custo dos produtos, o lucro e a margem. Ao expandir uma venda, o gestor também vê os produtos e o resultado de cada item. Assim, ele entende exatamente onde ganhou dinheiro e onde precisa agir.",
    scenes: [
      {
        mode: "screen",
        image: join(shotsDir, "erp-resultado.png"),
        eyebrow: "Gestão em tempo real",
        title: "Venda não é faturamento. É resultado.",
        body: "Taxas, impostos, custos, lucro e margem aparecem sem esperar o fechamento do mês.",
        accent: "#f59e0b",
      },
      {
        mode: "screen",
        image: join(capturesDir, "05-vendas-lista.png"),
        eyebrow: "Resultado venda por venda",
        title: "Cada venda mostra o que realmente aconteceu.",
        body: "O gestor acompanha valor líquido, custos, lucro e margem em tempo real.",
        accent: "#f59e0b",
        copyStyle: "top:90px;bottom:auto;width:720px",
        focus: {
          left: 3,
          top: 49,
          width: 94,
          height: 10,
          label: "Resultado individual da venda",
        },
      },
      {
        mode: "screen",
        image: join(shotsDir, "erp-venda-expandida.png"),
        eyebrow: "Detalhe completo",
        title: "Abra a venda e veja os produtos.",
        body: "O resultado também aparece por item, com custo, lucro e margem.",
        accent: "#34d399",
        fit: "contain",
        maskSourceLogo: true,
        copyStyle: "top:90px;bottom:auto;width:690px",
        focus: {
          left: 2,
          top: 56.5,
          width: 96,
          height: 20,
          label: "Venda aberta: produtos e resultado por item",
        },
      },
    ],
  },
  {
    slug: "motor-campanhas",
    voice:
      "Campanha não precisa ser uma ação solta. No CorePet, fidelidade, cupons, retenção e notificações do app ficam no mesmo motor. A loja pode criar regras automáticas para clientes inativos e também ofertas por validade. Quando a regra identifica a oportunidade, o sistema prepara a ação e publica nos canais definidos. Menos operação manual e mais clientes voltando a comprar.",
    scenes: [
      {
        mode: "screen",
        image: join(shotsDir, "erp-campanhas.png"),
        eyebrow: "Motor de campanhas",
        title: "Relacionamento e venda em uma única central.",
        body: "Fidelidade, cupons, ranking, retenção e notificações do app trabalham juntos.",
        accent: "#14b8a6",
      },
      {
        mode: "screen",
        image: join(shotsDir, "erp-campanhas-retencao.png"),
        eyebrow: "Retenção automática",
        title: "O sistema identifica quem parou de comprar.",
        body: "Cada regra pode disparar uma ação diferente conforme os dias de inatividade.",
        accent: "#f97316",
        copyStyle: "top:90px;bottom:auto;width:700px",
        focus: {
          left: 11,
          top: 70,
          width: 78,
          height: 12,
          label: "Regra automática de retenção",
        },
      },
      {
        mode: "screen",
        image: join(shotsDir, "erp-campanhas-validade.png"),
        eyebrow: "Oferta por validade",
        title: "A oportunidade entra sozinha na campanha.",
        body: "O lote elegível é publicado no app e no site com o desconto configurado.",
        accent: "#34d399",
        copyStyle: "top:90px;bottom:auto;width:700px",
        focus: {
          left: 11,
          top: 70,
          width: 78,
          height: 15,
          label: "Campanha automática por validade",
        },
      },
    ],
  },
  {
    slug: "entregas-rotas-custos",
    voice:
      "A entrega também precisa dar resultado. No CorePet, o gestor acompanha as rotas, o entregador, as paradas e o andamento da operação. Depois, o painel financeiro mostra o custo total, o custo da moto, o repasse e o custo médio por entrega. O sistema ainda alerta quando uma despesa foge do esperado. Assim, a loja entrega melhor sem perder margem no caminho.",
    scenes: [
      {
        mode: "screen",
        image: join(shotsDir, "erp-rotas.png"),
        eyebrow: "Operação de entregas",
        title: "Rotas, entregadores e paradas sob controle.",
        body: "Acompanhe o que está em rota e abra o rastreio da entrega em tempo real.",
        accent: "#3b82f6",
      },
      {
        mode: "screen",
        image: join(shotsDir, "erp-rotas.png"),
        eyebrow: "Acompanhamento operacional",
        title: "Saiba quem está na rua e qual é a próxima entrega.",
        body: "Distância, tempo previsto, endereço e status ficam na mesma visão.",
        accent: "#3b82f6",
        fit: "contain",
        maskSourceLogo: true,
        copyStyle: "top:90px;bottom:auto;width:760px",
        focus: {
          left: 1,
          top: 54.8,
          width: 98,
          height: 30.5,
          label: "Detalhes da rota em andamento",
        },
      },
      {
        mode: "screen",
        image: join(shotsDir, "erp-entregas-financeiro.png"),
        eyebrow: "Custo real da entrega",
        title: "Entregar também precisa preservar a margem.",
        body: "Custos, repasses, alertas e custo médio aparecem em tempo real.",
        accent: "#8b5cf6",
        copyStyle: "top:90px;bottom:auto;width:720px",
        focus: {
          left: 11,
          top: 59,
          width: 78,
          height: 36,
          label: "Custos e repasses da operação",
        },
      },
    ],
  },
];

function run(command, args, label) {
  const result = spawnSync(command, args, { encoding: "utf8", stdio: "pipe" });
  if (result.status !== 0) {
    throw new Error(`${label} falhou:\n${result.stderr || result.stdout}`);
  }
  return result.stdout.trim();
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function assetUrl(path) {
  if (!existsSync(path)) throw new Error(`Asset não encontrado: ${path}`);
  return pathToFileURL(path).href;
}

function brand() {
  return `<div class="brand"><img src="${assetUrl(logoPath)}" alt=""><strong>CorePet</strong></div>`;
}

function copyBlock(scene) {
  return `<div class="copy-card" style="--accent:${scene.accent};${scene.copyStyle || ""}">
    <div class="eyebrow">${escapeHtml(scene.eyebrow)}</div>
    <h1>${escapeHtml(scene.title)}</h1>
    <p>${escapeHtml(scene.body)}</p>
  </div>`;
}

function focusBlock(focus, accent) {
  if (!focus) return "";
  return `<div class="focus" style="left:${focus.left}%;top:${focus.top}%;width:${focus.width}%;height:${focus.height}%;--accent:${accent}">
    <span>${escapeHtml(focus.label)}</span>
  </div>`;
}

function screenScene(scene) {
  return `<div class="screen-wrap">
    <img class="screen-image" src="${assetUrl(scene.image)}" alt="" style="object-fit:${scene.fit || "cover"};transform:scale(${scene.zoom || 1});transform-origin:${scene.origin || "center"}">
    ${scene.maskSourceLogo ? '<div class="source-corner-mask"></div>' : ""}
    ${focusBlock(scene.focus, scene.accent)}
  </div>${copyBlock(scene)}`;
}

function notificationScene(scene) {
  return `<div class="ambient" style="background-image:url('${assetUrl(scene.background)}')"></div>
    <div class="notification-layout">
      ${copyBlock(scene)}
      <div class="phone">
        <img src="${assetUrl(scene.phone)}" alt="">
        <div class="push" style="--accent:${scene.accent}">
          <div class="push-brand"><span>C</span><strong>CorePet</strong></div>
          <h2>${escapeHtml(scene.notificationTitle)}</h2>
          <p>${escapeHtml(scene.notificationBody)}</p>
          <button>ABRIR O APP</button>
        </div>
      </div>
    </div>`;
}

function channelsScene(scene) {
  return `<div class="channels-copy">${copyBlock(scene)}</div>
    <div class="channels">
      <div class="browser-card"><div class="window-title">● ● ● &nbsp; E-COMMERCE</div><img src="${assetUrl(scene.ecommerce)}" alt=""></div>
      <div class="phone compact"><img src="${assetUrl(scene.app)}" alt=""></div>
    </div>`;
}

function ecosystemScene(scene) {
  return `<div class="ecosystem-copy">${copyBlock(scene)}</div>
    <div class="ecosystem">
      <div class="eco-card erp"><span>ERP</span><img src="${assetUrl(scene.erp)}" alt=""></div>
      <div class="eco-card app"><span>APP</span><img src="${assetUrl(scene.app)}" alt=""></div>
      <div class="eco-card ecommerce"><span>E-COMMERCE</span><img src="${assetUrl(scene.ecommerce)}" alt=""></div>
    </div>`;
}

function sceneHtml(scene) {
  const content =
    scene.mode === "notification"
      ? notificationScene(scene)
      : scene.mode === "channels"
        ? channelsScene(scene)
        : scene.mode === "ecosystem"
          ? ecosystemScene(scene)
          : screenScene(scene);

  return `<!doctype html><html><head><meta charset="utf-8"><style>
    *{box-sizing:border-box}html,body{margin:0;width:1920px;height:1080px;overflow:hidden;font-family:Inter,Segoe UI,Arial,sans-serif;background:#020617;color:#fff}
    body{position:relative;background:radial-gradient(circle at 82% 12%,rgba(20,184,166,.24),transparent 30%),linear-gradient(135deg,#020617 0%,#07152a 58%,#111827 100%)}
    .brand{position:absolute;z-index:20;top:30px;left:42px;height:54px;display:flex;align-items:center;gap:14px;padding:8px 18px 8px 9px;border:1px solid rgba(255,255,255,.16);border-radius:17px;background:rgba(2,6,23,.78);box-shadow:0 14px 40px rgba(0,0,0,.25)}
    .brand img{width:38px;height:38px;border-radius:10px}.brand strong{font-size:24px;letter-spacing:-.4px}
    .screen-wrap{position:absolute;inset:0;background:#f8fafc;overflow:hidden}.screen-image{width:100%;height:100%;object-fit:cover;transition:none}
    .source-corner-mask{position:absolute;z-index:3;left:0;top:0;width:64px;height:92px;background:#f8fafc}
    .screen-wrap:after{content:"";position:absolute;inset:0;background:linear-gradient(180deg,rgba(2,6,23,.05) 50%,rgba(2,6,23,.78) 100%)}
    .copy-card{position:absolute;z-index:10;left:54px;bottom:48px;width:min(860px,72vw);padding:25px 30px 26px;border:1px solid rgba(255,255,255,.18);border-left:7px solid var(--accent);border-radius:22px;background:rgba(2,6,23,.88);box-shadow:0 22px 70px rgba(0,0,0,.34);backdrop-filter:blur(12px)}
    .eyebrow{font-size:18px;font-weight:900;letter-spacing:.18em;text-transform:uppercase;color:var(--accent)}
    .copy-card h1{margin:11px 0 0;font-size:47px;line-height:1.03;letter-spacing:-1.7px}.copy-card p{margin:14px 0 0;font-size:23px;line-height:1.35;color:#dbeafe}
    .focus{position:absolute;z-index:8;border:5px solid var(--accent);border-radius:18px;box-shadow:0 0 0 9999px rgba(2,6,23,.58),0 0 40px color-mix(in srgb,var(--accent) 65%,transparent)}
    .focus span{position:absolute;right:0;top:-58px;padding:12px 18px;border-radius:13px;background:var(--accent);color:#07111f;font-size:21px;font-weight:900;white-space:nowrap;box-shadow:0 12px 30px rgba(0,0,0,.25)}
    .ambient{position:absolute;inset:0;background-position:center;background-size:cover;filter:blur(5px) brightness(.28);transform:scale(1.04)}
    .notification-layout{position:absolute;inset:0;display:grid;grid-template-columns:1fr 680px;align-items:center;gap:70px;padding:110px 120px 60px}
    .notification-layout .copy-card,.channels-copy .copy-card,.ecosystem-copy .copy-card{position:relative;left:auto;bottom:auto;width:auto;background:transparent;border:0;border-left:7px solid var(--accent);box-shadow:none;backdrop-filter:none;border-radius:0;padding:8px 0 8px 28px}
    .notification-layout .copy-card h1,.channels-copy .copy-card h1,.ecosystem-copy .copy-card h1{font-size:62px}.notification-layout .copy-card p,.channels-copy .copy-card p,.ecosystem-copy .copy-card p{font-size:27px;max-width:800px}
    .phone{position:relative;margin:auto;width:500px;height:870px;padding:18px;border:9px solid #0f172a;border-radius:66px;background:#fff;overflow:hidden;box-shadow:0 35px 100px rgba(0,0,0,.55)}
    .phone:before{content:"";position:absolute;z-index:3;top:10px;left:50%;width:150px;height:30px;transform:translateX(-50%);border-radius:20px;background:#0f172a}
    .phone>img{width:100%;height:100%;object-fit:cover;object-position:top;border-radius:42px}
    .push{position:absolute;z-index:4;left:34px;right:34px;bottom:88px;padding:24px;border:2px solid color-mix(in srgb,var(--accent) 72%,#fff);border-radius:24px;background:rgba(7,20,42,.95);color:#fff;box-shadow:0 22px 60px rgba(0,0,0,.45)}
    .push-brand{display:flex;align-items:center;gap:12px;color:#dbeafe;font-size:18px}.push-brand span{display:grid;place-items:center;width:38px;height:38px;border-radius:11px;background:var(--accent);color:#06221b;font-weight:1000}
    .push h2{margin:16px 0 7px;font-size:30px;line-height:1.08}.push p{margin:0;color:#cbd5e1;font-size:20px}.push button{margin-top:19px;width:100%;padding:15px;border:0;border-radius:13px;background:var(--accent);color:#06101f;font-weight:1000;font-size:18px}
    .channels-copy,.ecosystem-copy{position:absolute;left:70px;top:120px;width:720px;z-index:8}.channels{position:absolute;right:70px;top:105px;width:1040px;height:880px}
    .browser-card{position:absolute;right:0;top:40px;width:990px;height:670px;padding:52px 12px 12px;border:4px solid #1e293b;border-radius:28px;background:#fff;overflow:hidden;box-shadow:0 30px 90px rgba(0,0,0,.48);transform:rotate(1deg)}
    .window-title{position:absolute;left:20px;top:16px;color:#f97316;font-size:18px;font-weight:900;letter-spacing:.12em}.browser-card img{width:100%;height:100%;object-fit:cover;object-position:top;border-radius:12px}
    .phone.compact{position:absolute;z-index:5;left:15px;bottom:0;width:330px;height:690px;transform:rotate(-3deg)}
    .ecosystem{position:absolute;left:760px;right:55px;top:120px;bottom:60px}.eco-card{position:absolute;padding:47px 10px 10px;border:4px solid #1e293b;border-radius:26px;background:#fff;overflow:hidden;box-shadow:0 28px 80px rgba(0,0,0,.45)}
    .eco-card span{position:absolute;top:14px;left:20px;color:#0f172a;font-size:18px;font-weight:1000;letter-spacing:.13em}.eco-card img{width:100%;height:100%;object-fit:cover;object-position:top;border-radius:12px}
    .eco-card.erp{left:0;top:0;width:910px;height:480px}.eco-card.ecommerce{right:0;bottom:0;width:870px;height:470px}.eco-card.app{z-index:5;left:390px;top:260px;width:300px;height:620px;padding-top:40px;border-radius:48px}.eco-card.app img{object-fit:cover}.eco-card.app span{color:#0f172a}
    .footer-mark{position:absolute;z-index:30;right:38px;bottom:24px;font-size:16px;font-weight:800;color:rgba(255,255,255,.72);letter-spacing:.06em}
  </style></head><body>${brand()}${content}<div class="footer-mark">corepet.com.br</div></body></html>`;
}

function captureScene(scene, videoSlug, index) {
  const htmlPath = join(workDir, `${videoSlug}-${index}.html`);
  const pngPath = join(workDir, `${videoSlug}-${index}.png`);
  writeFileSync(htmlPath, sceneHtml(scene), "utf8");
  run(
    chrome,
    [
      "--headless=new",
      "--hide-scrollbars",
      "--disable-gpu",
      "--allow-file-access-from-files",
      "--window-size=1920,1080",
      "--force-device-scale-factor=1",
      `--screenshot=${pngPath}`,
      pathToFileURL(htmlPath).href,
    ],
    `Captura da cena ${videoSlug}/${index + 1}`,
  );
  return pngPath;
}

function audioDuration(path) {
  return Number(
    run(
      ffprobe,
      [
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=nw=1:nk=1",
        path,
      ],
      `Leitura da duração de ${path}`,
    ),
  );
}

function generateVoice(text, outputPath) {
  const args = [
    "--voice",
    "pt-BR-AntonioNeural",
    "--rate=-4%",
    "--pitch=-2Hz",
    "--text",
    text,
    "--write-media",
    outputPath,
  ];
  let lastError = "";
  for (let attempt = 1; attempt <= 5; attempt += 1) {
    const result = spawnSync(edgeTts, args, {
      encoding: "utf8",
      stdio: "pipe",
    });
    if (result.status === 0 && existsSync(outputPath)) return;
    lastError =
      result.stderr || result.stdout || `tentativa ${attempt} sem saída`;
    Atomics.wait(
      new Int32Array(new SharedArrayBuffer(4)),
      0,
      0,
      attempt * 1200,
    );
  }
  throw new Error(
    `Narração humanizada de ${basename(outputPath)} falhou:\n${lastError}`,
  );
}

function renderVideo(video, images, audioPath, paddingSeconds = 1.1) {
  const outputPath = join(
    publicDir,
    video.outputName || `corepet-demo-${video.slug}.mp4`,
  );
  const posterPath = join(
    publicDir,
    video.posterName || `corepet-demo-${video.slug}-poster.jpg`,
  );
  const transition = 0.45;
  const targetDuration = audioDuration(audioPath) + paddingSeconds;
  const sceneDuration =
    (targetDuration + transition * (images.length - 1)) / images.length;
  const inputs = images.flatMap((image) => [
    "-loop",
    "1",
    "-t",
    sceneDuration.toFixed(3),
    "-i",
    image,
  ]);
  const normalized = images
    .map(
      (_, index) =>
        `[${index}:v]scale=1920:1080,fps=30,format=yuv420p[v${index}]`,
    )
    .join(";");
  const transitions = [];
  let previous = "v0";
  let elapsed = sceneDuration;
  for (let index = 1; index < images.length; index += 1) {
    const output = index === images.length - 1 ? "video" : `x${index}`;
    transitions.push(
      `[${previous}][v${index}]xfade=transition=fade:duration=${transition}:offset=${(elapsed - transition).toFixed(3)}[${output}]`,
    );
    previous = output;
    elapsed += sceneDuration - transition;
  }

  run(
    ffmpeg,
    [
      "-y",
      ...inputs,
      "-i",
      audioPath,
      "-filter_complex",
      `${normalized};${transitions.join(";")};[${images.length}:a]adelay=350|350,volume=1.0,apad[audio]`,
      "-map",
      "[video]",
      "-map",
      "[audio]",
      "-c:v",
      "libx264",
      "-preset",
      "veryfast",
      "-crf",
      "24",
      "-pix_fmt",
      "yuv420p",
      "-c:a",
      "aac",
      "-b:a",
      "160k",
      "-shortest",
      "-movflags",
      "+faststart",
      outputPath,
    ],
    `Renderização de ${basename(outputPath)}`,
  );

  run(
    ffmpeg,
    [
      "-y",
      "-i",
      images[video.posterScene ?? 1],
      "-vf",
      "scale=1280:-2",
      "-q:v",
      "3",
      "-frames:v",
      "1",
      posterPath,
    ],
    `Geração do poster de ${video.slug}`,
  );

  return { outputPath, posterPath, duration: audioDuration(outputPath) };
}

if (!existsSync(chrome)) throw new Error(`Chrome não encontrado: ${chrome}`);
if (!existsSync(logoPath)) throw new Error(`Logo não encontrado: ${logoPath}`);

rmSync(workDir, { recursive: true, force: true });
mkdirSync(workDir, { recursive: true });
mkdirSync(publicDir, { recursive: true });

const requestedSlugs = new Set(process.argv.slice(2));
const selectedVideos = requestedSlugs.size
  ? videos.filter((video) => requestedSlugs.has(video.slug))
  : videos;

if (requestedSlugs.size && selectedVideos.length !== requestedSlugs.size) {
  const foundSlugs = new Set(selectedVideos.map((video) => video.slug));
  const missingSlugs = [...requestedSlugs].filter((slug) => !foundSlugs.has(slug));
  throw new Error(`Vídeo(s) não encontrado(s): ${missingSlugs.join(", ")}`);
}

const results = [];
for (const video of selectedVideos) {
  const reuseAudio = process.env.COREPET_REUSE_AUDIO === "1";
  const audioPath = join(
    workDir,
    `${video.slug}-narracao.${reuseAudio ? "m4a" : "mp3"}`,
  );
  if (reuseAudio) {
    const currentVideoPath = join(
      publicDir,
      video.outputName || `corepet-demo-${video.slug}.mp4`,
    );
    if (!existsSync(currentVideoPath)) {
      throw new Error(`Vídeo atual não encontrado para reutilizar áudio: ${currentVideoPath}`);
    }
    run(
      ffmpeg,
      ["-y", "-i", currentVideoPath, "-vn", "-c:a", "copy", audioPath],
      `Extração do áudio atual de ${video.slug}`,
    );
  } else {
    generateVoice(video.voice, audioPath);
  }
  const images = video.scenes.map((scene, index) =>
    captureScene(scene, video.slug, index),
  );
  results.push({
    slug: video.slug,
    ...renderVideo(video, images, audioPath, reuseAudio ? 0 : 1.1),
  });
}

console.log(JSON.stringify({ ok: true, videos: results }, null, 2));
