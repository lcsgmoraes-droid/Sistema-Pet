import { existsSync, mkdirSync, rmSync, writeFileSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import { spawnSync } from "node:child_process";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const output = join(root, "docs", "marketing", "instagram", "growth", "weekly", "2026-32");
const shots = join(root, "frontend", "public", "marketing", "product-shots");
const logo = join(root, "frontend", "public", "brand", "corepet", "corepet-icon-192.png");
const chrome = "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";
const work = join(root, "runtime", "instagram-weekly-2026-32");
const url = (file) => pathToFileURL(file).href;

function run(command, args, label) {
  const result = spawnSync(command, args, { encoding: "utf8" });
  if (result.status !== 0) throw new Error(`${label}: ${result.stderr || result.stdout}`);
}
function esc(value) { return String(value).replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;"); }
function page(content, [width, height], accent) {
  return `<!doctype html><meta charset="utf-8"><style>
*{box-sizing:border-box}html,body{margin:0;width:${width}px;height:${height}px;overflow:hidden;background:#030b1d;color:#fff;font-family:Inter,Segoe UI,Arial,sans-serif}body{position:relative;background:radial-gradient(circle at 87% 10%,${accent}55,transparent 34%),radial-gradient(circle at 6% 90%,#7c3aed44,transparent 42%),linear-gradient(145deg,#020617,#102440)}body:after{content:"";position:absolute;inset:0;background-image:linear-gradient(#fff0 96%,#ffffff08),linear-gradient(90deg,#fff0 96%,#ffffff08);background-size:54px 54px}.brand{position:absolute;z-index:5;top:46px;left:58px;display:flex;align-items:center;gap:12px;font-size:36px;font-weight:950;letter-spacing:-1px}.brand img{width:56px;height:56px;border-radius:15px}.footer{position:absolute;z-index:7;right:43px;bottom:31px;color:#cbd5e1;font-size:18px;font-weight:800}.tag{color:${accent};font-size:21px;font-weight:950;letter-spacing:.14em}.glyph{position:absolute;right:38px;bottom:98px;color:${accent}20;font-size:440px;font-weight:950;line-height:.72}.cta{display:inline-block;margin-top:28px;padding:15px 20px;border-radius:13px;background:${accent};color:#08111f;font-size:18px;font-weight:950;letter-spacing:.05em}.screen{position:absolute;z-index:3;left:60px;right:60px;bottom:76px;height:464px;padding:40px 12px 12px;border:2px solid #334155;border-radius:25px;background:#f8fafc;overflow:hidden;box-shadow:0 30px 90px #000a}.screen:before{content:"";position:absolute;left:18px;top:14px;width:11px;height:11px;border-radius:50%;background:#fb7185;box-shadow:20px 0 #fbbf24,40px 0 #34d399}.screen img{width:100%;height:100%;object-fit:cover;border-radius:11px}.screen-label{position:absolute;z-index:4;right:78px;bottom:554px;color:#334155;font-size:14px;font-weight:950;letter-spacing:.09em}</style><div class="brand"><img src="${url(logo)}">CorePet</div>${content}<div class="footer">@corepet.erp</div>`;
}
function capture(html, file, size) {
  mkdirSync(dirname(file), { recursive: true });
  const source = join(work, `${file.replaceAll(/[\\/:]/g, "-")}.html`);
  writeFileSync(source, html, "utf8");
  run(chrome, ["--headless=new", "--hide-scrollbars", "--disable-gpu", "--allow-file-access-from-files", `--window-size=${size[0]},${size[1]}`, "--force-device-scale-factor=1", `--screenshot=${file}`, url(source)], `Renderização ${file}`);
  if (!existsSync(file)) throw new Error(`Arquivo não criado: ${file}`);
}
function feed({ file, tag, title, body, cta, accent, shot }) {
  const visual = shot ? `<figure class="screen"><img src="${url(join(shots, shot))}"></figure><span class="screen-label">TELA REAL DO COREPET</span>` : `<div class="glyph">✦</div><div style="position:absolute;z-index:3;left:60px;right:60px;bottom:115px;padding:28px;border:1px solid #ffffff20;border-radius:22px;background:#ffffff0b;color:#dbeafe;font-size:28px;line-height:1.36">Demonstração guiada para entender a rotina da sua operação.</div>`;
  capture(page(`<main style="position:absolute;z-index:4;left:60px;right:60px;top:178px"><div class="tag">${tag}</div><h1 style="margin:17px 0 0;font-size:72px;line-height:.98;letter-spacing:-3.4px;white-space:pre-line">${esc(title)}</h1><p style="margin:25px 0 0;max-width:890px;color:#dbeafe;font-size:28px;line-height:1.35;font-weight:650">${esc(body)}</p><span class="cta">${cta}</span></main>${visual}`, [1080, 1350], accent), join(output, file), [1080, 1350]);
}
function carousel(slug, accent, slides) {
  slides.forEach(([tag, title, body], index) => {
    const progress = slides.map((_, i) => `<i style="height:6px;flex:1;border-radius:6px;background:${i === index ? accent : "#ffffff25"}"></i>`).join("");
    capture(page(`<main style="position:absolute;z-index:4;left:62px;right:62px;top:190px"><div class="tag">${tag}</div><h1 style="margin:24px 0 0;font-size:${title.length > 45 ? 61 : 75}px;line-height:.99;letter-spacing:-3.3px;white-space:pre-line">${esc(title)}</h1><p style="margin:29px 0 0;max-width:875px;color:#dbeafe;font-size:30px;line-height:1.37;font-weight:650">${esc(body)}</p></main><div class="glyph" style="font-size:390px">${index + 1}</div><div style="position:absolute;z-index:5;left:62px;right:62px;bottom:55px;display:flex;gap:8px">${progress}</div>`, [1080, 1350], accent), join(output, slug, `${String(index + 1).padStart(2, "0")}.png`), [1080, 1350]);
  });
}
function reelFrame(tag, title, body, accent) {
  return page(`<main style="position:absolute;z-index:4;left:68px;right:68px;top:430px"><div class="tag">${tag}</div><h1 style="margin:22px 0 0;font-size:88px;line-height:.96;letter-spacing:-4px">${esc(title)}</h1><p style="margin:30px 0 0;color:#dbeafe;font-size:37px;line-height:1.35;font-weight:650">${esc(body)}</p><span class="cta" style="font-size:21px">DEMO PELO LINK DO PERFIL</span></main><div class="glyph" style="font-size:520px;bottom:270px">✦</div>`, [1080, 1920], accent);
}

rmSync(work, { recursive: true, force: true });
mkdirSync(work, { recursive: true });
feed({ file: "08-petshop-uma-operacao-tres-canais.png", tag: "PET SHOP", title: "Três canais.\nUma operação.", body: "ERP, app e e-commerce compartilham produtos, pedidos e estoque.", cta: "VEJA EM UMA DEMO", accent: "#38bdf8", shot: "ecommerce-catalogo.png" });
feed({ file: "10-banho-tosa-agenda-operacional.png", tag: "BANHO & TOSA", title: "Agenda que respeita\na operação.", body: "Pet, profissional e recurso entram no mesmo agendamento para evitar conflitos.", cta: "CONHEÇA O MÓDULO", accent: "#f472b6" });
carousel("09-carrossel-recompra-inteligente", "#34d399", [
  ["RECOMPRA INTELIGENTE", "A próxima compra\nnão precisa ser chute.", "Arraste para ver quando o histórico pode virar uma oportunidade."],
  ["01", "O histórico precisa ser consistente.", "Produtos de reposição usam o comportamento real quando há compras em intervalos consistentes."],
  ["02", "Há uma regra para aprender.", "Sem configuração manual, a recorrência pode ser descoberta após pelo menos três compras consistentes."],
  ["03", "O aviso chega pelo app.", "Ao tocar na notificação, o cliente abre diretamente o produto."],
  ["COREPET", "Venda ativa com contexto.", "Peça uma demonstração pelo link do perfil."]
]);
carousel("11-carrossel-clinica-piloto", "#60a5fa", [
  ["CLÍNICA VETERINÁRIA", "Uma vertical para\ndemonstrar com clareza.", "O módulo Veterinário CorePet está em beta/piloto acompanhado."],
  ["01", "Comece pela agenda.", "Mostre o fluxo de atendimento e avance para consultas."],
  ["02", "Navegue pelo prontuário.", "Sinais vitais, anamnese, exame físico, diagnóstico e conduta fazem parte da demonstração."],
  ["03", "Apresente os controles clínicos.", "Vacinas, exames, internação, catálogo e repasse podem ser mostrados em uma demo guiada."],
  ["COREPET", "Piloto acompanhado.", "Agende uma conversa para avaliar o cenário da sua clínica."]
]);
const frames = [
  ["LISTA DE ESPERA", "Produto em falta?\nA conversa continua.", "O interesse do cliente pode entrar na lista de espera.", "#f59e0b"],
  ["QUANDO HÁ REPOSIÇÃO", "O sistema reconhece\no produto disponível.", "A rotina confere a volta do item ao estoque.", "#38bdf8"],
  ["NO APP", "O cliente pode\nser avisado.", "Conheça a lista de espera CorePet em uma demonstração.", "#34d399"]
];
const reel = join(work, "reel"); mkdirSync(reel, { recursive: true }); const segments = [];
frames.forEach((frame, index) => { const image = join(reel, `frame-${index}.png`); const segment = join(reel, `segment-${index}.mp4`); capture(reelFrame(...frame), image, [1080, 1920]); run("ffmpeg", ["-y", "-loop", "1", "-i", image, "-t", "4.5", "-vf", "scale=1080:1920,format=yuv420p", "-r", "30", "-an", "-c:v", "libx264", "-crf", "19", segment], `Cena ${index + 1}`); segments.push(segment); });
const concat = join(reel, "concat.txt"); writeFileSync(concat, segments.map((item) => `file '${item.replaceAll("'", "'\\''")}'`).join("\n"));
const audio = join(reel, "audio.mp3"); run("edge-tts", ["--voice", "pt-BR-AntonioNeural", "--rate=+2%", "--text", "Produto em falta não precisa encerrar a conversa. A lista de espera registra o interesse. Quando o item volta ao estoque, o cliente pode receber um aviso pelo app. Conheça o CorePet em uma demonstração.", "--write-media", audio], "Narração");
run("ffmpeg", ["-y", "-f", "concat", "-safe", "0", "-i", concat, "-i", audio, "-c:v", "copy", "-c:a", "aac", "-b:a", "160k", "-shortest", "-movflags", "+faststart", join(output, "12-reel-lista-espera-app.mp4")], "Reel");
console.log(`Lote criado em ${output}`);
