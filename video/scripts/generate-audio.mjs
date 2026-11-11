// Genera la música (electrónica suave, 120 BPM, La menor) y los efectos de sonido
// como WAV propios: sin derechos de autor y sin dependencias.
// Uso: npm run audio  →  public/audio/{music,whoosh,hit,tick,pop,riser}.wav
import { mkdirSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const SR = 44100;
const DUR = 60; // segundos
const BPM = 120;
const BEAT = 60 / BPM;
const out = join(dirname(fileURLToPath(import.meta.url)), "..", "public", "audio");
mkdirSync(out, { recursive: true });

// ---------- utilidades ----------
let seed = 1234567;
const rnd = () => {
  seed = (seed * 1664525 + 1013904223) >>> 0;
  return seed / 4294967296 - 0.5;
};
const mtof = (m) => 440 * 2 ** ((m - 69) / 12);
const buf = (sec) => [new Float32Array(Math.ceil(sec * SR)), new Float32Array(Math.ceil(sec * SR))];
const saw = (ph) => 2 * (ph - Math.floor(ph + 0.5));

function add(track, t0, mono, gain = 1, pan = 0) {
  const start = Math.floor(t0 * SR);
  const l = gain * Math.min(1, 1 - pan);
  const r = gain * Math.min(1, 1 + pan);
  for (let i = 0; i < mono.length; i++) {
    const k = start + i;
    if (k < 0 || k >= track[0].length) continue;
    track[0][k] += mono[i] * l;
    track[1][k] += mono[i] * r;
  }
}

// paso bajo de un polo; cutoff puede ser función del tiempo
function lowpass(x, cutoff) {
  const y = new Float32Array(x.length);
  let s = 0;
  for (let i = 0; i < x.length; i++) {
    const fc = typeof cutoff === "function" ? cutoff(i / SR) : cutoff;
    const a = 1 - Math.exp((-2 * Math.PI * fc) / SR);
    s += a * (x[i] - s);
    y[i] = s;
  }
  return y;
}
function highpass(x, fc) {
  const lp = lowpass(x, fc);
  return x.map((v, i) => v - lp[i]);
}

const env = (t, a, d, s, r, len) => {
  if (t < a) return t / a;
  if (t < a + d) return 1 - (1 - s) * ((t - a) / d);
  if (t < len) return s;
  return Math.max(0, s * (1 - (t - len) / r));
};

// ---------- instrumentos ----------
function kick() {
  const n = Math.floor(0.45 * SR);
  const x = new Float32Array(n);
  let ph = 0;
  for (let i = 0; i < n; i++) {
    const t = i / SR;
    const f = 45 + 110 * Math.exp(-t * 28);
    ph += (2 * Math.PI * f) / SR;
    x[i] = Math.sin(ph) * Math.exp(-t * 7) * (t < 0.002 ? t / 0.002 : 1);
  }
  return x;
}
function hat(open = false) {
  const len = open ? 0.25 : 0.06;
  const n = Math.floor(len * SR);
  const x = new Float32Array(n);
  for (let i = 0; i < n; i++) x[i] = rnd() * Math.exp((-i / SR) * (open ? 14 : 70));
  return highpass(x, 7000);
}
function clap() {
  const n = Math.floor(0.22 * SR);
  const x = new Float32Array(n);
  for (let i = 0; i < n; i++) {
    const t = i / SR;
    const burst = [0, 0.012, 0.024].reduce((s, o) => s + (t >= o ? Math.exp(-(t - o) * 90) : 0), 0);
    x[i] = rnd() * (burst * 0.5 + Math.exp(-t * 20) * 0.4);
  }
  return lowpass(highpass(x, 900), 6500);
}
function pluck(freq, len = 0.28, bright = 3500) {
  const n = Math.floor(len * SR);
  const x = new Float32Array(n);
  for (let i = 0; i < n; i++) {
    const t = i / SR;
    const ph = t * freq;
    x[i] = (saw(ph) * 0.6 + saw(ph * 1.005) * 0.4) * Math.exp(-t * 11);
  }
  return lowpass(x, (t) => 400 + bright * Math.exp(-t * 14));
}
function pad(freqs, len) {
  const n = Math.floor((len + 1.2) * SR);
  const x = new Float32Array(n);
  for (const f of freqs) {
    for (const det of [-0.004, 0.004]) {
      const fr = f * (1 + det);
      for (let i = 0; i < n; i++) {
        const t = i / SR;
        x[i] += saw(t * fr) * env(t, 0.9, 0.3, 0.8, 1.2, len) * 0.07;
      }
    }
  }
  return lowpass(x, 1400);
}
function bass(freq, len) {
  const n = Math.floor((len + 0.1) * SR);
  const x = new Float32Array(n);
  for (let i = 0; i < n; i++) {
    const t = i / SR;
    const v = Math.sin(2 * Math.PI * freq * t) + 0.35 * saw(t * freq);
    x[i] = v * env(t, 0.01, 0.1, 0.8, 0.08, len) * 0.55;
  }
  return lowpass(x, 420);
}
function lead(freq, len) {
  const n = Math.floor((len + 0.4) * SR);
  const x = new Float32Array(n);
  for (let i = 0; i < n; i++) {
    const t = i / SR;
    const vib = 1 + 0.003 * Math.sin(2 * Math.PI * 5.5 * t);
    x[i] = (Math.sin(2 * Math.PI * freq * vib * t) * 0.7 + saw(t * freq * vib) * 0.15) * env(t, 0.03, 0.2, 0.6, 0.4, len) * 0.35;
  }
  return lowpass(x, 3000);
}
function noiseSweep(len, f0, f1, shape) {
  const n = Math.floor(len * SR);
  const x = new Float32Array(n);
  for (let i = 0; i < n; i++) x[i] = rnd();
  const y = lowpass(x, (t) => f0 + (f1 - f0) * Math.pow(t / len, shape));
  return y.map((v, i) => v * Math.sin(Math.PI * Math.min(1, i / n)) ** 1.5);
}
function riser(len) {
  const n = Math.floor(len * SR);
  const x = new Float32Array(n);
  let ph = 0;
  for (let i = 0; i < n; i++) {
    const p = i / n;
    ph += (2 * Math.PI * (200 + 1800 * p * p)) / SR;
    x[i] = (Math.sin(ph) * 0.25 + rnd() * 0.5 * p) * p ** 1.6;
  }
  return highpass(x, 300);
}
function impact() {
  const n = Math.floor(2.4 * SR);
  const x = new Float32Array(n);
  let ph = 0;
  for (let i = 0; i < n; i++) {
    const t = i / SR;
    ph += (2 * Math.PI * (38 + 90 * Math.exp(-t * 9))) / SR;
    x[i] = Math.sin(ph) * Math.exp(-t * 2.2) + rnd() * 0.4 * Math.exp(-t * 14);
  }
  return lowpass(x, 900);
}
function tickSound() {
  const n = Math.floor(0.09 * SR);
  const x = new Float32Array(n);
  for (let i = 0; i < n; i++) {
    const t = i / SR;
    x[i] = Math.sin(2 * Math.PI * 1800 * t) * Math.exp(-t * 60) * 0.6;
  }
  return x;
}
function popSound() {
  const n = Math.floor(0.22 * SR);
  const x = new Float32Array(n);
  let ph = 0;
  for (let i = 0; i < n; i++) {
    const t = i / SR;
    ph += (2 * Math.PI * (500 + 700 * Math.exp(-t * 25))) / SR;
    x[i] = Math.sin(ph) * Math.exp(-t * 18) * 0.6;
  }
  return x;
}

// ---------- música ----------
const m = buf(DUR);
const t_ = (bar, beat = 0) => (bar * 4 + beat) * BEAT; // compás de 4 tiempos
const BARS = DUR / (4 * BEAT);
// Am – F – C – G
const chords = [
  { root: 45, notes: [57, 60, 64] },
  { root: 41, notes: [53, 57, 60] },
  { root: 48, notes: [55, 60, 64] },
  { root: 43, notes: [55, 59, 62] },
];
const arpPattern = [0, 1, 2, 1, 2, 1, 0, 2];
const K = kick(), H = hat(), HO = hat(true), C = clap();

// escenas en segundos: intro 0-5, presentación 5-12, funciones 12-38, resultado 38-50, outro 50-60
for (let bar = 0; bar < BARS; bar++) {
  const s = t_(bar);
  const ch = chords[bar % 4];
  const inIntro = s < 5, inPres = s >= 5 && s < 12, inMain = s >= 12 && s < 50, inOutro = s >= 50;
  // colchón
  add(m, s, pad(ch.notes.map(mtof), 4 * BEAT), inOutro ? 0.9 : 1);
  if (s >= 3) add(m, s, bass(mtof(ch.root), 4 * BEAT * 0.97), s < 5 ? 0.5 : 0.9);
  // batería
  if (s >= 5 && s < 49.5) {
    for (let b = 0; b < 4; b++) {
      add(m, t_(bar, b), K, 0.95);
      add(m, t_(bar, b + 0.5), H, 0.35);
      if (inMain) add(m, t_(bar, b + 0.75), H, 0.18);
      if (b === 1 || b === 3) if (s >= 12) add(m, t_(bar, b), C, 0.4);
    }
    if (inMain) add(m, t_(bar, 3.5), HO, 0.3);
  }
  if (s >= 3 && s < 5) for (let b = 0; b < 4; b++) add(m, t_(bar, b + 0.5), H, 0.2);
  // arpegio
  if (s >= 5 && s < 50) {
    const up = inMain ? 12 : 0;
    for (let i = 0; i < 8; i++) {
      const note = ch.notes[arpPattern[i] % 3] + 12 + (i === 7 ? 12 : 0) + (s >= 38 && s < 50 ? up : 0);
      add(m, t_(bar, i * 0.5), pluck(mtof(note)), inPres ? 0.28 : 0.4, i % 2 ? 0.35 : -0.35);
    }
  }
  // melodía en el resultado (38-50 s)
  if (s >= 38 && s < 50) {
    const mel = [ch.notes[2] + 12, ch.notes[1] + 12, ch.notes[2] + 12, ch.notes[0] + 24];
    mel.forEach((nt, i) => add(m, t_(bar, i), lead(mtof(nt), BEAT * 0.9), 0.5));
  }
}
// intro: pulso lejano y riser hacia la presentación
add(m, 2.2, riser(2.8), 0.7);
add(m, 5, impact(), 0.7);
// resultado: riser hacia el cierre
add(m, 47.5, riser(2.5), 0.6);
// outro: impacto y acorde final largo
add(m, 50, impact(), 0.9);
add(m, 50, pad([57, 60, 64, 69].map(mtof), 7), 1.4);
add(m, 50, bass(mtof(45), 4), 0.9);
for (let i = 0; i < 6; i++) add(m, 50.5 + i * 0.5, pluck(mtof([69, 72, 76, 72, 69, 64][i]), 0.9, 2500), 0.35, i % 2 ? 0.4 : -0.4);

// fundidos y normalización
const fadeIn = 1.2, fadeOut = 3.5;
let peak = 0;
for (const ch of m) for (let i = 0; i < ch.length; i++) peak = Math.max(peak, Math.abs(ch[i]));
for (const ch of m) {
  for (let i = 0; i < ch.length; i++) {
    const t = i / SR;
    const g = Math.min(1, t / fadeIn) * Math.min(1, (DUR - t) / fadeOut);
    ch[i] = Math.tanh((ch[i] / peak) * 1.1) * g * 0.85;
  }
}

// ---------- WAV ----------
function writeWav(name, [l, r]) {
  const n = l.length;
  const b = Buffer.alloc(44 + n * 4);
  b.write("RIFF", 0); b.writeUInt32LE(36 + n * 4, 4); b.write("WAVE", 8); b.write("fmt ", 12);
  b.writeUInt32LE(16, 16); b.writeUInt16LE(1, 20); b.writeUInt16LE(2, 22);
  b.writeUInt32LE(SR, 24); b.writeUInt32LE(SR * 4, 28); b.writeUInt16LE(4, 32); b.writeUInt16LE(16, 34);
  b.write("data", 36); b.writeUInt32LE(n * 4, 40);
  for (let i = 0; i < n; i++) {
    b.writeInt16LE(Math.max(-32768, Math.min(32767, Math.round(l[i] * 32767))), 44 + i * 4);
    b.writeInt16LE(Math.max(-32768, Math.min(32767, Math.round(r[i] * 32767))), 46 + i * 4);
  }
  writeFileSync(join(out, name), b);
  console.log("✔", name, (b.length / 1e6).toFixed(1), "MB");
}
function sfx(name, mono, gain = 0.8) {
  const t = buf(mono.length / SR + 0.05);
  add(t, 0, mono, 1);
  let pk = 0;
  for (const v of t[0]) pk = Math.max(pk, Math.abs(v));
  for (const ch of t) for (let i = 0; i < ch.length; i++) ch[i] = (ch[i] / (pk || 1)) * gain;
  writeWav(name, t);
}

writeWav("music.wav", m);
sfx("whoosh.wav", noiseSweep(0.9, 300, 6000, 2), 0.7);
sfx("hit.wav", impact(), 0.9);
sfx("tick.wav", tickSound(), 0.6);
sfx("pop.wav", popSound(), 0.7);
sfx("riser.wav", riser(2), 0.6);
