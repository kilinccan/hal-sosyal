const SR = 48000;

// Sahnenin ipuclarindan (vurus, süpürme, hava) müziksiz stereo ses sentezler; 16-bit WAV döner.
export function synth(cues, dur) {
  const n = Math.ceil(dur * SR) + SR;
  const L = new Float32Array(n), R = new Float32Array(n);
  let seed = 7;
  const rnd = () => { seed = (seed * 1664525 + 1013904223) >>> 0; return seed / 2147483648 - 1; };
  const add = (i, l, r) => { if (i >= 0 && i < n) { L[i] += l; R[i] += r; } };

  const hit = (t, g) => {
    const s0 = Math.floor(t * SR); let ph = 0, lp = 0, lp2 = 0;
    for (let i = 0; i < 1.8 * SR; i++) {
      const u = i / SR, f = 34 + 70 * Math.exp(-u * 9);
      ph += 2 * Math.PI * f / SR;
      const body = (Math.sin(ph) + .25 * Math.sin(2 * ph)) * Math.exp(-u * 2.4) * (1 - Math.exp(-u * 500));
      const nz = rnd(); lp += .06 * (nz - lp); lp2 += .35 * (nz - lp2);
      const thump = lp * 5 * Math.exp(-u * 26), snap = lp2 * Math.exp(-u * 55) * .5;
      const rumble = lp * 2.2 * Math.exp(-u * 3) * .35;
      const v = g * .55 * (body + thump + snap + rumble);
      add(s0 + i, v, v);
    }
  };
  const svf = () => { let low = 0, band = 0; return (x, fc, q) => { const f = 2 * Math.sin(Math.PI * fc / SR); low += f * band; const high = x - low - q * band; band += f * high; return band; }; };
  const whoosh = (t, d, dir, g) => {
    const s0 = Math.floor(t * SR), flt = svf();
    for (let i = 0; i < d * SR; i++) {
      const x = i / (d * SR), env = Math.pow(Math.sin(Math.PI * x), 2);
      const k = dir > 0 ? x * x : 1 - x * x, fc = 250 + 4200 * k;
      const v = flt(rnd(), fc, 1.1) * env * g * .5, pan = dir * (1 - 2 * x) * -.6;
      add(s0 + i, v * (1 - pan) / 2 * 1.4, v * (1 + pan) / 2 * 1.4);
    }
  };
  const riser = (t, d, g) => {
    const s0 = Math.floor(t * SR), flt = svf(); let ph = 0;
    for (let i = 0; i < d * SR; i++) {
      const x = i / (d * SR), env = Math.pow(x, 2.5);
      ph += 2 * Math.PI * (40 + 55 * x) / SR;
      const v = (flt(rnd(), 400 + 5000 * x * x, 1.4) * .5 + Math.sin(ph) * .5) * env * g * .5;
      add(s0 + i, v, v);
    }
  };
  const tick = (t, g) => {
    const s0 = Math.floor(t * SR); let prev = 0;
    for (let i = 0; i < .12 * SR; i++) { const x = rnd(), v = (x - prev) * Math.exp(-i / SR * 70) * g * .3; prev = x; add(s0 + i, v, v); }
  };
  const shimmer = (t, d, g) => {
    const s0 = Math.floor(t * SR); let p1 = 0, p2 = 0, q1 = 0, q2 = 0;
    for (let i = 0; i < d * SR; i++) {
      const x = i / (d * SR), env = Math.pow(Math.sin(Math.PI * Math.pow(x, .6)), 2);
      const a = rnd(), b = rnd(); const ha = a - p1, hb = b - q1; p1 = a; q1 = b;
      const va = ha - p2, vb = hb - q2; p2 = ha; q2 = hb;
      add(s0 + i, va * env * g * .12, vb * env * g * .12);
    }
  };
  const bed = () => {
    const fl = svf(), fr = svf();
    for (let i = 0; i < n; i++) {
      const u = i / SR, fc = 180 + 120 * Math.sin(u * .5) + 60 * Math.sin(u * 1.3);
      add(i, fl(rnd(), fc, 1.6) * .1, fr(rnd(), fc * 1.07, 1.6) * .1);
    }
  };

  for (const [k, ...a] of cues) ({ hit, whoosh, riser, tick, shimmer, bed })[k](...a);

  const out = Buffer.alloc(n * 4);
  let peak = 0; for (let i = 0; i < n; i++) peak = Math.max(peak, Math.abs(L[i]), Math.abs(R[i]));
  const nrm = peak > 0 ? .9 / peak : 1;
  for (let i = 0; i < n; i++) {
    out.writeInt16LE(Math.round(L[i] * nrm * 32767), i * 4);
    out.writeInt16LE(Math.round(R[i] * nrm * 32767), i * 4 + 2);
  }
  const hd = Buffer.alloc(44);
  hd.write('RIFF', 0); hd.writeUInt32LE(36 + out.length, 4); hd.write('WAVEfmt ', 8); hd.writeUInt32LE(16, 16);
  hd.writeUInt16LE(1, 20); hd.writeUInt16LE(2, 22); hd.writeUInt32LE(SR, 24); hd.writeUInt32LE(SR * 4, 28);
  hd.writeUInt16LE(4, 32); hd.writeUInt16LE(16, 34); hd.write('data', 36); hd.writeUInt32LE(out.length, 40);
  return Buffer.concat([hd, out]);
}
