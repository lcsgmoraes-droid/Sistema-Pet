import { existsSync, mkdirSync, rmSync, writeFileSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import { spawnSync } from "node:child_process";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const instagram = join(root, "docs", "marketing", "instagram");
const output = join(instagram, "growth", "weekly", "2026-31");
const shots = join(root, "frontend", "public", "marketing", "product-shots");
const logo = join(root, "frontend", "public", "brand", "corepet", "corepet-icon-192.png");
const chrome = "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";
const ffmpeg = "ffmpeg";
const edgeTts = "edge-tts";
const work = join(root, "runtime", "instagram-weekly-2026-31");
const url = (p) => pathToFileURL(p).href;

const pieces = [
  { file: "01-petshop-estoque-que-vende.png", tag: "PET SHOP", title: "Estoque parado custa.\nEstoque visível vende.", body: "Lista de espera transforma interesse em próxima oportunidade.", cta: "VEJA EM UMA DEMO", accent: "#f59e0b", image: "pdv-lista-espera.png", label: "TELA REAL DO COREPET" },
  { file: "02-petshop-recompra-com-contexto.png", tag: "RECOMPRA INTELIGENTE", title: "A próxima compra\ndeixa sinais.", body: "Histórico consistente ajuda a identificar a provável recompra pelo app.", cta: "CONHEÇA O COREPET", accent: "#34d399", image: "erp-recorrencia.png", label: "TELA REAL DO COREPET" },
  { file: "03-clinica-veterinaria-piloto.png", tag: "CLÍNICA VETERINÁRIA • PILOTO", title: "Agenda, prontuário\ne controle clínico.", body: "Uma demonstração guiada mostra a vertical veterinária em beta/piloto.", cta: "AGENDAR DEMONSTRAÇÃO", accent: "#60a5fa" },
  { file: "04-banho-tosa-operacao.png", tag: "BANHO & TOSA", title: "A agenda não pode\nser uma adivinhação.", body: "Capacidade, equipe, recurso e pet na mesma operação.", cta: "VEJA O MÓDULO", accent: "#f472b6" },
];

const carousels = [
  { slug: "05-carrossel-estoque-lista-espera", accent: "#f59e0b", slides: [
    ["ESTOQUE E VENDA", "Produto em falta não precisa encerrar a conversa.", "Arraste para ver uma oportunidade que não depende da memória da equipe."],
    ["01", "Registre o interesse.", "A lista de espera organiza quem procurou o produto."],
    ["02", "O produto voltou ao estoque.", "O CorePet reconhece a reposição."],
    ["03", "O cliente pode ser avisado pelo app.", "A oportunidade volta para a conversa no momento certo."],
    ["COREPET", "Estoque também é relacionamento.", "Peça uma demonstração pelo link do perfil."]
  ]},
  { slug: "06-carrossel-banho-tosa", accent: "#f472b6", slides: [
    ["BANHO & TOSA", "O dia começa na agenda.\nNão no improviso.", "Uma operação organizada conecta atendimento, equipe e recursos."],
    ["01", "Agende respeitando capacidade.", "O módulo considera pet, profissional e recurso para evitar conflitos."],
    ["02", "Acompanhe o atendimento.", "Check-in, fila e etapas deixam o dia mais visível."],
    ["03", "Conheça o custo do atendimento.", "Insumos, mão de obra e outros itens apoiam o cálculo de margem."],
    ["COREPET", "Banho & tosa com operação centralizada.", "Solicite uma demonstração pelo link do perfil."]
  ]}
];

function esc(s) { return String(s).replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;"); }
function shell(content, size, accent) { return `<!doctype html><meta charset="utf-8"><style>
*{box-sizing:border-box}html,body{margin:0;width:${size[0]}px;height:${size[1]}px;overflow:hidden;background:#020817;color:#fff;font-family:Inter,Segoe UI,Arial,sans-serif}body{position:relative;background:radial-gradient(circle at 85% 12%,${accent}55,transparent 34%),radial-gradient(circle at 8% 88%,#7c3aed44,transparent 40%),linear-gradient(145deg,#020617,#0c1b32)}body:after{content:"";position:absolute;inset:0;background-image:linear-gradient(#fff0 96%,#ffffff08),linear-gradient(90deg,#fff0 96%,#ffffff08);background-size:54px 54px;pointer-events:none}.brand{position:absolute;z-index:5;top:48px;left:58px;display:flex;align-items:center;gap:13px;font-size:36px;font-weight:900;letter-spacing:-1px}.brand img{width:58px;height:58px;border-radius:15px}.footer{position:absolute;z-index:5;right:42px;bottom:30px;color:#cbd5e1;font-weight:700;font-size:18px}.tag{color:${accent};font-size:21px;font-weight:900;letter-spacing:.14em}.cta{display:inline-block;margin-top:30px;padding:16px 22px;border-radius:14px;background:${accent};color:#08111f;font-weight:950;font-size:18px;letter-spacing:.06em}.screen{position:absolute;z-index:3;left:60px;right:60px;bottom:72px;height:490px;margin:0;padding:42px 12px 12px;border:2px solid #334155;border-radius:26px;background:#f8fafc;overflow:hidden;box-shadow:0 30px 90px #000a}.screen:before{content:"";position:absolute;left:19px;top:15px;width:11px;height:11px;border-radius:50%;background:#fb7185;box-shadow:20px 0 #fbbf24,40px 0 #34d399}.screen img{width:100%;height:100%;object-fit:cover;border-radius:12px}.label{position:absolute;z-index:4;right:82px;bottom:530px;color:#334155;font-size:14px;font-weight:950;letter-spacing:.1em}.glyph{position:absolute;z-index:1;right:50px;bottom:115px;font-size:440px;font-weight:950;line-height:.7;color:${accent}22}.panel{position:absolute;z-index:2;left:60px;right:60px;bottom:115px;padding:28px;border:1px solid #ffffff22;border-radius:22px;background:#ffffff0b;color:#dbeafe;font-size:27px;line-height:1.35}</style><div class="brand"><img src="${url(logo)}">CorePet</div>${content}<div class="footer">@corepet.erp</div>`; }
function feed(p) { const media = p.image ? `<figure class="screen"><img src="${url(join(shots,p.image))}"></figure><span class="label">${p.label}</span>` : `<div class="glyph">✦</div><div class="panel">Demonstração guiada para entender a realidade da sua operação.</div>`; return shell(`<main style="position:absolute;z-index:4;left:60px;right:60px;top:178px"><div class="tag">${p.tag}</div><h1 style="margin:17px 0 0;font-size:75px;line-height:.98;letter-spacing:-3.5px;white-space:pre-line">${esc(p.title)}</h1><p style="margin:25px 0 0;max-width:870px;color:#dbeafe;font-size:29px;line-height:1.35;font-weight:600">${esc(p.body)}</p><span class="cta">${p.cta}</span></main>${media}`,[1080,1350],p.accent); }
function carousel(slide, accent, index, total) { const [tag,title,body]=slide; const dot=Array.from({length:total},(_,i)=>`<i style="height:6px;flex:1;border-radius:8px;background:${i===index?accent:'#ffffff25'}"></i>`).join(''); return shell(`<main style="position:absolute;z-index:4;left:62px;right:62px;top:190px"><div class="tag">${tag}</div><h1 style="margin:24px 0 0;font-size:${title.length>42?65:78}px;line-height:.99;letter-spacing:-3.5px;white-space:pre-line">${esc(title)}</h1><p style="margin:28px 0 0;max-width:870px;color:#dbeafe;font-size:31px;line-height:1.38;font-weight:600">${esc(body)}</p></main><div class="glyph" style="font-size:390px">${index+1}</div><div style="position:absolute;z-index:4;left:62px;right:62px;bottom:55px;display:flex;gap:8px">${dot}</div>`,[1080,1350],accent); }
function reelFrame(tag,title,body,accent) { return shell(`<main style="position:absolute;z-index:4;left:68px;right:68px;top:430px"><div class="tag">${tag}</div><h1 style="margin:22px 0 0;font-size:91px;line-height:.96;letter-spacing:-4px">${title}</h1><p style="margin:30px 0 0;color:#dbeafe;font-size:38px;line-height:1.36;font-weight:600">${body}</p><span class="cta" style="font-size:22px">DEMONSTRAÇÃO PELO LINK DO PERFIL</span></main><div class="glyph" style="font-size:520px;bottom:260px">✦</div>`,[1080,1920],accent); }
function capture(html, out, size) { mkdirSync(dirname(out),{recursive:true}); const source=join(work,`${out.replaceAll(/[\\/:]/g,'-')}.html`); writeFileSync(source,html,'utf8'); const r=spawnSync(chrome,["--headless=new","--hide-scrollbars","--disable-gpu","--allow-file-access-from-files",`--window-size=${size[0]},${size[1]}`,"--force-device-scale-factor=1",`--screenshot=${out}`,url(source)],{encoding:'utf8'}); if(r.status!==0||!existsSync(out)) throw new Error(r.stderr||r.stdout||`Falha em ${out}`); }
function run(cmd,args,label){const r=spawnSync(cmd,args,{encoding:'utf8'});if(r.status!==0)throw new Error(`${label}: ${r.stderr||r.stdout}`)}
rmSync(work,{recursive:true,force:true}); mkdirSync(work,{recursive:true}); mkdirSync(output,{recursive:true});
for(const p of pieces) capture(feed(p),join(output,p.file),[1080,1350]);
for(const c of carousels)c.slides.forEach((s,i)=>capture(carousel(s,c.accent,i,c.slides.length),join(output,c.slug,`${String(i+1).padStart(2,'0')}.png`),[1080,1350]));
const frames=[
  ["RECOMPRA INTELIGENTE","A próxima compra deixa sinais.","Histórico consistente pode indicar a provável recompra.","#34d399"],
  ["NO APP","O lembrete leva ao produto.","O cliente abre diretamente o item quando toca no aviso.","#60a5fa"],
  ["COREPET","Venda ativa com contexto.","Conheça em uma demonstração guiada.","#f59e0b"]
];
const reelDir=join(work,"reel"); mkdirSync(reelDir,{recursive:true}); const segments=[];
frames.forEach((f,i)=>{const frame=join(reelDir,`frame-${i}.png`);capture(reelFrame(...f),frame,[1080,1920]);const segment=join(reelDir,`segment-${i}.mp4`);run(ffmpeg,["-y","-loop","1","-i",frame,"-t","4.5","-vf","scale=1080:1920,format=yuv420p","-r","30","-an","-c:v","libx264","-crf","19",segment],`Cena ${i+1}`);segments.push(segment)});
const list=join(reelDir,"concat.txt");writeFileSync(list,segments.map(x=>`file '${x.replaceAll("'","'\\''")}'`).join('\n'));const audio=join(reelDir,"audio.mp3");run(edgeTts,["--voice","pt-BR-AntonioNeural","--rate=+2%","--text","A próxima compra deixa sinais. O CorePet usa um histórico consistente para identificar a provável recompra. Pelo app, o cliente pode abrir diretamente o produto. Venda ativa com contexto. Conheça o CorePet em uma demonstração guiada.","--write-media",audio],"Narração");run(ffmpeg,["-y","-f","concat","-safe","0","-i",list,"-i",audio,"-c:v","copy","-c:a","aac","-b:a","160k","-shortest","-movflags","+faststart",join(output,"07-reel-recompra-com-contexto.mp4")],"Reel");
console.log(`Lote criado em ${output}`);
