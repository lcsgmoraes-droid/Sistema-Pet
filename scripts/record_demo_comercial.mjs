import { spawn } from "node:child_process";
import { existsSync, mkdirSync } from "node:fs";
import { join } from "node:path";
import os from "node:os";

const baseUrl = process.env.COREPET_BASE_URL || "http://127.0.0.1:5173";
const email = process.env.COREPET_DEMO_EMAIL || "corepeterp@gmail.com";
const password = process.env.COREPET_DEMO_PASSWORD;
const chromePath =
  process.env.CHROME_PATH || "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";
const ffmpegPath =
  process.env.FFMPEG_PATH ||
  join(
    process.env.LOCALAPPDATA || "",
    "Microsoft",
    "WinGet",
    "Packages",
    "Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe",
    "ffmpeg-8.1.2-full_build",
    "bin",
    "ffmpeg.exe",
  );
const outputDir =
  process.env.COREPET_RECORD_OUTPUT_DIR ||
  join(os.homedir(), "Videos", "SistemaPetDemo");
const outputFile = join(
  outputDir,
  `sistema-pet_demo-comercial_sem-audio_${new Date()
    .toISOString()
    .slice(0, 19)
    .replace(/[:T]/g, "-")}.mp4`,
);
const debugPort = Number(process.env.COREPET_CHROME_DEBUG_PORT || 9333);
const profileDir = join(os.tmpdir(), `corepet-record-profile-${Date.now()}`);

if (!password) {
  throw new Error("Defina COREPET_DEMO_PASSWORD antes de gravar.");
}
if (!existsSync(chromePath)) {
  throw new Error(`Chrome nao encontrado em ${chromePath}`);
}
if (!existsSync(ffmpegPath)) {
  throw new Error(`FFmpeg nao encontrado em ${ffmpegPath}`);
}
mkdirSync(outputDir, { recursive: true });

const wait = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

class CdpClient {
  constructor(wsUrl) {
    this.ws = new WebSocket(wsUrl);
    this.nextId = 1;
    this.pending = new Map();
    this.events = [];
    this.ws.addEventListener("message", (message) => {
      const payload = JSON.parse(message.data);
      if (payload.id && this.pending.has(payload.id)) {
        const { resolve, reject } = this.pending.get(payload.id);
        this.pending.delete(payload.id);
        if (payload.error) reject(new Error(JSON.stringify(payload.error)));
        else resolve(payload.result);
        return;
      }
      if (payload.method) this.events.push(payload);
    });
  }

  async ready() {
    if (this.ws.readyState === WebSocket.OPEN) return;
    await new Promise((resolve, reject) => {
      this.ws.addEventListener("open", resolve, { once: true });
      this.ws.addEventListener("error", reject, { once: true });
    });
  }

  async send(method, params = {}) {
    await this.ready();
    const id = this.nextId++;
    const message = JSON.stringify({ id, method, params });
    const promise = new Promise((resolve, reject) => {
      this.pending.set(id, { resolve, reject });
    });
    this.ws.send(message);
    return promise;
  }

  close() {
    this.ws.close();
  }
}

async function fetchJson(url, attempts = 80) {
  let lastError;
  for (let i = 0; i < attempts; i += 1) {
    try {
      const response = await fetch(url);
      if (response.ok) return response.json();
      lastError = new Error(`HTTP ${response.status}`);
    } catch (error) {
      lastError = error;
    }
    await wait(250);
  }
  throw lastError;
}

async function connectToChrome() {
  const tabs = await fetchJson(`http://127.0.0.1:${debugPort}/json`);
  const page = tabs.find((tab) => tab.type === "page") || tabs[0];
  if (!page?.webSocketDebuggerUrl) {
    throw new Error("Nao encontrei aba do Chrome com CDP ativo.");
  }
  const cdp = new CdpClient(page.webSocketDebuggerUrl);
  await cdp.ready();
  await cdp.send("Page.enable");
  await cdp.send("Runtime.enable");
  try {
    const { windowId } = await cdp.send("Browser.getWindowForTarget", {
      targetId: page.id,
    });
    await cdp.send("Browser.setWindowBounds", {
      windowId,
      bounds: { left: 0, top: 0, width: 1920, height: 1080, windowState: "normal" },
    });
  } catch {
    // Some Chrome builds reject window commands for fresh profile targets.
    // The launch flags still position a regular visible window for recording.
  }
  return cdp;
}

async function evaluate(cdp, expression) {
  const result = await cdp.send("Runtime.evaluate", {
    expression,
    awaitPromise: true,
    returnByValue: true,
  });
  if (result.exceptionDetails) {
    throw new Error(JSON.stringify(result.exceptionDetails));
  }
  return result.result?.value;
}

async function waitFor(cdp, expression, timeoutMs = 15000) {
  const start = Date.now();
  while (Date.now() - start < timeoutMs) {
    const result = await evaluate(cdp, expression);
    if (result) return result;
    await wait(300);
  }
  throw new Error(`Timeout aguardando: ${expression}`);
}

async function navigate(cdp, path) {
  await cdp.send("Page.navigate", { url: `${baseUrl}${path}` });
  await waitFor(
    cdp,
    `document.readyState === "complete" || document.readyState === "interactive"`,
    20000,
  );
  await suppressGuidedTours(cdp);
  await wait(1200);
}

async function login(cdp) {
  await navigate(cdp, "/login");
  await evaluate(
    cdp,
    `(() => {
      const setValue = (el, value) => {
        const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "value").set;
        setter.call(el, value);
        el.dispatchEvent(new Event("input", { bubbles: true }));
        el.dispatchEvent(new Event("change", { bubbles: true }));
      };
      const inputs = Array.from(document.querySelectorAll("input"));
      const emailInput =
        document.querySelector('input[type="email"]') ||
        inputs.find((input) => /email|e-mail|usuario|login/i.test(input.name || input.placeholder || "")) ||
        inputs[0];
      const passwordInput =
        document.querySelector('input[type="password"]') ||
        inputs.find((input) => /senha|password/i.test(input.name || input.placeholder || "")) ||
        inputs[1];
      if (!emailInput || !passwordInput) return { ok: false, reason: "inputs" };
      setValue(emailInput, ${JSON.stringify(email)});
      setValue(passwordInput, ${JSON.stringify(password)});
      const button =
        Array.from(document.querySelectorAll("button")).find((btn) =>
          /entrar|acessar|login/i.test(btn.textContent || "")
        ) || document.querySelector('button[type="submit"]');
      if (!button) return { ok: false, reason: "button" };
      button.click();
      return { ok: true };
    })()`,
  );
  await waitFor(cdp, `!location.pathname.includes("/login")`, 20000);
  await suppressGuidedTours(cdp);
}

async function suppressGuidedTours(cdp) {
  await evaluate(
    cdp,
    `(() => {
      const tourKeys = [
        "dashboard",
        "produtos",
        "pdv",
        "pessoas",
        "lembretes",
        "meus_caixas",
      ];
      for (const key of tourKeys) {
        localStorage.setItem("tour_visto_" + key, "1");
      }

      for (const button of document.querySelectorAll(".driver-popover button, button[aria-label*='Fechar'], button[aria-label*='Close']")) {
        const text = (button.textContent || "").trim();
        const label = button.getAttribute("aria-label") || "";
        if (text === "×" || /fechar|close|pular|concluir/i.test(text + " " + label)) {
          button.click();
        }
      }

      for (const el of document.querySelectorAll(".driver-popover, .driver-overlay, .driver-active-element")) {
        el.remove();
      }

      document.body.classList.remove("driver-active");
      return true;
    })()`,
  );
}

async function caption(cdp, text) {
  await evaluate(
    cdp,
    `(() => {
      let el = document.getElementById("corepet-demo-caption");
      if (!el) {
        el = document.createElement("div");
        el.id = "corepet-demo-caption";
        Object.assign(el.style, {
          position: "fixed",
          left: "28px",
          bottom: "28px",
          zIndex: "2147483647",
          maxWidth: "680px",
          padding: "14px 18px",
          borderRadius: "10px",
          background: "rgba(2, 6, 23, 0.84)",
          color: "#fff",
          fontFamily: "Inter, Arial, sans-serif",
          fontSize: "24px",
          lineHeight: "1.25",
          boxShadow: "0 12px 32px rgba(0,0,0,0.28)",
          pointerEvents: "none",
        });
        document.body.appendChild(el);
      }
      el.textContent = ${JSON.stringify(text)};
    })()`,
  );
}

async function clickText(cdp, text) {
  await evaluate(
    cdp,
    `(() => {
      const target = Array.from(document.querySelectorAll("button, [role='tab'], a"))
        .find((el) => (el.textContent || "").trim().includes(${JSON.stringify(text)}));
      if (target) target.click();
      return Boolean(target);
    })()`,
  );
  await wait(700);
}

async function scrollTo(cdp, top) {
  await evaluate(cdp, `window.scrollTo({ top: ${top}, behavior: "smooth" }); true`);
  await wait(900);
}

async function pinChromeWindow() {
  const escapedProfileDir = profileDir.replace(/'/g, "''");
  const script = `
    Add-Type @"
using System;
using System.Runtime.InteropServices;
public class CorePetWin32 {
  [DllImport("user32.dll")] public static extern bool SetWindowPos(IntPtr hWnd, IntPtr hWndInsertAfter, int X, int Y, int cx, int cy, UInt32 uFlags);
  [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr hWnd, int nCmdShow);
}
"@
    $profile = '${escapedProfileDir}'
    $pids = Get-CimInstance Win32_Process -Filter "name = 'chrome.exe'" |
      Where-Object { $_.CommandLine -like "*$profile*" } |
      Select-Object -ExpandProperty ProcessId
    if (-not $pids) { exit 0 }
    $window = Get-Process chrome |
      Where-Object { $pids -contains $_.Id -and $_.MainWindowHandle -ne 0 } |
      Sort-Object StartTime -Descending |
      Select-Object -First 1
    if (-not $window) { exit 0 }
    $hWnd = $window.MainWindowHandle
    [CorePetWin32]::ShowWindow($hWnd, 1) | Out-Null
    [CorePetWin32]::SetWindowPos($hWnd, [IntPtr](-1), 0, 0, 1920, 1080, 0x0040) | Out-Null
  `;
  await new Promise((resolve) => {
    const proc = spawn(
      "powershell.exe",
      ["-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", script],
      { stdio: "ignore", windowsHide: true },
    );
    proc.on("exit", resolve);
    proc.on("error", resolve);
  });
}

async function calculatorAction(cdp) {
  await evaluate(
    cdp,
    `(() => {
      const inputs = Array.from(document.querySelectorAll("input"));
      const numbers = inputs.filter((input) => input.type === "number" || /peso|idade/i.test(input.getAttribute("aria-label") || input.placeholder || ""));
      const setValue = (el, value) => {
        const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "value").set;
        setter.call(el, value);
        el.dispatchEvent(new Event("input", { bubbles: true }));
        el.dispatchEvent(new Event("change", { bubbles: true }));
      };
      if (numbers[0]) setValue(numbers[0], "12");
      if (numbers[1]) setValue(numbers[1], "36");
      const button = Array.from(document.querySelectorAll("button"))
        .find((btn) => /Comparar Todas/i.test(btn.textContent || ""));
      if (button) button.click();
      return Boolean(button);
    })()`,
  );
  await wait(1800);
}

function startFfmpeg() {
  const args = [
    "-y",
    "-f",
    "gdigrab",
    "-framerate",
    "20",
    "-offset_x",
    "0",
    "-offset_y",
    "0",
    "-video_size",
    "1920x1080",
    "-i",
    "desktop",
    "-c:v",
    "libx264",
    "-preset",
    "veryfast",
    "-crf",
    "24",
    "-pix_fmt",
    "yuv420p",
    outputFile,
  ];
  const proc = spawn(ffmpegPath, args, { stdio: ["pipe", "pipe", "pipe"] });
  proc.stderr.on("data", (chunk) => {
    const line = chunk.toString();
    if (/frame=|Output #|Input #|error/i.test(line)) process.stderr.write(line);
  });
  return proc;
}

async function stopFfmpeg(proc) {
  proc.stdin.write("q");
  await new Promise((resolve) => proc.on("exit", resolve));
}

async function runRecording(cdp) {
  await pinChromeWindow();
  const ffmpeg = startFfmpeg();
  await wait(1500);

  await navigate(cdp, "/financeiro/vendas");
  await pinChromeWindow();
  await clickText(cdp, "Lista de Vendas");
  await caption(cdp, "Vendas com rentabilidade: canal, taxas, imposto, CMV, lucro e margem");
  await wait(7000);
  await scrollTo(cdp, 440);
  await wait(5000);

  await navigate(cdp, "/produtos");
  await pinChromeWindow();
  await caption(cdp, "Produtos reais: imagem, custo, preco, margem, estoque e canais");
  await wait(8500);

  await navigate(cdp, "/calculadora-racao");
  await pinChromeWindow();
  await caption(cdp, "Comparador de racao: custo por dia, custo por mes e preco por kg");
  await calculatorAction(cdp);
  await wait(9000);

  await navigate(cdp, "/financeiro/contas-receber");
  await pinChromeWindow();
  await caption(cdp, "Recebimentos: previsao, aberto e efetivamente recebido");
  await wait(8000);

  await navigate(cdp, "/financeiro/contas-pagar");
  await pinChromeWindow();
  await caption(cdp, "Custos: imposto, entrega, comissao, taxas e despesas fixas");
  await wait(8000);

  await navigate(cdp, "/financeiro/fluxo-caixa");
  await pinChromeWindow();
  await caption(cdp, "Fluxo de caixa: entradas, saidas, previsto e realizado");
  await wait(8000);

  await navigate(cdp, "/entregas/rotas");
  await pinChromeWindow();
  await caption(cdp, "Entregas: rota pendente, rota em andamento e entregador");
  await wait(9000);

  await navigate(cdp, "/comissoes");
  await pinChromeWindow();
  await caption(cdp, "Comissoes: regra geral para vendedor comissionado");
  await wait(6500);

  await navigate(cdp, "/comissoes/abertas");
  await pinChromeWindow();
  await caption(cdp, "Comissoes em aberto: valores pendentes para conferencia");
  await wait(6500);

  await navigate(cdp, "/financeiro");
  await pinChromeWindow();
  await caption(cdp, "Fechamento executivo: alertas, risco e leitura automatica");
  await wait(8500);

  await stopFfmpeg(ffmpeg);
}

const chrome = spawn(
  chromePath,
  [
    `--remote-debugging-port=${debugPort}`,
    `--user-data-dir=${profileDir}`,
    "--new-window",
    "--window-position=0,0",
    "--window-size=1920,1080",
    "--force-device-scale-factor=1",
    `${baseUrl}/login`,
  ],
  { stdio: "ignore", detached: false },
);

let cdp;
try {
  cdp = await connectToChrome();
  await login(cdp);
  await runRecording(cdp);
  console.log(JSON.stringify({ ok: true, outputFile }, null, 2));
} finally {
  if (cdp) {
    try {
      await cdp.send("Browser.close");
    } catch {
      cdp.close();
    }
  }
  if (!chrome.killed) chrome.kill();
}
