import { spawnSync } from "node:child_process";
import {
  copyFileSync,
  existsSync,
  mkdirSync,
  rmSync,
  writeFileSync,
} from "node:fs";
import { basename, join, resolve } from "node:path";
import { pathToFileURL } from "node:url";

const root = resolve(import.meta.dirname, "..");
const chrome =
  process.env.CHROME_PATH ||
  "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";
const ffmpeg = process.env.FFMPEG_PATH || "ffmpeg";
const outputDir = resolve(
  process.env.COREPET_VIDEO_OUTPUT_DIR ||
    join(root, "frontend", "public", "marketing"),
);
const workDir = join(root, "runtime", "marketing-video-venda-ativa");
const logoPath = join(
  root,
  "frontend",
  "public",
  "brand",
  "corepet",
  "corepet-icon-192.png",
);
const verticalOutput = join(outputDir, "corepet-vende-de-novo-vertical.mp4");
const horizontalOutput = join(
  outputDir,
  "corepet-vende-de-novo-horizontal.mp4",
);
const posterOutput = join(outputDir, "corepet-vende-de-novo-poster.jpg");
const voiceoverPath = join(outputDir, "corepet-vende-de-novo-narracao.mp3");
const demoCaptureDir = join(root, "runtime", "marketing-captures");

const scenes = [
  {
    eyebrow: "O varejo pet mudou",
    title: "Sua loja ainda espera o cliente voltar?",
    text: "Enquanto você espera, a próxima compra pode estar indo para outro lugar.",
    accent: "#a78bfa",
  },
  {
    eyebrow: "Venda ativa",
    title: "A ração está acabando.",
    text: "O CorePet aprende o comportamento de consumo e identifica a hora da recompra.",
    accent: "#34d399",
    notification:
      "Ei, a ração do seu pet não está acabando? Peça agora no app.",
  },
  {
    eyebrow: "Recorrência inteligente",
    title: "O produto certo. No momento certo.",
    text: "Rações, antipulgas e protocolos configurados viram oportunidades de nova venda.",
    accent: "#2dd4bf",
    demoCapture: join(demoCaptureDir, "03-recorrencia-criada.png"),
    demoObjectPosition: "left top",
  },
  {
    eyebrow: "Um único ecossistema",
    title: "ERP + App + E‑commerce",
    text: "Três canais. Uma única operação.",
    accent: "#60a5fa",
    channelShowcase: true,
    erpCapture: join(demoCaptureDir, "02-produtos-canais-estoque.png"),
    appCapture: join(demoCaptureDir, "04-ecommerce-real.jpg"),
    ecommerceCapture: join(demoCaptureDir, "04-ecommerce-real.jpg"),
  },
  {
    eyebrow: "Gestão em tempo real",
    title: "Venda não é faturamento. É resultado.",
    text: "Taxas, impostos, custos, comissão, margem e lucro visíveis para decidir melhor.",
    accent: "#fbbf24",
    metrics: ["TAXAS", "IMPOSTOS", "MARGEM", "LUCRO"],
    demoCapture: join(demoCaptureDir, "01-vendas-rentabilidade.png"),
  },
  {
    eyebrow: "CorePet",
    title: "Seu ERP registra o que você vendeu.",
    text: "O CorePet trabalha para vender de novo.",
    accent: "#34d399",
    cta: "SOLICITE UMA DEMONSTRAÇÃO",
  },
];

const durations = [3.4, 4.2, 3.8, 4.1, 4.2, 5.1];
const transitionDuration = 0.45;

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function sceneHtml(scene, width, height) {
  const vertical = height > width;
  const titleSize = vertical ? 90 : 86;
  const textSize = vertical ? 39 : 34;
  const maxWidth = vertical ? 900 : 1350;
  const logoUrl = pathToFileURL(logoPath).href;
  const chips = scene.chips
    ? `<div class="chips">${scene.chips.map((item) => `<span>${item}</span>`).join("")}</div>`
    : "";
  const metrics = scene.metrics
    ? `<div class="metrics">${scene.metrics.map((item) => `<span>${item}</span>`).join("")}</div>`
    : "";
  const notification = scene.notification
    ? `<div class="notification"><div class="app-icon">C</div><div><b>CorePet</b><p>${escapeHtml(scene.notification)}</p></div></div>`
    : "";
  const cta = scene.cta
    ? `<div class="cta">${escapeHtml(scene.cta)}</div>`
    : "";
  const demoCapture =
    scene.demoCapture && existsSync(scene.demoCapture)
      ? `<figure class="demo"><img src="${pathToFileURL(scene.demoCapture).href}" alt="Tela real do CorePet"><figcaption>TELA REAL DO SISTEMA</figcaption></figure>`
      : "";
  const channelShowcase =
    scene.channelShowcase &&
    existsSync(scene.erpCapture) &&
    existsSync(scene.appCapture) &&
    existsSync(scene.ecommerceCapture)
      ? `<div class="channels-showcase">
          <figure class="channel-window channel-erp">
            <figcaption><span></span>ERP</figcaption>
            <img src="${pathToFileURL(scene.erpCapture).href}" alt="Tela real do ERP CorePet">
          </figure>
          <figure class="channel-window channel-ecommerce">
            <figcaption><span></span>E-COMMERCE</figcaption>
            <img src="${pathToFileURL(scene.ecommerceCapture).href}" alt="Tela real do e-commerce CorePet">
          </figure>
          <figure class="channel-phone">
            <figcaption>APP</figcaption>
            <div class="phone-speaker"></div>
            <img src="${pathToFileURL(scene.appCapture).href}" alt="Catálogo do app CorePet">
            <div class="phone-proof">
              <b>CorePet</b>
              <span>Sua ração está acabando?</span>
              <small>Peça novamente pelo app.</small>
              <button>PEDIR AGORA</button>
            </div>
            <div class="phone-home"></div>
          </figure>
        </div>`
      : "";
  const hasDemo = Boolean(demoCapture || channelShowcase);

  return `<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<style>
  * { box-sizing: border-box; }
  html, body { width: 100%; height: 100%; margin: 0; overflow: hidden; }
  body {
    font-family: Inter, "Segoe UI", Arial, sans-serif;
    color: #fff;
    background:
      radial-gradient(circle at 84% 18%, ${scene.accent}44 0, transparent 32%),
      radial-gradient(circle at 16% 82%, #7c3aed33 0, transparent 35%),
      linear-gradient(145deg, #020617 0%, #0f172a 58%, #111827 100%);
  }
  body::before {
    content: "";
    position: absolute;
    inset: 0;
    opacity: .2;
    background-image: linear-gradient(#ffffff0b 1px, transparent 1px), linear-gradient(90deg, #ffffff0b 1px, transparent 1px);
    background-size: 72px 72px;
    mask-image: linear-gradient(to bottom, black, transparent 90%);
  }
  .frame { position: relative; width: 100%; height: 100%; padding: ${vertical ? "58px 54px 190px" : "48px 70px 100px"}; display: flex; flex-direction: column; }
  .brand { display: flex; align-items: center; gap: 18px; width: fit-content; color: #fff; font-size: ${vertical ? 38 : 34}px; font-weight: 950; letter-spacing: -.03em; }
  .brand img { width: ${vertical ? 66 : 58}px; height: ${vertical ? 66 : 58}px; border-radius: 16px; box-shadow: 0 16px 46px #0007; }
  .content { margin: auto 0; max-width: ${hasDemo && !vertical ? "1740" : maxWidth}px; }
  .content.has-demo { display: grid; grid-template-columns: ${vertical ? "1fr" : "minmax(0, .72fr) minmax(820px, 1.28fr)"}; gap: ${vertical ? "28px" : "48px"}; align-items: center; }
  .copy { min-width: 0; }
  .content.has-demo h1 { font-size: ${vertical ? "58px" : "56px"}; line-height: 1; }
  .content.has-demo .lead { margin-top: ${vertical ? "16px" : "20px"}; font-size: ${vertical ? "25px" : "26px"}; }
  .content.has-demo .line { margin-top: ${vertical ? "23px" : "25px"}; }
  .content.has-demo .chips, .content.has-demo .metrics { margin-top: ${vertical ? "25px" : "30px"}; gap: 12px; }
  .content.has-demo .chips span, .content.has-demo .metrics span { padding: ${vertical ? "14px 12px" : "17px 14px"}; font-size: ${vertical ? "18px" : "18px"}; }
  .eyebrow { color: ${scene.accent}; font-size: ${vertical ? 28 : 25}px; font-weight: 900; letter-spacing: .18em; text-transform: uppercase; margin-bottom: 28px; }
  h1 { margin: 0; max-width: ${maxWidth}px; font-size: ${titleSize}px; line-height: .98; letter-spacing: -.045em; font-weight: 950; }
  .lead { margin: 34px 0 0; max-width: ${vertical ? 860 : 1150}px; color: #cbd5e1; font-size: ${textSize}px; line-height: 1.28; font-weight: 600; }
  .line { width: 116px; height: 8px; margin-top: 38px; border-radius: 99px; background: ${scene.accent}; box-shadow: 0 0 40px ${scene.accent}88; }
  .notification { margin-top: 56px; display: flex; gap: 22px; align-items: flex-start; max-width: ${vertical ? 900 : 1050}px; padding: 28px; border: 1px solid #ffffff25; border-radius: 28px; background: #ffffff12; box-shadow: 0 26px 80px #0008; backdrop-filter: blur(22px); }
  .notification .app-icon { flex: none; display: grid; place-items: center; width: 76px; height: 76px; border-radius: 20px; color: #052e2b; background: ${scene.accent}; font-size: 36px; font-weight: 950; }
  .notification b { font-size: ${vertical ? 31 : 27}px; }
  .notification p { margin: 8px 0 0; color: #e2e8f0; font-size: ${vertical ? 29 : 25}px; line-height: 1.35; }
  .chips, .metrics { display: grid; grid-template-columns: repeat(${vertical ? 1 : 3}, minmax(0, 1fr)); gap: 18px; margin-top: 54px; max-width: ${vertical ? 760 : 1220}px; }
  .metrics { grid-template-columns: repeat(${vertical ? 2 : 4}, minmax(0, 1fr)); }
  .chips span, .metrics span { padding: 22px 25px; border: 1px solid #ffffff22; border-radius: 18px; background: #ffffff0d; color: #f8fafc; text-align: center; font-size: ${vertical ? 27 : 24}px; font-weight: 900; letter-spacing: .06em; }
  .demo { position: relative; margin: 0; padding: ${vertical ? "13px" : "16px"}; border: 1px solid #ffffff2b; border-radius: ${vertical ? "24px" : "28px"}; background: #020617cc; box-shadow: 0 34px 100px #000b, 0 0 60px ${scene.accent}22; transform: rotate(${vertical ? "0" : "-1.2deg"}); overflow: hidden; }
  .demo img { display: block; width: 100%; height: ${vertical ? "720px" : "650px"}; object-fit: cover; object-position: ${scene.demoObjectPosition || "top center"}; border-radius: ${vertical ? "15px" : "18px"}; }
  .demo figcaption { position: absolute; right: 28px; bottom: 25px; padding: 10px 15px; border-radius: 999px; color: #020617; background: ${scene.accent}; font-size: ${vertical ? 17 : 16}px; font-weight: 950; letter-spacing: .08em; box-shadow: 0 10px 30px #0008; }
  .cta { display: inline-flex; align-items: center; justify-content: center; margin-top: 52px; width: fit-content; padding: 24px 34px; border-radius: 18px; background: ${scene.accent}; color: #052e2b; font-size: ${vertical ? 26 : 24}px; font-weight: 950; letter-spacing: .08em; box-shadow: 0 20px 60px ${scene.accent}33; }
  .channels-showcase { position: relative; width: 100%; height: ${vertical ? "910px" : "720px"}; }
  .channel-window, .channel-phone { margin: 0; overflow: hidden; border: 1px solid #ffffff30; background: #020617; box-shadow: 0 28px 90px #000c; }
  .channel-window { position: absolute; width: ${vertical ? "82%" : "82%"}; height: ${vertical ? "390px" : "330px"}; border-radius: 25px; }
  .channel-window figcaption { display: flex; align-items: center; gap: 10px; height: 46px; padding: 0 18px; color: #e2e8f0; background: #0f172a; font-size: 18px; font-weight: 950; letter-spacing: .08em; }
  .channel-window figcaption span { width: 11px; height: 11px; border-radius: 50%; background: ${scene.accent}; box-shadow: 18px 0 #34d399, 36px 0 #fbbf24; margin-right: 38px; }
  .channel-window img { width: 100%; height: calc(100% - 46px); object-fit: cover; object-position: top center; }
  .channel-erp { left: 0; top: 0; transform: rotate(-1.2deg); }
  .channel-ecommerce { right: 0; bottom: 0; transform: rotate(1.2deg); }
  .channel-ecommerce img { object-position: center bottom; }
  .channel-phone { position: absolute; z-index: 3; left: ${vertical ? "55%" : "53%"}; top: ${vertical ? "210px" : "145px"}; width: ${vertical ? "310px" : "270px"}; height: ${vertical ? "610px" : "540px"}; border: 12px solid #020617; border-radius: 48px; background: #f8fafc; transform: translateX(-50%) rotate(2deg); }
  .channel-phone figcaption { position: absolute; z-index: 3; left: 50%; top: 24px; transform: translateX(-50%); padding: 9px 18px; border-radius: 999px; color: #020617; background: ${scene.accent}; font-size: 18px; font-weight: 950; letter-spacing: .1em; }
  .channel-phone img { position: absolute; width: ${vertical ? "900px" : "820px"}; height: auto; left: ${vertical ? "-100px" : "-105px"}; top: ${vertical ? "-230px" : "-210px"}; }
  .phone-proof { position: absolute; z-index: 3; left: 15px; right: 15px; top: ${vertical ? "270px" : "235px"}; padding: ${vertical ? "23px 19px" : "19px 16px"}; border-radius: 23px; color: #e2e8f0; background: linear-gradient(145deg, #0f172a, #172554); box-shadow: 0 20px 45px #02061755; }
  .phone-proof b { display: block; color: ${scene.accent}; font-size: ${vertical ? "20px" : "18px"}; }
  .phone-proof span { display: block; margin-top: 13px; color: #fff; font-size: ${vertical ? "23px" : "20px"}; font-weight: 900; line-height: 1.08; }
  .phone-proof small { display: block; margin-top: 9px; color: #cbd5e1; font-size: ${vertical ? "16px" : "14px"}; line-height: 1.25; }
  .phone-proof button { width: 100%; margin-top: 17px; padding: 13px 8px; border: 0; border-radius: 13px; color: #020617; background: ${scene.accent}; font-size: 14px; font-weight: 950; letter-spacing: .08em; }
  .phone-speaker { position: absolute; z-index: 4; left: 50%; top: 7px; width: 82px; height: 7px; transform: translateX(-50%); border-radius: 99px; background: #334155; }
  .phone-home { position: absolute; z-index: 4; left: 50%; bottom: 8px; width: 82px; height: 6px; transform: translateX(-50%); border-radius: 99px; background: #64748b; }
  .footer { position: absolute; z-index: 10; left: ${vertical ? "54px" : "70px"}; right: ${vertical ? "54px" : "70px"}; bottom: ${vertical ? "122px" : "48px"}; display: flex; align-items: center; justify-content: space-between; color: #94a3b8; font-size: ${vertical ? 23 : 20}px; font-weight: 700; }
  .dot { display: inline-block; width: 11px; height: 11px; margin-right: 10px; border-radius: 50%; background: ${scene.accent}; box-shadow: 0 0 22px ${scene.accent}; }
</style>
</head>
<body>
  <main class="frame">
    <div class="brand"><img src="${logoUrl}" alt=""><span>CorePet</span></div>
    <section class="content${hasDemo ? " has-demo" : ""}">
      <div class="copy">
        <div class="eyebrow">${escapeHtml(scene.eyebrow)}</div>
        <h1>${escapeHtml(scene.title)}</h1>
        <p class="lead">${escapeHtml(scene.text)}</p>
        <div class="line"></div>
        ${notification}${chips}${metrics}${cta}
      </div>
      ${channelShowcase || demoCapture}
    </section>
    <footer class="footer"><span><i class="dot"></i>ERP • APP • E-COMMERCE</span><span>corepet.com.br</span></footer>
  </main>
</body>
</html>`;
}

function run(command, args, label) {
  const result = spawnSync(command, args, { encoding: "utf8", stdio: "pipe" });
  if (result.status !== 0) {
    throw new Error(`${label} falhou:\n${result.stderr || result.stdout}`);
  }
}

function captureScene(scene, index, width, height, suffix) {
  const htmlPath = join(workDir, `scene-${index}-${suffix}.html`);
  const pngPath = join(workDir, `scene-${index}-${suffix}.png`);
  writeFileSync(htmlPath, sceneHtml(scene, width, height), "utf8");
  run(
    chrome,
    [
      "--headless=new",
      "--hide-scrollbars",
      "--disable-gpu",
      "--allow-file-access-from-files",
      `--window-size=${width},${height}`,
      `--screenshot=${pngPath}`,
      pathToFileURL(htmlPath).href,
    ],
    `Captura da cena ${index + 1}`,
  );
  return pngPath;
}

function renderVideo(images, outputPath, width, height) {
  const visualOutput = existsSync(voiceoverPath)
    ? join(workDir, `sem-audio-${basename(outputPath)}`)
    : outputPath;
  const inputs = images.flatMap((image, index) => [
    "-loop",
    "1",
    "-t",
    String(durations[index]),
    "-i",
    image,
  ]);
  const normalized = images
    .map(
      (_, index) =>
        `[${index}:v]scale=${width}:${height}:force_original_aspect_ratio=increase,crop=${width}:${height},fps=30,format=yuv420p[v${index}]`,
    )
    .join(";");

  let previous = "v0";
  let elapsed = durations[0];
  const transitions = [];
  for (let index = 1; index < images.length; index += 1) {
    const output = index === images.length - 1 ? "video" : `x${index}`;
    const offset = elapsed - transitionDuration;
    transitions.push(
      `[${previous}][v${index}]xfade=transition=fade:duration=${transitionDuration}:offset=${offset.toFixed(2)}[${output}]`,
    );
    previous = output;
    elapsed += durations[index] - transitionDuration;
  }

  run(
    ffmpeg,
    [
      "-y",
      ...inputs,
      "-filter_complex",
      `${normalized};${transitions.join(";")}`,
      "-map",
      "[video]",
      "-an",
      "-c:v",
      "libx264",
      "-preset",
      "medium",
      "-crf",
      "20",
      "-movflags",
      "+faststart",
      "-pix_fmt",
      "yuv420p",
      visualOutput,
    ],
    `Renderização de ${visualOutput}`,
  );

  if (existsSync(voiceoverPath)) {
    run(
      ffmpeg,
      [
        "-y",
        "-i",
        visualOutput,
        "-i",
        voiceoverPath,
        "-filter_complex",
        "[1:a]adelay=450|450,volume=1.0,apad[audio]",
        "-map",
        "0:v:0",
        "-map",
        "[audio]",
        "-c:v",
        "copy",
        "-c:a",
        "aac",
        "-b:a",
        "160k",
        "-shortest",
        "-movflags",
        "+faststart",
        outputPath,
      ],
      `Inclusão da narração em ${outputPath}`,
    );
  }
}

if (!existsSync(chrome)) throw new Error(`Chrome não encontrado: ${chrome}`);
if (!existsSync(logoPath)) throw new Error(`Logo não encontrado: ${logoPath}`);

rmSync(workDir, { recursive: true, force: true });
mkdirSync(workDir, { recursive: true });
mkdirSync(outputDir, { recursive: true });

const verticalScenes = scenes.map((scene, index) =>
  captureScene(scene, index, 1080, 1920, "vertical"),
);
const horizontalScenes = scenes.map((scene, index) =>
  captureScene(scene, index, 1920, 1080, "horizontal"),
);

renderVideo(verticalScenes, verticalOutput, 1080, 1920);
renderVideo(horizontalScenes, horizontalOutput, 1920, 1080);

run(
  ffmpeg,
  ["-y", "-i", verticalScenes[1], "-q:v", "2", posterOutput],
  "Geração do poster",
);

copyFileSync(verticalScenes[0], join(workDir, "preview-first-frame.png"));

console.log(
  JSON.stringify(
    {
      ok: true,
      vertical: verticalOutput,
      horizontal: horizontalOutput,
      poster: posterOutput,
      durationSeconds:
        durations.reduce((sum, value) => sum + value, 0) -
        transitionDuration * (durations.length - 1),
    },
    null,
    2,
  ),
);
