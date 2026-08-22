import { existsSync, mkdirSync, rmSync, writeFileSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import { spawnSync } from "node:child_process";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const output = join(root, "docs", "marketing", "instagram", "growth", "weekly", "2026-34");
const shots = join(root, "frontend", "public", "marketing", "product-shots");
const logo = join(root, "frontend", "public", "brand", "corepet", "corepet-icon-192.png");
const chrome = "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";
const work = join(root, "runtime", "instagram-weekly-2026-34");
const url = (file) => pathToFileURL(file).href;

function run(command, args, label) { const result = spawnSync(command, args, { encoding: "utf8" }); if (result.status !== 0) throw new Error(`${label}: ${result.stderr || result.stdout}`); }
function esc(value) { return String(value).replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;"); }
function page(content, [width, height], accent) { return `<!doctype html><meta charset="utf-8"><style>
*{box-sizing:border-box}html,body{margin:0;width:${width}px;height:${height}px;overflow:hidden;background:#030b1d;color:#fff;font-family:Inter,Segoe UI,Arial,sans-serif}body{position:relative;background:radial-gradient(circle at 87% 10%,${accent}55,transparent 34%),radial-gradient(circle at 6% 90%,#7c3aed44,transparent 42%),linear-gradient(145deg,#020617,#102440)}body:after{content:"";position:absolute;inset:0;background-image:linear-gradient(#fff0 96%,#ffffff08),linear-gradient(90deg,#fff0 96%,#ffffff08);background-size:54px 54px}.brand{position:absolute;z-index:5;top:46px;left:58px;display:flex;align-items:center;gap:12px;font-size:36px;font-weight:950;letter-spacing:-1px}.brand img{width:56px;height:56px;border-radius:15px}.footer{position:absolute;z-index:7;right:43px;bottom:31px;color:#cbd5e1;font-size:18px;font-weight:800}.tag{color:${accent};font-size:21px;font-weight:950;letter-spacing:.14em}.glyph{position:absolute;right:38px;bottom:98px;color:${accent}20;font-size:440px;font-weight:950;line-height:.72}.cta{display:inline-block;margin-top:28px;padding:15px 20px;border-radius:13px;background:${accent};color:#08111f;font-size:18px;font-weight:950;letter-spacing:.05em}.screen{position:absolute;z-index:3;left:60px;right:60px;bottom:76px;height:464px;padding:40px 12px 12px;border:2px solid #334155;border-radius:25px;background:#f8fafc;overflow:hidden;box-shadow:0 30px 90px #000a}.screen:before{content:"";position:absolute;left:18px;top:14px;width:11px;height:11px;border-radius:50%;background:#fb7185;box-shadow:20px 0 #fbbf24,40px 0 #34d399}.screen img{width:100%;height:100%;object-fit:cover;border-radius:11px}.screen-label{position:absolute;z-index:4;right:78px;bottom:554px;color:#334155;font-size:14px;font-weight:950;letter-spacing:.09em}</style><div class="brand"><img src="${url(logo)}">CorePet</div>${content}<div class="footer">@corepet.erp</div>`; }
function capture(html, file, size) { mkdirSync(dirname(file), { recursive: true }); const source = join(work, `${file.replaceAll(/[\\/:]/g, "-")}.html`); writeFileSync(source, html, "utf8"); run(chrome, ["--headless=new", "--hide-scrollbars", "--disable-gpu", "--allow-file-access-from-files", `--window-size=${size[0]},${size[1]}`, "--force-device-scale-factor=1", `--screenshot=${file}`, url(source)], `Renderização ${file}`); if (!existsSync(file)) throw new Error(`Arquivo não criado: ${file}`); }
function feed({ file, tag, title, body, cta, accent, shot }) { const visual = `<figure class="screen"><img src="${url(join(shots, shot))}"></figure><span class="screen-label">TELA REAL DO COREPET</span>`; capture(page(`<main style="position:absolute;z-index:4;left:60px;right:60px;top:178px"><div class="tag">${tag}</div><h1 style="margin:17px 0 0;font-size:72px;line-height:.98;letter-spacing:-3.4px;white-space:pre-line">${esc(title)}</h1><p style="margin:25px 0 0;max-width:890px;color:#dbeafe;font-size:28px;line-height:1.35;font-weight:650">${esc(body)}</p><span class="cta">${cta}</span></main>${visual}`, [1080, 1350], accent), join(output, file), [1080, 1350]); }
function carousel(slug, accent, slides) { slides.forEach(([tag, title, body], index) => { const progress = slides.map((_, i) => `<i style="height:6px;flex:1;border-radius:6px;background:${i === index ? accent : "#ffffff25"}"></i>`).join(""); capture(page(`<main style="position:absolute;z-index:4;left:62px;right:62px;top:190px"><div class="tag">${tag}</div><h1 style="margin:24px 0 0;font-size:${title.length > 45 ? 61 : 75}px;line-height:.99;letter-spacing:-3.3px;white-space:pre-line">${esc(title)}</h1><p style="margin:29px 0 0;max-width:875px;color:#dbeafe;font-size:30px;line-height:1.37;font-weight:650">${esc(body)}</p></main><div class="glyph" style="font-size:390px">${index + 1}</div><div style="position:absolute;z-index:5;left:62px;right:62px;bottom:55px;display:flex;gap:8px">${progress}</div>`, [1080, 1350], accent), join(output, slug, `${String(index + 1).padStart(2, "0")}.png`), [1080, 1350]); }); }
function reelFrame(tag, title, body, accent) { return page(`<main style="position:absolute;z-index:4;left:68px;right:68px;top:430px"><div class="tag">${tag}</div><h1 style="margin:22px 0 0;font-size:88px;line-height:.96;letter-spacing:-4px;white-space:pre-line">${esc(title)}</h1><p style="margin:30px 0 0;color:#dbeafe;font-size:37px;line-height:1.35;font-weight:650">${esc(body)}</p><span class="cta" style="font-size:21px">DEMO PELO LINK DO PERFIL</span></main><div class="glyph" style="font-size:520px;bottom:270px">✦</div>`, [1080, 1920], accent); }

rmSync(work, { recursive: true, force: true }); mkdirSync(work, { recursive: true }); mkdirSync(output, { recursive: true });
feed({ file: "19-lista-espera-estoque.png", tag: "ESTOQUE", title: "Sem produto não precisa\nser fim da conversa.", body: "Registre o interesse na lista de espera e deixe o app avisar quando o item voltar ao estoque.", cta: "VEJA EM UMA DEMO", accent: "#f59e0b", shot: "pdv-lista-espera.png" });
feed({ file: "22-venda-com-contexto.png", tag: "DEMONSTRAÇÃO", title: "Uma venda pede\nmais que um total.", body: "Custos, taxas, impostos, comissão, margem e lucro ajudam a ler cada venda por inteiro.", cta: "VEJA A TELA REAL", accent: "#34d399", shot: "erp-venda-expandida.png" });
feed({ file: "24-catalogo-aberto.png", tag: "VENDA 24 HORAS", title: "O cliente escolhe\nquando comprar.", body: "App e e-commerce deixam o catálogo disponível além do horário da loja física.", cta: "CONHEÇA O COREPET", accent: "#38bdf8", shot: "app-produtos.png" });
carousel("20-carrossel-recompra-com-contexto", "#a78bfa", [
  ["RECOMPRA", "A venda terminou.\nA conversa não.", "Arraste para entender como o histórico ajuda a enxergar o próximo passo."],
  ["01", "Produtos recorrentes deixam sinais.", "A data provável de recompra ajuda a identificar uma oportunidade no momento certo."],
  ["02", "Contexto evita contato genérico.", "Use o histórico para a equipe saber com quem vale conversar e por quê."],
  ["03", "O próximo passo pode ser organizado.", "Recompra e retenção ajudam a transformar sinais em rotina comercial."],
  ["COREPET", "Venda ativa é\nter contexto.", "Peça uma demonstração pelo link do perfil."]
]);
carousel("23-carrossel-escolher-sistema-pet", "#f472b6", [
  ["GUIA PARA PET SHOP", "Antes de escolher\num sistema, pergunte:", "Cinco perguntas para olhar além do cadastro e do caixa."],
  ["01", "O catálogo atende\nos seus canais?", "Confira como produtos, pedidos e estoque acompanham app e e-commerce."],
  ["02", "O estoque ajuda\na recuperar interesse?", "Uma lista de espera torna visível quem quer ser avisado quando o produto voltar."],
  ["03", "A venda mostra o\nresultado completo?", "Olhe para custos, taxas, impostos, comissão, margem e lucro."],
  ["COREPET", "Veja as respostas\nna prática.", "Solicite uma demonstração guiada pelo link do perfil."]
]);
const frames = [
  ["ECOSSISTEMA COREPET", "O pedido chega\npelo canal do cliente.", "A operação não precisa perder o contexto.", "#38bdf8"],
  ["CATÁLOGO CENTRALIZADO", "Produto, pedido\ne estoque juntos.", "App e e-commerce fazem parte da mesma operação.", "#34d399"],
  ["COREPET", "Menos troca\nde tela.", "Conheça em uma demonstração guiada.", "#f59e0b"]
];
const reel = join(work, "reel"); mkdirSync(reel, { recursive: true }); const segments = [];
frames.forEach((frame, index) => { const image = join(reel, `frame-${index}.png`); const segment = join(reel, `segment-${index}.mp4`); capture(reelFrame(...frame), image, [1080, 1920]); run("ffmpeg", ["-y", "-loop", "1", "-i", image, "-t", "4.5", "-vf", "scale=1080:1920,format=yuv420p", "-r", "30", "-an", "-c:v", "libx264", "-crf", "19", segment], `Cena ${index + 1}`); segments.push(segment); });
const concat = join(reel, "concat.txt"); writeFileSync(concat, segments.map((item) => `file '${item.replaceAll("'", "'\\''")}'`).join("\n")); const audio = join(reel, "audio.mp3");
run("edge-tts", ["--voice", "pt-BR-AntonioNeural", "--rate=+2%", "--text", "O pedido chega pelo canal que o cliente escolheu. Produto, pedido e estoque seguem na mesma operação. Menos troca de tela. Conheça o CorePet em uma demonstração guiada.", "--write-media", audio], "Narração");
run("ffmpeg", ["-y", "-f", "concat", "-safe", "0", "-i", concat, "-i", audio, "-c:v", "copy", "-c:a", "aac", "-b:a", "160k", "-shortest", "-movflags", "+faststart", join(output, "21-reel-canais-mesma-operacao.mp4")], "Reel");
console.log(`Lote criado em ${output}`);
