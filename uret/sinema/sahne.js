const W = 1080, H = 1920, FPS = 30;
const clamp = (x, a = 0, b = 1) => Math.min(b, Math.max(a, x));
const lerp = (a, b, x) => a + (b - a) * x;
const eo = x => 1 - Math.pow(2, -10 * clamp(x));
const eio = x => { x = clamp(x); return x < .5 ? Math.pow(2, 20 * x - 10) / 2 : 1 - Math.pow(2, -20 * x + 10) / 2; };
const h = i => { const s = Math.sin(i * 127.1 + 311.7) * 43758.5453; return s - Math.floor(s); };
const pulse = (t, t0, k) => t < t0 ? 0 : Math.exp(-(t - t0) * k);
const shake = (t, t0, amp) => { const u = t - t0; return u < 0 ? 0 : amp * Math.exp(-u * 9) * Math.sin(u * 75); };
const GOLD = [216, 184, 120];

const cam = document.getElementById('cam');
const fxc = document.getElementById('fx').getContext('2d');
const dustc = document.getElementById('dust').getContext('2d');

// ---------- arka plan: shader ----------
const gl = document.getElementById('gl').getContext('webgl', { preserveDrawingBuffer: true });
const VS = 'attribute vec2 a;void main(){gl_Position=vec4(a,0.,1.);}';
const FS = `precision highp float;
uniform vec2 R;uniform float T,I,G,Z,F,RAY;uniform vec2 L,P;
float h(vec2 p){return fract(sin(dot(p,vec2(127.1,311.7)))*43758.5453);}
float n(vec2 p){vec2 i=floor(p),f=fract(p);f=f*f*(3.-2.*f);
 return mix(mix(h(i),h(i+vec2(1,0)),f.x),mix(h(i+vec2(0,1)),h(i+vec2(1,1)),f.x),f.y);}
float fbm(vec2 p){float a=.5,s=0.;for(int i=0;i<5;i++){s+=a*n(p);p=p*2.03+vec2(1.7,9.2);a*=.5;}return s;}
void main(){
 vec2 uv=gl_FragCoord.xy/R;
 vec2 p=(uv-.5)*vec2(R.x/R.y,1.)/Z+P;
 float t=T*.045;
 float f1=fbm(p*1.5+vec2(t,-t*.6));
 float f2=fbm(p*3.0+f1*1.5+vec2(-t*1.3,t));
 float fog=smoothstep(.22,.92,f2);
 vec2 d=uv-L;d.x*=R.x/R.y;
 float dist=length(d),ang=atan(d.y,d.x);
 float rays=(pow(.5+.5*sin(ang*7.+f1*5.+T*.1),2.)*.6+pow(.5+.5*sin(ang*17.-T*.08+f2*4.),3.)*.4)*(.4+f1);
 float fall=exp(-dist*2.1);
 vec3 gold=vec3(.847,.722,.471);
 vec3 cool=vec3(.30,.78,.58);
 vec3 lc=mix(cool,gold,G);
 vec3 col=vec3(.0196,.0431,.0353);
 col+=vec3(.014,.14,.095)*fog*(1.05-uv.y*.5);
 col+=vec3(.0,.05,.04)*smoothstep(.45,.9,f1)*.9;
 col+=lc*(fall*fall*I*1.25+fall*rays*RAY*I*.3)*(.5+.9*fog);
 col+=gold*F*(exp(-dist*1.8)*1.2+.05)+lc*F*rays*exp(-dist*.9)*.3;
 col-=max(col-.8,0.)*.7;
 col+=(h(gl_FragCoord.xy+T)-.5)/200.;
 gl_FragColor=vec4(col,1.);
}`;
const prog = gl.createProgram();
for (const [ty, src] of [[gl.VERTEX_SHADER, VS], [gl.FRAGMENT_SHADER, FS]]) {
  const s = gl.createShader(ty); gl.shaderSource(s, src); gl.compileShader(s);
  if (!gl.getShaderParameter(s, gl.COMPILE_STATUS)) throw new Error(gl.getShaderInfoLog(s));
  gl.attachShader(prog, s);
}
gl.linkProgram(prog); gl.useProgram(prog);
gl.bindBuffer(gl.ARRAY_BUFFER, gl.createBuffer());
gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1, -1, 3, -1, -1, 3]), gl.STATIC_DRAW);
gl.enableVertexAttribArray(0); gl.vertexAttribPointer(0, 2, gl.FLOAT, false, 0, 0);
const U = n => gl.getUniformLocation(prog, n);

function drawBg(t, b) {
  const v = { lx: .5, ly: .6, I: .5, G: .3, Z: 1, F: 0, RAY: .6, px: 0, py: 0, ...b };
  gl.viewport(0, 0, W, H);
  gl.uniform2f(U('R'), W, H); gl.uniform1f(U('T'), t); gl.uniform2f(U('L'), v.lx, v.ly);
  gl.uniform1f(U('I'), v.I); gl.uniform1f(U('G'), v.G); gl.uniform1f(U('Z'), v.Z);
  gl.uniform1f(U('F'), v.F); gl.uniform1f(U('RAY'), v.RAY); gl.uniform2f(U('P'), v.px, v.py);
  gl.drawArrays(gl.TRIANGLES, 0, 3);
}

// ---------- bokeh tozu ----------
function sprite(rgb) {
  const c = document.createElement('canvas'); c.width = c.height = 128;
  const x = c.getContext('2d'), g = x.createRadialGradient(64, 64, 0, 64, 64, 64);
  g.addColorStop(0, `rgba(${rgb},1)`); g.addColorStop(.45, `rgba(${rgb},.55)`); g.addColorStop(1, `rgba(${rgb},0)`);
  x.fillStyle = g; x.fillRect(0, 0, 128, 128); return c;
}
const SPR = [sprite('226,190,126'), sprite('150,215,185')];
function drawDust(t, d) {
  const { a = 1, sp = 1, lx = .5, ly = .6, Z = 1 } = d;
  dustc.clearRect(0, 0, W, H); dustc.globalCompositeOperation = 'lighter';
  for (let i = 0; i < 150; i++) {
    const z = h(i * 7.3), sz = lerp(10, 90, z * z * z) + 6;
    const span = H * 1.3;
    let x = (h(i * 3.1) * 1.3 - .15) * W + Math.sin(t * (.25 + .4 * h(i * 2.2)) + i) * 50 * z;
    let y = H + 120 - ((h(i * 5.7) * span + t * (14 + 70 * z) * sp) % span);
    x = 540 + (x - 540) * (1 + (Z - 1) * (.4 + z)); y = 960 + (y - 960) * (1 + (Z - 1) * (.4 + z));
    const dx = x / W - lx, dy = 1 - y / H - ly;
    const boost = 1 + 2.2 * Math.exp(-Math.hypot(dx, dy) * 3);
    const tw = .65 + .35 * Math.sin(t * 1.6 + i * 3.3);
    dustc.globalAlpha = clamp(a * (.04 + .2 * h(i * 9.1)) * tw * boost, 0, .6);
    dustc.drawImage(SPR[i % 3 === 0 ? 1 : 0], x - sz / 2, y - sz / 2, sz, sz);
  }
  dustc.globalAlpha = 1;
}

// ---------- kivilcim patlamasi ----------
function sparks(t, t0, cx, cy, n, v, life, seed) {
  const u = t - t0; if (u < 0 || u > life) return;
  fxc.globalCompositeOperation = 'lighter'; fxc.lineCap = 'round';
  const r = (u, sp) => sp * (1 - Math.exp(-3 * u)) / 3;
  for (let i = 0; i < n; i++) {
    const a = h(i * 1.7 + seed) * 6.2832, sp = v * (.2 + Math.pow(h(i * 3.3 + seed), 1.5) * .9);
    const l = life * (.45 + .55 * h(i * 5.1 + seed)); if (u > l) continue;
    const q = u / l, r1 = r(u, sp), r0 = r(Math.max(0, u - .05), sp), g = 60 * u * u;
    fxc.strokeStyle = `rgba(255,${215 + 30 * h(i)},${150 + 40 * h(i * 2)},${Math.pow(1 - q, 1.4)})`;
    fxc.lineWidth = 1.5 + 3 * h(i * 4.4);
    fxc.beginPath(); fxc.moveTo(cx + Math.cos(a) * r0, cy + Math.sin(a) * r0 + g);
    fxc.lineTo(cx + Math.cos(a) * r1, cy + Math.sin(a) * r1 + g); fxc.stroke();
  }
}

// ---------- metin ----------
function mk(cls, text) {
  const d = document.createElement('div'); d.className = 't ' + cls; d.textContent = text;
  d.style.display = 'none'; cam.appendChild(d); return d;
}
function fit(d, maxW) {
  d.style.display = 'block';
  const w = d.offsetWidth; if (w > maxW) d.style.fontSize = (parseFloat(getComputedStyle(d).fontSize) * maxW / w) + 'px';
  d.style.display = 'none';
}
function fitAll(ds, size, maxW) {
  ds.forEach(d => { d.style.fontSize = size + 'px'; fit(d, maxW); });
  const m = Math.min(...ds.map(d => parseFloat(d.style.fontSize)));
  ds.forEach(d => { d.style.fontSize = m + 'px'; });
}
function anim(d, t, s) {
  const { y = 960, x = 0, t0, t1 = 1e9, inD = .6, outD = .5, inK = 'slam', outK = 'dissolve', ls = 0, lsFrom = .14, drift = .02, glow = 0 } = s;
  const pi = (t - t0) / inD, po = (t - t1) / outD;
  if (t < t0 || (outK === 'cut' ? t >= t1 : po >= 1)) { d.style.display = 'none'; return; }
  d.style.display = 'block'; d.style.top = y + 'px';
  const e = eo(pi); let o = 1, b = 0, dy = 0, k = 1, l = ls;
  if (inK === 'slam') { k = lerp(1.45, 1, e); b = (1 - e) * 26; l = lerp(lsFrom, ls, e); o = clamp(pi * 8); }
  else { dy = (1 - e) * 70; b = (1 - e) * 18; k = lerp(.95, 1, e); o = clamp(pi * 2.2); l = lerp(lsFrom * .5, ls, e); }
  if (outK === 'dissolve' && po > 0) { const q = eo(po); o *= 1 - clamp(po * 1.4); b += q * 28; dy -= q * 60; k *= 1 + q * .06; l += q * .06; }
  k *= 1 + drift * Math.max(0, t - t0);
  d.style.opacity = o;
  d.style.filter = (b > .3 ? `blur(${b}px) ` : '') + 'drop-shadow(0 6px 28px rgba(3,8,6,.7)) ' + (glow ? `drop-shadow(0 0 ${glow}px rgba(216,184,120,.55))` : '') || 'none';
  d.style.letterSpacing = l + 'em';
  d.style.transform = `translate(-50%,-50%) translate(${x}px,${dy}px) scale(${k})`;
}
function shineAnim(d, t, t0) { d.style.backgroundPosition = lerp(100, 0, clamp((t - t0) / 1.6)) + '% 0'; }

function ayahBlock(v, arSize) {
  const ar = mk('ar', v.ar); ar.lang = 'ar'; ar.style.fontSize = arSize + 'px';
  const ml = mk('ml', v.meal);
  const rf = mk('rf', v.ref + ' · Meal: Elmalılı Hamdi Yazır');
  const ha = [ar, ml, rf].map(d => { d.style.display = 'block'; const hh = d.offsetHeight; d.style.display = 'none'; return hh; });
  const total = ha[0] + 64 + ha[1] + 56 + ha[2], top = 880 - total / 2;
  return { ar, ml, rf, yAr: top + ha[0] / 2, yMl: top + ha[0] + 64 + ha[1] / 2, yRf: top + ha[0] + 64 + ha[1] + 56 + ha[2] / 2 };
}
function arAnim(d, t, t0, dur, t1, y) {
  const p = (t - t0) / dur, po = (t - t1) / .5;
  if (t < t0 || po >= 1) { d.style.display = 'none'; return; }
  d.style.display = 'block'; d.style.top = y + 'px';
  const e = eio(p), m = lerp(0, 140, e);
  d.style.webkitMaskImage = m >= 135 ? 'none' : `linear-gradient(to left,#000 ${m - 38}%,transparent ${m}%)`;
  let b = (1 - eo(p)) * 8, o = 1, dy = 0;
  if (po > 0) { o = 1 - clamp(po * 1.4); b += eo(po) * 24; dy = -eo(po) * 50; }
  d.style.opacity = o;
  d.style.filter = `blur(${b}px) drop-shadow(0 0 ${6 + 24 * (1 - e)}px rgba(216,184,120,${.3 + .3 * (1 - e)}))`;
  d.style.transform = `translate(-50%,-50%) translateY(${dy}px) scale(${1 + .02 * Math.max(0, t - t0)})`;
}
function ayahAnim(B, t, a) {
  arAnim(B.ar, t, a.arT0, a.arD, a.out, B.yAr);
  anim(B.ml, t, { y: B.yMl, t0: a.mlT0, t1: a.out, inK: 'rise', inD: .7, drift: .006 });
  anim(B.rf, t, { y: B.yRf, t0: a.arT0 + .5, t1: a.out, inK: 'rise', inD: .6, drift: 0 });
}

function endCard(d, t, t0) { return anim(d, t, { y: 880, t0, inD: 1.1, lsFrom: .5, ls: .1, glow: 34, drift: .012 }); }

const SCENES = {};

// ---------- 1: gonderildi ----------
SCENES['01-gonderildi'] = V => {
  const a = [['Bunu sana', 720, -.3], ['biri', 890, .25], ['gönderdiyse', 1060, .6]].map(([s, y, t0]) => ({ d: mk('hk', s), y, t0 }));
  const b = [['seni', 800, 2.2], ['düşünüyor.', 990, 2.32]].map(([s, y, t0]) => ({ d: mk('hk gd', s), y, t0 }));
  fitAll(b.map(x => x.d), 210, 900);
  fitAll(a.map(x => x.d), 190, 900);
  const A = ayahBlock(V.a1, 112);
  const c1 = mk('hk', 'Şimdi sıra\nsende.'), c2 = mk('hk gd', 'Birine gönder.'), hal = mk('hk gd shine', 'HÂL');
  c1.style.fontSize = '130px'; c2.style.fontSize = '120px'; fit(c2, 900); hal.style.fontSize = '250px';
  const DUR = 13.8;
  const cues = [['bed'], ['hit', .02, 1.1], ['hit', .4, 1], ['hit', .85, 1.2], ['riser', 1.4, .8, 1], ['hit', 2.2, 1.9], ['whoosh', 4.3, .9, -1, .7],
    ['whoosh', 4.45, 1.4, -1, .9], ['shimmer', 4.5, 1.6, .5], ['tick', 5.6, .5], ['whoosh', 9.8, .7, 1, .6], ['hit', 10.15, .8], ['hit', 11.1, .9],
    ['riser', 11.5, .8, 1], ['hit', 12.3, 1.8], ['shimmer', 12.3, 1.4, .7]];
  const frame = t => {
    fxc.clearRect(0, 0, W, H);
    for (const x of a) anim(x.d, t, { y: x.y, t0: x.t0, t1: 2.2, outK: 'cut', inD: .55 });
    for (const x of b) anim(x.d, t, { y: x.y, t0: x.t0, t1: 4.4, inD: .7, glow: 36, lsFrom: .1 });
    ayahAnim(A, t, { arT0: 4.4, arD: 1.4, mlT0: 5.5, out: 9.9 });
    anim(c1, t, { y: 800, t0: 10.15, t1: 12.1, inD: .6 });
    anim(c2, t, { y: 1030, t0: 11.1, t1: 12.1, inD: .6, glow: 30 });
    endCard(hal, t, 12.3); shineAnim(hal, t, 12.3);
    sparks(t, 2.2, 540, 880, 220, 1300, 1.5, 3);
    const sw = t >= 4.4 && t < 6.2 ? lerp(1.12, -.12, eio((t - 4.4) / 1.4)) : null;
    const hitP = pulse(t, .02, 7) * .3 + pulse(t, .4, 7) * .3 + pulse(t, .85, 7) * .3 + pulse(t, 11.1, 6) * .2;
    const bg = t < 2.2 ? { lx: .5, ly: .62, I: .8 + hitP, G: .2, RAY: .7, Z: 1 + .03 * t, F: hitP * .04 }
      : t < 4.4 ? { lx: .5, ly: .56, I: .55 + 1.0 * pulse(t, 2.2, 2.4), G: 1, RAY: .8, Z: 1.06 + .01 * (t - 2.2), F: pulse(t, 2.2, 5) * .7 }
      : t < 9.9 ? { lx: sw ?? .22, ly: .52, I: .6 + (sw !== null ? .3 : 0) - .15 * eo((t - 6.2) / 2), G: 1, RAY: 1, Z: 1.05 }
      : t < 12.3 ? { lx: .5, ly: .55, I: .5 + .3 * pulse(t, 10.15, 3) + .3 * pulse(t, 11.1, 3), G: .8, RAY: .9, Z: 1.04 }
      : { lx: .5, ly: .52, I: 1 + pulse(t, 12.3, 2.5), G: 1, RAY: 1.3, F: pulse(t, 12.3, 3.5) * .9, Z: 1.04 };
    drawBg(t, bg);
    const k = 1 + .045 * t / DUR;
    cam.style.transform = `translate(${shake(t, .02, 14) + shake(t, 2.2, 30)}px,${shake(t, .4, 10) + shake(t, .85, 12) + shake(t, 2.2, 22)}px) scale(${k})`;
    drawDust(t, { a: 1, sp: 1 + 3 * pulse(t, 2.2, 1.2), lx: bg.lx, ly: bg.ly, Z: bg.Z });
  };
  return { dur: DUR, cues, frame };
};

// ---------- 2: agirlik ----------
SCENES['02-agirlik'] = V => {
  const w = [['YORGUNUM.', -.25, 1.0], ['YETİŞEMİYORUM.', 1.0, 2.05], ['DAYANAMIYORUM.', 2.05, 3.2]].map(([s, t0, t1]) => {
    const d = mk('hk cap', s); d.style.fontSize = '200px'; d.style.letterSpacing = '-.015em'; fit(d, 900); return { d, t0, t1 };
  });
  const SH = 3.2, LT = 4.5;
  const dy = 960, wd = w[2].d;
  const fs = parseFloat(getComputedStyle(wd).fontSize);
  const pts = (() => {
    const c = document.createElement('canvas'); c.width = W; c.height = 400; const x = c.getContext('2d');
    x.font = `800 ${fs}px HalSerif`; x.letterSpacing = '-.015em'; x.textAlign = 'center'; x.textBaseline = 'middle'; x.fillStyle = '#fff'; x.fillText(wd.textContent, 540, 200);
    const im = x.getImageData(0, 0, W, 400).data, r = [];
    for (let yy = 0; yy < 400; yy += 2) for (let xx = 0; xx < W; xx += 2) if (im[(yy * W + xx) * 4 + 3] > 140) r.push([xx, yy - 200 + dy]);
    return r;
  })();
  const c1 = mk('hk it', 'Bir dakika\ndur.'); c1.style.fontSize = '150px'; c1.style.fontWeight = '500';
  const A = ayahBlock(V.a2, 108);
  const hal = mk('hk gd shine', 'HÂL'), sub = mk('hk it', 'Hâline göre bir ayet.');
  hal.style.fontSize = '250px'; sub.style.fontSize = '64px'; sub.style.fontWeight = '400';
  const DUR = 14.8;
  const cues = [['bed'], ['hit', .02, 1.5], ['hit', 1.0, 1.6], ['hit', 2.05, 1.9], ['whoosh', SH, 1.3, 1, 1], ['riser', 3.4, 1.1, .8],
    ['hit', LT, 1.2], ['shimmer', LT, 1.8, .7], ['whoosh', 6.0, 1.3, -1, .8], ['shimmer', 6.1, 1.4, .4], ['whoosh', 12.2, .7, 1, .6],
    ['riser', 12.0, .6, .8], ['hit', 12.6, 1.6], ['shimmer', 12.6, 1.4, .6]];
  const frame = t => {
    fxc.clearRect(0, 0, W, H);
    w.forEach((x, i) => anim(x.d, t, i < 2 ? { y: dy, t0: x.t0, t1: x.t1, outK: 'cut', inD: .5, lsFrom: .1, ls: -.015, drift: .03 }
      : { y: dy, t0: x.t0, t1: SH + .2, outK: 'cut', inD: .5, lsFrom: .1, ls: -.015, drift: 0 }));
    const u = t - SH;
    if (u > 0 && u < 3) {
      fxc.globalCompositeOperation = 'lighter';
      for (let i = 0; i < pts.length; i++) {
        const [px, py] = pts[i], dl = (px - 90) / 900 * .55 + h(i) * .15, v = u - dl;
        if (v < 0) { fxc.fillStyle = 'rgba(243,235,216,1)'; fxc.fillRect(px - 1, py - 1, 2.4, 2.4); continue; }
        const ang = -Math.PI / 2 + (h(i * 1.3) - .5) * 2.0, sp = 160 + 760 * h(i * 2.7) * h(i * 2.7);
        const rr = sp * (1 - Math.exp(-2.5 * v)) / 2.5, cur = Math.sin(v * 5 + i) * 70 * h(i * 1.9);
        const sx = px + Math.cos(ang) * rr + cur, sy = py + Math.sin(ang) * rr;
        const s = eio((v - .45) / .85);
        const tx = 540 + (h(i * 4.1) - .5) * 40, ty = 760 + (h(i * 6.1) - .5) * 40;
        const X = lerp(sx, tx, s), Y = lerp(sy, ty, s), al = s > .7 ? 1 - (s - .7) / .3 : 1;
        if (al <= 0) continue;
        fxc.fillStyle = `rgba(${lerp(243, GOLD[0], s) | 0},${lerp(235, GOLD[1], s) | 0},${lerp(216, GOLD[2], s) | 0},${al * (.55 + .45 * h(i * 8.8))})`;
        const z = 2.4 * (1 - .5 * s); fxc.fillRect(X, Y, z, z);
      }
    }
    anim(c1, t, { y: 900, t0: LT, t1: 6.0, inK: 'rise', inD: .9, lsFrom: .04, glow: 24, drift: .015 });
    ayahAnim(A, t, { arT0: 6.0, arD: 1.3, mlT0: 6.9, out: 12.3 });
    endCard(hal, t, 12.6); shineAnim(hal, t, 12.6);
    anim(sub, t, { y: 1060, t0: 13.1, inK: 'rise', inD: .8, lsFrom: .06, drift: .008 });
    const hits = pulse(t, .02, 8) + pulse(t, 1.0, 8) + pulse(t, 2.05, 8);
    const ramp = eio((u - .7) / 1.1);
    const sw = t >= 6.0 && t < 7.5 ? lerp(1.12, -.12, eio((t - 6) / 1.3)) : null;
    const bg = t < SH ? { lx: .5, ly: .5, I: .22 + .3 * hits, G: 0, RAY: .5, Z: 1 + .03 * t, F: hits * .06 }
      : t < LT + .2 ? { lx: .5, ly: .6, I: .2 + 1.4 * ramp, G: lerp(0, 1, ramp), RAY: .6 + .8 * ramp, Z: 1.05 + .05 * ramp }
      : t < 12.6 ? { lx: sw ?? .5, ly: sw !== null ? .5 : .62, I: .75 - .25 * eo((t - 6.5) / 2) + .6 * pulse(t, LT, 1.6) , G: 1, RAY: 1, F: pulse(t, LT, 2.6) * .8, Z: 1.06 }
      : { lx: .5, ly: .52, I: 1 + pulse(t, 12.6, 2.5), G: 1, RAY: 1.3, F: pulse(t, 12.6, 3.5) * .9, Z: 1.05 };
    drawBg(t, bg);
    const k = 1 + .04 * t / DUR, sx = shake(t, .02, 26) + shake(t, 1.0, 28) + shake(t, 2.05, 36);
    cam.style.transform = `translate(${sx}px,${sx * -.6}px) scale(${k})`;
    drawDust(t, { a: t < SH ? .7 : 1, sp: t < SH ? 2 : 1, lx: bg.lx, ly: bg.ly, Z: bg.Z });
  };
  return { dur: DUR, cues, frame };
};

// ---------- 3: lansman ----------
SCENES['03-lansman'] = V => {
  const t1 = [['Bugün', 780], ['nasılsın?', 970]].map(([s, y]) => ({ d: mk('hk', s), y }));
  t1.forEach(x => x.d.style.fontSize = '190px'); fit(t1[1].d, 900);
  const ta = mk('hk', 'Hâlin ne\nolursa olsun,'), tb = mk('hk gd', 'bir ayet var.');
  ta.style.fontSize = '120px'; tb.style.fontSize = '130px'; fit(ta, 900); fit(tb, 900);
  const hal = mk('hk gd shine', 'HÂL'), s1 = mk('hk it', "Yakında App Store'da"), s2 = mk('hk gd', 'Reklamsız · Veri toplamaz');
  hal.style.fontSize = '250px'; s1.style.fontSize = '68px'; s1.style.fontWeight = '400'; s2.style.fontSize = '52px'; s2.style.fontWeight = '500'; fit(s2, 900);

  const pg = document.createElement('div'); pg.id = 'pg'; cam.appendChild(pg);
  const ph = document.createElement('div'); ph.className = 'phone'; cam.appendChild(ph);
  const layers = [];
  for (let k = 14; k >= 1; k--) { const l = document.createElement('div'); l.className = 'pl'; l.style.transform = `translateZ(${-k}px)`; ph.appendChild(l); layers.push(l); }
  const fr = document.createElement('div'); fr.className = 'pl front'; fr.style.transform = 'translateZ(7px)'; ph.appendChild(fr);
  const rim = document.createElement('div'); rim.className = 'rim'; fr.appendChild(rim);
  const scr = document.createElement('div'); scr.className = 'scr'; fr.appendChild(scr);
  const im1 = new Image(), im2 = new Image(); im1.src = V.screens.a; im2.src = V.screens.b; scr.append(im1, im2);
  const mkd = (st) => { const d = document.createElement('div'); d.style.cssText = st; scr.appendChild(d); return d; };
  const btn = mkd('left:247px;top:349px;width:205px;height:65px;border-radius:16px;background:rgb(216,184,120)');
  const ring = mkd('left:0;top:0;width:10px;height:10px;border-radius:50%;border:3px solid rgb(240,214,160)');
  const seam = mkd('left:0;top:0;height:5px;background:linear-gradient(90deg,transparent,#FFF1CF,transparent);box-shadow:0 0 60px 30px rgba(216,184,120,.55)');
  const refl = mkd('background:linear-gradient(115deg,transparent 40%,rgba(255,255,255,.09) 48%,transparent 56%);background-size:300% 100%');
  const isl = mkd(''); isl.className = 'isl';
  const DUR = 12.8, TAP = 3.75, SW = 4.4;
  const cues = [['bed'], ['hit', .02, 1.4], ['whoosh', 1.3, 1.4, -1, .7], ['hit', 1.9, .9], ['tick', TAP, .8], ['hit', TAP + .02, .4], ['whoosh', SW, .8, -1, 1],
    ['shimmer', SW, 1.4, .6], ['whoosh', 5.2, 2.6, 1, .5], ['whoosh', 7.4, .7, 1, .6], ['hit', 7.9, .8], ['hit', 8.5, 1.0],
    ['riser', 9.7, .5, .8], ['hit', 10.2, 1.8], ['shimmer', 10.2, 1.4, .6]];
  const frame = t => {
    fxc.clearRect(0, 0, W, H);
    t1.forEach((x, i) => anim(x.d, t, { y: x.y, t0: -.3 + .1 * i, t1: 1.8, inD: .6, lsFrom: .1, glow: 0 }));
    const pin = eo((t - 1.3) / 1.7), ex = clamp((t - 7.4) / .7), exq = eo(ex);
    const o = (t < 1.3 || ex >= 1) ? 0 : 1 - clamp(ex * 1.5);
    ph.style.display = pg.style.display = o > 0 ? 'block' : 'none';
    const orb = eio((t - 4.8) / 2.6);
    const rotY = -38 + 24 * eio((t - 1.3) / 3.6) + 54 * orb;
    const rotX = lerp(40, 7, pin) + Math.sin(t * .9) * 2 - 4 * orb;
    const rotZ = lerp(-7, 0, pin) + Math.sin(t * .7) * .8;
    const yy = lerp(1300, 0, pin) + Math.sin(t * 1.2) * 12 - exq * 120;
    const zz = lerp(-700, 0, pin) - exq * 500;
    const sc = lerp(.9, 1.07, pin) * (1 + .07 * clamp((t - 2) / 5));
    ph.style.opacity = o; ph.style.filter = ex > 0 ? `blur(${exq * 24}px)` : 'none';
    ph.style.transform = `translate3d(${(t - 4) * 5}px,${yy}px,${zz}px) rotateX(${rotX}deg) rotateY(${rotY}deg) rotateZ(${rotZ}deg) scale(${sc})`;
    const sweep = ((t - 1.6) * .22) % 1 * 140 - 20;
    layers.forEach((l, i) => {
      const a = sweep + i * 2;
      l.style.background = `linear-gradient(180deg,#141a18 0%,#141a18 ${a - 14}%,rgba(255,232,180,.7) ${a}%,#141a18 ${a + 14}%,#141a18 100%)`;
    });
    rim.style.background = `conic-gradient(from ${(t - 1.3) * 70}deg,rgba(216,184,120,.08) 0%,rgba(216,184,120,.08) 66%,rgba(255,235,190,.95) 80%,rgba(216,184,120,.08) 94%)`;
    refl.style.backgroundPosition = `${lerp(110, -10, clamp((rotY + 40) / 85))}% 0`;
    const tp = clamp((t - TAP) / .7);
    btn.style.opacity = tp > 0 && tp < 1 ? .38 * Math.sin(Math.PI * Math.pow(tp, .6)) : 0;
    ring.style.opacity = tp > 0 && tp < 1 ? 1 - tp : 0;
    const rr = 20 + 170 * eo(tp * 1.4); ring.style.width = ring.style.height = rr * 2 + 'px';
    ring.style.left = 350 - rr - 3 + 'px'; ring.style.top = 381 - rr - 3 + 'px';
    const sp = eio((t - SW) / .8);
    im2.style.webkitMaskImage = sp >= 1 ? 'none' : `linear-gradient(to top,#000 ${sp * 100}%,transparent ${sp * 100 + 6}%)`;
    im2.style.display = sp > 0 ? 'block' : 'none';
    seam.style.display = sp > 0 && sp < 1 ? 'block' : 'none'; seam.style.width = '480px'; seam.style.top = (1 - sp) * 1039 + 'px';
    anim(ta, t, { y: 800, t0: 7.9, t1: 10.0, inD: .6 });
    anim(tb, t, { y: 1010, t0: 8.5, t1: 10.0, inD: .6, glow: 30 });
    endCard(hal, t, 10.2); shineAnim(hal, t, 10.2);
    anim(s1, t, { y: 1050, t0: 10.7, inK: 'rise', inD: .7, lsFrom: .05, drift: .008 });
    anim(s2, t, { y: 1170, t0: 11.1, inK: 'rise', inD: .7, lsFrom: .05, drift: .008 });
    const glowI = .2 * pin * o;
    pg.style.background = `radial-gradient(circle,rgba(100,190,150,${glowI + .3 * pulse(t, SW, 2) * o}),transparent 70%)`;
    const bg = t < 1.8 ? { lx: .5, ly: .6, I: .6 + .5 * pulse(t, .02, 4), G: .4, RAY: .9, Z: 1 + .03 * t, F: pulse(t, .02, 6) * .15 }
      : t < 7.9 ? { lx: lerp(.8, .25, clamp((t - 1.8) / 6)), ly: .55, I: .5 + .9 * pulse(t, SW, 2.2) + .4 * pulse(t, TAP, 5), G: .6 + .4 * clamp((t - SW) / 2), RAY: .9, F: pulse(t, SW, 4) * .5, Z: 1.03 }
      : t < 10.2 ? { lx: .5, ly: .55, I: .5 + .4 * pulse(t, 7.9, 3) + .3 * pulse(t, 8.5, 3), G: .9, RAY: 1, Z: 1.04 }
      : { lx: .5, ly: .52, I: 1 + pulse(t, 10.2, 2.5), G: 1, RAY: 1.3, F: pulse(t, 10.2, 3.5) * .9, Z: 1.04 };
    drawBg(t, bg);
    cam.style.transform = `translate(${shake(t, .02, 16)}px,${shake(t, .02, 12) + shake(t, 7.9, 8) + shake(t, 10.2, 14)}px) scale(${1 + .03 * t / DUR})`;
    drawDust(t, { a: 1, sp: 1.2, lx: bg.lx, ly: bg.ly, Z: bg.Z });
  };
  return { dur: DUR, cues, frame };
};

// ---------- giris ----------
(function () {
  const g = document.getElementById('grain'), c = document.createElement('canvas'); c.width = c.height = 256;
  const x = c.getContext('2d'), im = x.createImageData(256, 256);
  for (let i = 0; i < 65536; i++) { const v = h(i * .37) * 255; im.data.set([v, v, v, 255], i * 4); }
  x.putImageData(im, 0, 0); g.style.backgroundImage = `url(${c.toDataURL()})`;
  window.grain = f => { g.style.backgroundPosition = `${(h(f * 1.1) * 256) | 0}px ${(h(f * 2.3) * 256) | 0}px`; };
})();

let SC = null;
window.init = async name => {
  await Promise.all(['700 100px HalSerif', '800 100px HalSerif', 'italic 400 100px HalSerif', 'italic 500 100px HalSerif', '100px HalAmiri'].map(f => document.fonts.load(f, 'AaİÂم')));
  await document.fonts.ready;
  cam.replaceChildren();
  SC = SCENES[name](VERI);
  if (VERI.screens) await Promise.all([...document.images].map(i => i.decode()));
  return { dur: SC.dur, cues: SC.cues };
};
window.seek = t => { SC.frame(t); window.grain(Math.round(t * FPS)); };
