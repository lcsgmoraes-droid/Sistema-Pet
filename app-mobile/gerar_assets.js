// Script para gerar os assets necessários para o Expo
// Cria imagens PNG sólidas com a cor primária do app (#2563EB = R:37 G:99 B:235)
const fs = require('fs');
const zlib = require('zlib');

function crc32(buf) {
  let c = 0xFFFFFFFF;
  for (const b of buf) { c ^= b; for (let i = 0; i < 8; i++) c = (c & 1) ? (0xEDB88320 ^ (c >>> 1)) : (c >>> 1); }
  return (c ^ 0xFFFFFFFF) >>> 0;
}
function chunk(type, data) {
  const t = Buffer.from(type); const h = Buffer.alloc(4); h.writeUInt32BE(data.length); const crcBuf = Buffer.concat([t, data]); const c = Buffer.alloc(4); c.writeUInt32BE(crc32(crcBuf)); return Buffer.concat([h, t, data, c]);
}
function makePNG(w, h, r, g, b) {
  const sig = Buffer.from([0x89,0x50,0x4E,0x47,0x0D,0x0A,0x1A,0x0A]);
  const ihdrD = Buffer.alloc(13); ihdrD.writeUInt32BE(w,0); ihdrD.writeUInt32BE(h,4); ihdrD[8]=8; ihdrD[9]=2;
  const row = Buffer.alloc(w*3+1); row[0]=0; for(let x=0;x<w;x++){row[1+x*3]=r;row[2+x*3]=g;row[3+x*3]=b;}
  const raw = Buffer.concat(Array(h).fill(row));
  const compressed = zlib.deflateSync(raw, {level:1});
  return Buffer.concat([sig, chunk('IHDR',ihdrD), chunk('IDAT',compressed), chunk('IEND',Buffer.alloc(0))]);
}

const dir = './assets';
// Azul primário do app
const [R, G, B] = [37, 99, 235];

fs.writeFileSync(dir+'/icon.png',              makePNG(1024, 1024, R, G, B));
fs.writeFileSync(dir+'/adaptive-icon.png',     makePNG(1024, 1024, R, G, B));
fs.writeFileSync(dir+'/splash.png',            makePNG(600,  1200, R, G, B));
fs.writeFileSync(dir+'/favicon.png',           makePNG(32,   32,   R, G, B));
fs.writeFileSync(dir+'/notification-icon.png', makePNG(96,   96,   255, 255, 255));

console.log('✓ Assets criados:', fs.readdirSync(dir).join(', '));
