// HAL sinematik Reels: Chrome (CDP) ile deterministik kare -> ffmpeg MP4.
// Kullanim: node render.mjs <01-gonderildi|02-agirlik|03-lansman|hepsi> [--kareler 0,1.5,3]
// HAL_APP, CHROME, EKRAN, CIKTI ortam degiskenleriyle degistirilebilir.
import { spawn, execFileSync } from 'node:child_process';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { synth } from './ses.mjs';

const DIR = path.dirname(fileURLToPath(import.meta.url));
const APP = process.env.HAL_APP || path.resolve(DIR, '../../../ckappdesign/app');
const CHROME = process.env.CHROME || 'C:/Program Files/Google/Chrome/Application/chrome.exe';
const EKRAN = process.env.EKRAN || path.resolve(DIR, '../../../hal-kaynaklar/ekran');
const OUT = process.env.CIKTI || path.resolve(DIR, '../../../hal-kaynaklar/sosyal/v2');
const W = 1080, H = 1920, FPS = 30;
const VIDEOS = ['01-gonderildi', '02-agirlik', '03-lansman'];

const args = process.argv.slice(2);
const secim = args[0] || 'hepsi';
const ki = args.indexOf('--kareler');
const kareler = ki >= 0 ? args[ki + 1].split(',').map(Number) : null;
if (secim !== 'hepsi' && !VIDEOS.includes(secim)) throw new Error(`Bilinmeyen video: ${secim}`);

const items = JSON.parse(fs.readFileSync(path.join(APP, 'assets/content/items.json'), 'utf8'));
const meal = JSON.parse(fs.readFileSync(path.join(APP, 'assets/content/meal/elmalili.json'), 'utf8')).texts;

function ayet(key) {
  const x = items.find(i => i.translation_key === key);
  if (!x) throw new Error(`items.json'da ${key} yok`);
  if (x.verified !== true) throw new Error(`${key} verified degil`);
  if (!meal[key]) throw new Error(`${key} meali yok`);
  return { ar: x.arabic, meal: meal[key], ref: `${x.surah_name} ${x.surah}:${x.ayah}${x.ayah_end ? '-' + x.ayah_end : ''}` };
}

const font = (ad, dosya, stil = 'normal', agirlik = '200 900') =>
  `@font-face{font-family:${ad};font-style:${stil};font-weight:${agirlik};src:url(data:font/ttf;base64,${fs.readFileSync(path.join(APP, 'assets/fonts', dosya)).toString('base64')})}`;
const FONTS = [font('HalSerif', 'SourceSerif4.ttf'), font('HalSerif', 'SourceSerif4-Italic.ttf', 'italic'), font('HalAmiri', 'AmiriQuran-Regular.ttf', 'normal', 'normal')].join('\n');
const jpg = f => 'data:image/jpeg;base64,' + fs.readFileSync(path.join(EKRAN, f)).toString('base64');

const VERI = {
  a1: ayet('93:3'), a2: ayet('94:5'),
  screens: { a: jpg('WhatsApp Image 2026-11-21 at 20.38.10 (3).jpeg'), b: jpg('WhatsApp Image 2026-11-21 at 20.38.09 (6).jpeg') },
};

const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'hal-sinema-'));
const sayfa = path.join(tmp, 'sahne.html');
fs.writeFileSync(sayfa, fs.readFileSync(path.join(DIR, 'sahne.html'), 'utf8')
  .split('{{FONTS}}').join(FONTS).split('{{VERI}}').join(JSON.stringify(VERI)).split('{{JS}}').join(fs.readFileSync(path.join(DIR, 'sahne.js'), 'utf8')));

let chrome = null;
const temizle = () => { try { chrome?.kill(); } catch { /* kapanmis */ } setTimeout(() => fs.rmSync(tmp, { recursive: true, force: true }), 500); };
process.on('exit', () => { try { chrome?.kill(); } catch { /* kapanmis */ } });
process.on('SIGINT', () => { chrome?.kill(); fs.rmSync(tmp, { recursive: true, force: true, maxRetries: 5, retryDelay: 200 }); process.exit(1); });

async function baslat() {
  const prof = path.join(tmp, 'profil');
  chrome = spawn(CHROME, ['--headless=new', '--remote-debugging-port=0', '--remote-debugging-address=127.0.0.1', `--user-data-dir=${prof}`,
    '--remote-allow-origins=http://127.0.0.1', '--no-first-run', '--disable-extensions', '--hide-scrollbars', '--force-device-scale-factor=1',
    '--use-angle=d3d11', '--ignore-gpu-blocklist', '--enable-unsafe-swiftshader', `--window-size=${W},${H}`, 'about:blank'], { stdio: 'ignore' });
  const portDosya = path.join(prof, 'DevToolsActivePort');
  for (let i = 0; i < 100 && !fs.existsSync(portDosya); i++) await new Promise(r => setTimeout(r, 100));
  if (!fs.existsSync(portDosya)) throw new Error('Chrome debug portu acilmadi');
  const port = fs.readFileSync(portDosya, 'utf8').split('\n')[0];
  const liste = await (await fetch(`http://127.0.0.1:${port}/json/list`)).json();
  const ws = new WebSocket(liste.find(x => x.type === 'page').webSocketDebuggerUrl);
  await new Promise((res, rej) => { ws.onopen = res; ws.onerror = rej; });
  let id = 0; const bekle = new Map();
  ws.onmessage = m => { const d = JSON.parse(m.data); const p = bekle.get(d.id); if (p) { bekle.delete(d.id); d.error ? p.rej(new Error(JSON.stringify(d.error))) : p.res(d.result); } };
  const send = (method, params = {}) => new Promise((res, rej) => { bekle.set(++id, { res, rej }); ws.send(JSON.stringify({ id, method, params })); });
  await send('Page.enable');
  await send('Emulation.setDeviceMetricsOverride', { width: W, height: H, deviceScaleFactor: 1, mobile: false });
  return send;
}

const ev = async (send, expression) => {
  const r = await send('Runtime.evaluate', { expression, awaitPromise: true, returnByValue: true });
  if (r.exceptionDetails) throw new Error(r.exceptionDetails.exception?.description || r.exceptionDetails.text);
  return r.result.value;
};

async function kare(send, t) {
  await ev(send, `seek(${t});new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)))`);
  const r = await send('Page.captureScreenshot', { format: 'png', optimizeForSpeed: true });
  return Buffer.from(r.data, 'base64');
}

async function video(send, ad) {
  await send('Page.navigate', { url: 'file:///' + sayfa.replace(/\\/g, '/') });
  await new Promise(r => setTimeout(r, 800));
  const { dur, cues } = await ev(send, `init(${JSON.stringify(ad)})`);
  fs.mkdirSync(OUT, { recursive: true });

  if (kareler) {
    const kd = path.join(OUT, 'onizleme'); fs.mkdirSync(kd, { recursive: true });
    for (const t of kareler) fs.writeFileSync(path.join(kd, `${ad}-${String(Math.round(t * 1000)).padStart(5, '0')}.png`), await kare(send, t));
    return;
  }

  const wav = path.join(tmp, ad + '.wav'), ses = path.join(tmp, ad + '.m4a');
  fs.writeFileSync(wav, synth(cues, dur));
  execFileSync('ffmpeg', ['-y', '-loglevel', 'error', '-i', wav, '-af',
    `aecho=0.7:0.5:70|140|230:0.3|0.2|0.12,atrim=0:${dur},loudnorm=I=-16:TP=-1.5:LRA=7,alimiter=limit=0.75:level=false,afade=t=out:st=${dur - .25}:d=0.25`,
    '-ar', '48000', '-c:a', 'aac', '-b:a', '128k', ses]);

  const mp4 = path.join(OUT, ad + '.mp4'), n = Math.round(dur * FPS);
  const ff = spawn('ffmpeg', ['-y', '-loglevel', 'error', '-f', 'image2pipe', '-framerate', String(FPS), '-c:v', 'png', '-i', '-', '-i', ses,
    '-vf', 'scale=out_color_matrix=bt709:flags=lanczos,format=yuv420p', '-colorspace', 'bt709', '-color_primaries', 'bt709', '-color_trc', 'bt709',
    '-c:v', 'libx264', '-preset', 'slow', '-crf', '20', '-maxrate', '12M', '-bufsize', '24M', '-g', '60', '-r', String(FPS), '-c:a', 'copy', '-t', String(dur), '-movflags', '+faststart', mp4],
    { stdio: ['pipe', 'inherit', 'inherit'] });
  const bitti = new Promise((res, rej) => { ff.on('exit', c => c === 0 ? res() : rej(new Error(`ffmpeg cikis ${c}`))); ff.stdin.on('error', rej); });
  const t0 = Date.now();
  for (let i = 0; i < n; i++) {
    if (!ff.stdin.write(await kare(send, i / FPS))) await new Promise(r => ff.stdin.once('drain', r));
    if (i % 60 === 0) console.log(`${ad}: ${i}/${n}`);
  }
  ff.stdin.end(); await bitti;
  console.log(`${ad}: ${((Date.now() - t0) / 1000).toFixed(0)} sn`);

  execFileSync('ffmpeg', ['-y', '-loglevel', 'error', '-i', mp4, '-vf', `fps=12/${dur},scale=270:480,tile=6x2`, '-frames:v', '1', path.join(OUT, `${ad}-serit.png`)]);
}

try {
  const send = await baslat();
  for (const ad of secim === 'hepsi' ? VIDEOS : [secim]) await video(send, ad);
} finally {
  temizle();
}
