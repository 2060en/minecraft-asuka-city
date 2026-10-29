import * as THREE from 'three';
import { Sky } from 'three/addons/objects/Sky.js';
import { MARK } from './mark.js';

const P = new URLSearchParams(location.search);
const VIEW = P.get('view') || 'side';
const W = +P.get('w') || 2400, H = +P.get('h') || 1000;

// ---------------------------------------------------------------------------
// Boeing 787-8, metres. x: aft from the nose, y: up from the ground, z: toward the aircraft's left side
// ---------------------------------------------------------------------------
const L = 56.72, YT = 8.87, YB = 2.90, W0 = 2.885, YTIP = 5.25;
const clamp = (v, a, b) => Math.min(Math.max(v, a), b);
const lerp = (a, b, t) => a + (b - a) * t;
const sup = (t, p) => { t = clamp(t, 0, 1); return Math.pow(1 - Math.pow(1 - t, p), 1 / p); };

function prof(x) {
  let yt = YT, yb = YB, w = W0;
  if (x < 12.0) yt = YTIP + (YT - YTIP) * sup(x / 12.0, 2.05);
  if (x < 7.0) yb = YTIP - (YTIP - YB) * sup(x / 7.0, 2.5);
  if (x < 9.0) w = W0 * sup(x / 9.0, 2.3);
  if (x > 34) { const t = (x - 34) / (L - 34); yb = YB + (7.55 - YB) * Math.pow(t, 1.7); }
  if (x > 44) { const t = (x - 44) / (L - 44); yt = YT - (YT - 8.25) * t * t; }
  if (x > 36) { const t = (x - 36) / (L - 36); w = Math.min(w, W0 - (W0 - 0.35) * Math.pow(t, 1.6)); }
  let dip = 0;
  if (x > 16 && x < 36) { const t = (x - 16) / 20; dip = 0.32 * Math.pow(Math.sin(Math.PI * t), 2); }
  return { yt, yb, w, dip };
}

function fuselageGeometry(NX = 460, NT = 200) {
  const pos = [], idx = [];
  for (let i = 0; i <= NX; i++) {
    const x = L * (1 - Math.cos(Math.PI * i / NX)) / 2;
    const { yt, yb, w, dip } = prof(x);
    const yc = (yt + yb) / 2;
    for (let j = 0; j <= NT; j++) {
      const th = 2 * Math.PI * j / NT - Math.PI / 2;
      const s = Math.sin(th), c = Math.cos(th);
      const y = s >= 0 ? yc + (yt - yc) * s : yc + (yc - (yb - dip)) * s;
      const z = w * c * (1 + 0.18 * dip * Math.max(0, -s));
      pos.push(x, y, z);
    }
  }
  for (let i = 0; i < NX; i++) for (let j = 0; j < NT; j++) {
    const a = i * (NT + 1) + j, b = a + NT + 1;
    idx.push(a, b, a + 1, b, b + 1, a + 1);
  }
  const g = new THREE.BufferGeometry();
  g.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3));
  g.setIndex(idx);
  g.computeVertexNormals();
  const n = g.attributes.normal;
  for (let i = 0; i <= NX; i++) {          // weld the seam along the belly
    const a = i * (NT + 1), b = a + NT;
    const v = new THREE.Vector3(n.getX(a) + n.getX(b), n.getY(a) + n.getY(b), n.getZ(a) + n.getZ(b)).normalize();
    n.setXYZ(a, v.x, v.y, v.z); n.setXYZ(b, v.x, v.y, v.z);
  }
  for (let j = 0; j <= NT; j++) n.setXYZ(j, -1, 0, 0);
  return g;
}

// NACA 4-digit thickness (unit thickness ratio) on a closed loop TE -> upper -> LE -> lower -> TE
const yt5 = x => 5 * (0.2969 * Math.sqrt(x) - 0.1260 * x - 0.3516 * x * x + 0.2843 * x ** 3 - 0.1036 * x ** 4);
function airfoilLoop(n = 40) {
  const xs = []; for (let k = 0; k <= n; k++) xs.push((1 - Math.cos(Math.PI * k / n)) / 2);
  const out = [];
  for (let k = n; k >= 0; k--) out.push([xs[k], 1]);
  for (let k = 1; k <= n; k++) out.push([xs[k], -1]);
  return out;
}

function loft(sections, flip, uvf) {
  const n = sections[0].length, pos = [], uv = [], idx = [];
  sections.forEach(sec => sec.forEach(p => { pos.push(p[0], p[1], p[2]); if (uvf) uv.push(...uvf(p)); }));
  for (let s = 0; s < sections.length - 1; s++) for (let k = 0; k < n - 1; k++) {
    const a = s * n + k, b = a + n;
    if (flip) idx.push(a, a + 1, b, b, a + 1, b + 1); else idx.push(a, b, a + 1, b, b + 1, a + 1);
  }
  // cap the far end
  const last = sections[sections.length - 1], prev = sections[sections.length - 2];
  const cen = p => p.reduce((m, q) => [m[0] + q[0] / p.length, m[1] + q[1] / p.length, m[2] + q[2] / p.length], [0, 0, 0]);
  const c = cen(last), cp = cen(prev);
  const out = new THREE.Vector3(c[0] - cp[0], c[1] - cp[1], c[2] - cp[2]);
  const ci = pos.length / 3; pos.push(...c); if (uvf) uv.push(...uvf(c));
  const base = (sections.length - 1) * n;
  const A = new THREE.Vector3(...last[Math.floor(n / 4)]), B = new THREE.Vector3(...last[Math.floor(n / 4) + 1]), C = new THREE.Vector3(...c);
  const nrm = new THREE.Vector3().crossVectors(A.clone().sub(C), B.clone().sub(C));
  const swap = nrm.dot(out) < 0;
  for (let k = 0; k < n - 1; k++) swap ? idx.push(ci, base + k + 1, base + k) : idx.push(ci, base + k, base + k + 1);
  const g = new THREE.BufferGeometry();
  g.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3));
  if (uvf) g.setAttribute('uv', new THREE.Float32BufferAttribute(uv, 2));
  g.setIndex(idx); g.computeVertexNormals();
  return g;
}

// vertical fin with dorsal fillet
function finGeometry() {
  const loop = airfoilLoop(48), secs = [];
  for (let y = 8.0; y <= 16.921; y += 0.12) {
    const yy = Math.min(y, 16.92);
    const le = 44.9 + (yy - 9.4) * 1.024 - 5.0 * Math.exp(-(yy - 8.0) / 0.8);
    const te = 55.2 + (yy - 8.0) / 8.92 * 0.75;
    const T = lerp(1.0, 0.32, (yy - 8.0) / 8.92);
    secs.push(loop.map(([xa, s]) => [le + (te - le) * xa, yy, s * T * yt5(xa)]));
  }
  return loft(secs, false);
}
const finLE = y => 44.9 + (y - 9.4) * 1.024 - 5.0 * Math.exp(-(y - 8.0) / 0.8);
const finTE = y => 55.2 + (y - 8.0) / 8.92 * 0.75;

function stabGeometry() {
  const loop = airfoilLoop(36), secs = [];
  for (let z = 0.3; z <= 9.751; z += 0.35) {
    const zz = Math.min(z, 9.75), t = (zz - 0.3) / 9.45;
    const le = 47.6 + (zz - 0.3) * 0.66, te = 53.6 + (zz - 0.3) * 0.17, ym = 7.35 + (zz - 0.3) * 0.1228;
    const T = lerp(0.62, 0.17, t);
    secs.push(loop.map(([xa, s]) => [le + (te - le) * xa, ym + s * T * yt5(xa), zz]));
  }
  return loft(secs, true);
}

// wing planform (z, LE, TE, y, t/c)
const WS = [[1.6, 20.8, 33.0, 3.62, 0.14], [2.9, 21.6, 32.6, 3.72, 0.135], [9.5, 26.3, 33.6, 4.42, 0.11], [28.0, 39.3, 41.6, 6.36, 0.09], [30.06, 41.9, 42.8, 6.62, 0.08]];
function wingAt(z) {
  for (let i = 0; i < WS.length - 1; i++) {
    const a = WS[i], b = WS[i + 1];
    if (z <= b[0] || i === WS.length - 2) {
      const t = clamp((z - a[0]) / (b[0] - a[0]), 0, 1);
      return { le: lerp(a[1], b[1], t), te: lerp(a[2], b[2], t), y: lerp(a[3], b[3], t), tc: lerp(a[4], b[4], t) };
    }
  }
}
const camber = x => { const m = 0.022, p = 0.42; return x < p ? m / (p * p) * (2 * p * x - x * x) : m / ((1 - p) ** 2) * ((1 - 2 * p) + 2 * p * x - x * x); };
function wingGeometry() {
  const loop = airfoilLoop(56), secs = [];
  const zs = []; for (let z = 1.6; z < 30.06; z += 0.4) zs.push(z); zs.push(30.06);
  for (const z of zs) {
    const { le, te, y, tc } = wingAt(z), c = te - le;
    secs.push(loop.map(([xa, s]) => [le + c * xa, y + c * (camber(xa) + s * tc * yt5(xa)), z]));
  }
  return loft(secs, true, p => [(p[0] - 18) / 28, p[2] / 31]);
}

// lathe around an axis parallel to x, with optional chevrons on the last ring
function latheX(profile, segs, cy, cz, chevron) {
  const pos = [], idx = [];
  profile.forEach(([x, r], k) => {
    for (let j = 0; j <= segs; j++) {
      const f = 2 * Math.PI * j / segs;
      const dx = chevron && k === profile.length - 1 ? chevron(f) : 0;
      pos.push(x + dx, cy + r * Math.cos(f), cz + r * Math.sin(f));
    }
  });
  for (let k = 0; k < profile.length - 1; k++) for (let j = 0; j < segs; j++) {
    const a = k * (segs + 1) + j, b = a + segs + 1;
    idx.push(a, a + 1, b, b, a + 1, b + 1);
  }
  const g = new THREE.BufferGeometry();
  g.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3));
  g.setIndex(idx); g.computeVertexNormals();
  return g;
}
const tri = t => 2 * Math.abs(t - Math.floor(t + 0.5));

// ---------------------------------------------------------------------------
// livery: two side-projection canvases (as seen from each side), sampled by world position
// ---------------------------------------------------------------------------
const K = 140, HM = 17.5, CW = Math.ceil(57.2 * K), CH = Math.ceil(HM * K), WM = CW / K;
const DOORS = [7.5, 18.3, 34.0, 47.3];
const WIN_Y = 6.43;

function blackPath() {
  const p = new Path2D();
  p.moveTo(31.2, 0.5); p.quadraticCurveTo(34.4, 6.6, 40.6, 9.8);
  p.lineTo(40.6, 18); p.lineTo(60, 18); p.lineTo(60, 0.5); p.closePath();
  return p;
}
function whitePath() {
  const p = new Path2D(); p.rect(-5, -5, 70, 30); p.addPath(blackPath()); return p;
}

function sCurve(x0, y0, i, R, th, d, extA, extB) {
  const pts = [], r1 = R - i * d, r2 = R + i * d;
  const O1 = [x0, y0 + R];
  const J = [O1[0] + R * Math.sin(th), O1[1] - R * Math.cos(th)];
  const O2 = [J[0] + R * Math.sin(th), J[1] - R * Math.cos(th)];
  pts.push([x0 - extA, y0 + i * d]);
  for (let k = 0; k <= 60; k++) { const f = th * k / 60; pts.push([O1[0] + r1 * Math.sin(f), O1[1] - r1 * Math.cos(f)]); }
  for (let k = 60; k >= 0; k--) { const f = th * k / 60; pts.push([O2[0] - r2 * Math.sin(f), O2[1] + r2 * Math.cos(f)]); }
  pts.push([O2[0] + extB, O2[1] + r2]);
  return pts;
}

function paintSide(side) {
  const cv = document.createElement('canvas'); cv.width = CW; cv.height = CH;
  const ctx = cv.getContext('2d');
  const world = () => side > 0 ? ctx.setTransform(K, 0, 0, -K, 0, HM * K) : ctx.setTransform(-K, 0, 0, -K, L * K, HM * K);
  ctx.fillStyle = '#f1f2f3'; ctx.fillRect(0, 0, CW, CH);
  world();
  const BLK = blackPath(), WHT = whitePath();
  ctx.fillStyle = '#0a0a0b'; ctx.fill(BLK);

  // draw a detail layer twice, once per paint colour, so trims read correctly on white and on black
  const layered = fn => {
    ctx.save(); ctx.clip(WHT, 'evenodd'); fn(false); ctx.restore();
    ctx.save(); ctx.clip(BLK); fn(true); ctx.restore();
  };

  // skin panel seams
  layered(dark => {
    ctx.strokeStyle = dark ? 'rgba(255,255,255,0.07)' : 'rgba(70,76,82,0.20)';
    ctx.lineWidth = 0.016;
    for (const x of [1.95, 6.1, 12.9, 20.4, 27.1, 33.0, 39.0, 45.4, 51.2]) {
      const p = prof(x); ctx.beginPath(); ctx.moveTo(x, p.yb - 0.5); ctx.lineTo(x, Math.min(p.yt + 0.05, 8.95)); ctx.stroke();
    }
    ctx.beginPath(); ctx.moveTo(8.2, 7.42); ctx.lineTo(46, 7.42); ctx.moveTo(8.2, 5.32); ctx.lineTo(46, 5.32); ctx.stroke();
  });

  const windowAt = (x, y, dark, s = 1) => {
    ctx.fillStyle = dark ? '#26282b' : '#c4c9ce';
    ctx.beginPath(); ctx.roundRect(x - 0.17 * s, y - 0.27 * s, 0.34 * s, 0.54 * s, 0.17 * s); ctx.fill();
    const g = ctx.createLinearGradient(0, y + 0.24 * s, 0, y - 0.24 * s);
    g.addColorStop(0, '#3e4b57'); g.addColorStop(0.45, '#1c242c'); g.addColorStop(1, '#0d1217');
    ctx.fillStyle = g;
    ctx.beginPath(); ctx.roundRect(x - 0.135 * s, y - 0.235 * s, 0.27 * s, 0.47 * s, 0.135 * s); ctx.fill();
    ctx.fillStyle = 'rgba(255,255,255,0.10)';
    ctx.beginPath(); ctx.roundRect(x - 0.10 * s, y + 0.02 * s, 0.07 * s, 0.17 * s, 0.035 * s); ctx.fill();
  };

  layered(dark => {
    for (let x = 9.45; x < 46.6; x += 0.548) {
      if (DOORS.some(d => Math.abs(x - d) < 0.95)) continue;
      windowAt(x, WIN_Y, dark);
    }
    for (const d of DOORS) {
      ctx.strokeStyle = dark ? 'rgba(170,170,170,0.35)' : 'rgba(95,102,110,0.75)';
      ctx.lineWidth = 0.028;
      ctx.beginPath(); ctx.roundRect(d - 0.535, 5.0, 1.07, 1.9, 0.2); ctx.stroke();
      windowAt(d, WIN_Y, dark, 0.8);
      ctx.fillStyle = dark ? 'rgba(160,160,160,0.35)' : 'rgba(110,116,122,0.6)';
      ctx.fillRect(d - 0.14, 5.62, 0.28, 0.07);
      ctx.strokeStyle = dark ? 'rgba(160,160,160,0.25)' : 'rgba(110,116,122,0.45)'; ctx.lineWidth = 0.015;
      ctx.strokeRect(d - 0.2, 5.48, 0.4, 0.35);
    }
  });

  // flight deck windows
  const cock = [
    [[1.98, 6.98], [3.02, 6.90], [3.18, 7.60], [2.40, 7.73]],
    [[3.22, 6.90], [4.62, 6.97], [4.30, 7.56], [3.40, 7.61]],
  ];
  for (const poly of cock) {
    ctx.beginPath(); poly.forEach(([x, y], k) => k ? ctx.lineTo(x, y) : ctx.moveTo(x, y)); ctx.closePath();
    const g = ctx.createLinearGradient(0, 6.9, 0, 7.7);
    g.addColorStop(0, '#36434f'); g.addColorStop(0.5, '#151c23'); g.addColorStop(1, '#0a0e12');
    ctx.fillStyle = g; ctx.fill();
    ctx.strokeStyle = '#3b3f44'; ctx.lineWidth = 0.05; ctx.lineJoin = 'round'; ctx.stroke();
  }
  ctx.strokeStyle = 'rgba(70,76,82,0.25)'; ctx.lineWidth = 0.016;   // radome seam
  ctx.beginPath(); ctx.moveTo(1.55, 4.1); ctx.quadraticCurveTo(1.25, 5.6, 1.7, 7.35); ctx.stroke();

  // the Kuroshio stream across the black rear fuselage (in place of the fern)
  ctx.strokeStyle = '#f4f4f4'; ctx.lineCap = 'round'; ctx.lineJoin = 'round'; ctx.lineWidth = 0.36;
  const th = 2 * Math.atan(2.4 / 11), R = 11 / (2 * Math.sin(th));
  for (const [i, a, b] of [[1, 1.2, 1.6], [0, 2.6, 3.4], [-1, 0.6, 1.0]]) {
    const pts = sCurve(38.3, 4.55, i, R, th, 0.85, a, b);
    ctx.beginPath(); pts.forEach(([x, y], k) => k ? ctx.lineTo(x, y) : ctx.moveTo(x, y)); ctx.stroke();
  }

  // fin: rudder hinge line, then the mark
  ctx.strokeStyle = 'rgba(255,255,255,0.09)'; ctx.lineWidth = 0.022; ctx.lineCap = 'butt';
  ctx.beginPath();
  for (let y = 9.2; y <= 16.85; y += 0.1) { const x = finLE(y) + 0.71 * (finTE(y) - finLE(y)); y === 9.2 ? ctx.moveTo(x, y) : ctx.lineTo(x, y); }
  ctx.stroke();
  ctx.beginPath(); { const y = 12.9, x = finLE(y) + 0.71 * (finTE(y) - finLE(y)); ctx.moveTo(x, y); ctx.lineTo(finTE(y), y); } ctx.stroke();

  const MS = +P.get('ms') || 5.8, MX = +P.get('mx') || 52.1, MY = +P.get('my') || 13.4;
  ctx.save();
  ctx.translate(MX, MY); ctx.scale(MS / 150, -MS / 150); ctx.translate(-100, -100);
  ctx.translate(100, 100); ctx.scale(MARK.sc, MARK.sc); ctx.translate(MARK.tx, -100);
  ctx.strokeStyle = '#f6f6f6'; ctx.lineWidth = MARK.sw; ctx.lineCap = 'round';
  MARK.paths.forEach(d => ctx.stroke(new Path2D(d)));
  ctx.fillStyle = '#f6f6f6'; ctx.beginPath(); ctx.arc(MARK.dot[0], MARK.dot[1], MARK.dot[2], 0, Math.PI * 2); ctx.fill();
  ctx.restore();

  // wordmark, painted upright as seen from this side; its forward end sits at x = 9.3 on both sides
  ctx.setTransform(1, 0, 0, 1, 0, 0);
  const capH = 0.98, fs = capH / 0.727 * K;
  ctx.font = `500 ${fs}px "Inter Display"`;
  ctx.letterSpacing = `${(0.13 * fs).toFixed(1)}px`;
  ctx.fillStyle = '#0b0b0c'; ctx.textBaseline = 'alphabetic';
  const base = (HM - 6.98) * K;
  if (side > 0) { ctx.textAlign = 'left'; ctx.fillText('ASUKA AIR', 9.3 * K, base); }
  else { ctx.textAlign = 'right'; ctx.fillText('ASUKA AIR', (L - 9.3) * K + 0.13 * fs, base); }

  const t = new THREE.CanvasTexture(cv);
  t.colorSpace = THREE.SRGBColorSpace; t.anisotropy = 16;
  t.minFilter = THREE.LinearMipmapLinearFilter; t.generateMipmaps = true;
  return t;
}

function liveryMaterial(texR, texL) {
  const m = new THREE.MeshPhysicalMaterial({ color: 0xffffff, roughness: 0.28, metalness: 0, clearcoat: 0.55, clearcoatRoughness: 0.12 });
  m.onBeforeCompile = sh => {
    sh.uniforms.texR = { value: texR }; sh.uniforms.texL = { value: texL };
    sh.uniforms.ext = { value: new THREE.Vector3(WM, HM, L) };
    sh.vertexShader = sh.vertexShader
      .replace('#include <common>', '#include <common>\nvarying vec3 vPosM;')
      .replace('#include <begin_vertex>', '#include <begin_vertex>\nvPosM = position;');
    sh.fragmentShader = sh.fragmentShader
      .replace('#include <common>', '#include <common>\nvarying vec3 vPosM;\nuniform sampler2D texR;\nuniform sampler2D texL;\nuniform vec3 ext;')
      .replace('#include <map_fragment>', `
        vec2 uvR = vec2(vPosM.x / ext.x, vPosM.y / ext.y);
        vec2 uvL = vec2((ext.z - vPosM.x) / ext.x, vPosM.y / ext.y);
        vec2 gx = dFdx(uvR), gy = dFdy(uvR);
        vec4 lc = vPosM.z >= 0.0 ? textureGrad(texR, uvR, gx, gy) : textureGrad(texL, uvL, -gx, -gy);
        diffuseColor.rgb *= lc.rgb;
        float darkPaint = 1.0 - smoothstep(0.05, 0.25, lc.g);
      `)
      .replace('#include <roughnessmap_fragment>', '#include <roughnessmap_fragment>\nroughnessFactor = mix(roughnessFactor, 0.22, darkPaint);');
  };
  return m;
}

// ---------------------------------------------------------------------------
// wing paint (plan view)
// ---------------------------------------------------------------------------
function paintWing() {
  const K2 = 90, cw = 28 * K2, ch = 31 * K2;
  const cv = document.createElement('canvas'); cv.width = cw; cv.height = ch;
  const ctx = cv.getContext('2d');
  ctx.fillStyle = '#d5d8db'; ctx.fillRect(0, 0, cw, ch);
  ctx.setTransform(K2, 0, 0, K2, -18 * K2, 0);
  const line = (f, z0, z1) => { ctx.beginPath(); for (let z = z0; z <= z1 + 1e-6; z += 0.2) { const w = wingAt(z), x = f(w); z === z0 ? ctx.moveTo(x, z) : ctx.lineTo(x, z); } ctx.stroke(); };
  ctx.fillStyle = '#c3c7cb';
  ctx.beginPath();
  for (let z = 0; z <= 30.1; z += 0.2) { const w = wingAt(z); ctx.lineTo(w.le - 0.3, z); }
  for (let z = 30.06; z >= 0; z -= 0.2) { const w = wingAt(z); ctx.lineTo(w.le + 0.07 * (w.te - w.le), z); }
  ctx.fill();
  ctx.strokeStyle = 'rgba(40,46,52,0.35)'; ctx.lineWidth = 0.025;
  const at = f => w => w.le + f * (w.te - w.le);
  line(at(0.07), 3, 28); line(at(0.17), 3, 28); line(at(0.63), 3, 26.5); line(at(0.76), 3, 26.5);
  ctx.beginPath();
  for (let z = 3.6; z < 23.5; z += 1.65) { const w = wingAt(z); ctx.moveTo(at(0.63)(w), z); ctx.lineTo(at(0.76)(w), z); }
  for (const z of [3.0, 9.0, 11.2, 21.5, 26.5]) { const w = wingAt(z); ctx.moveTo(at(0.76)(w), z); ctx.lineTo(w.te + 0.3, z); }
  for (let z = 5; z < 28; z += 3.4) { const w = wingAt(z); ctx.moveTo(w.le - 0.2, z); ctx.lineTo(at(0.07)(w), z); }
  ctx.stroke();
  const t = new THREE.CanvasTexture(cv);
  t.colorSpace = THREE.SRGBColorSpace; t.anisotropy = 16; t.flipY = false;
  return t;
}

function paintConcrete() {
  const n = 2048, cv = document.createElement('canvas'); cv.width = cv.height = n;
  const ctx = cv.getContext('2d');
  ctx.fillStyle = '#a7a59f'; ctx.fillRect(0, 0, n, n);
  let seed = 7; const rnd = () => (seed = (seed * 16807) % 2147483647) / 2147483647;
  for (let k = 0; k < 160; k++) {
    const x = rnd() * n, y = rnd() * n, r = 40 + rnd() * 220;
    const g = ctx.createRadialGradient(x, y, 0, x, y, r);
    const c = rnd() < 0.5 ? '0,0,0' : '255,255,255';
    g.addColorStop(0, `rgba(${c},${0.03 + rnd() * 0.04})`); g.addColorStop(1, `rgba(${c},0)`);
    ctx.fillStyle = g; ctx.fillRect(x - r, y - r, 2 * r, 2 * r);
  }
  for (let k = 0; k < 90000; k++) {
    const v = Math.floor(rnd() * 90 + 110);
    ctx.fillStyle = `rgba(${v},${v - 2},${v - 6},${0.25 + rnd() * 0.3})`;
    ctx.fillRect(rnd() * n, rnd() * n, 1 + rnd() * 2, 1 + rnd() * 2);
  }
  ctx.strokeStyle = 'rgba(70,68,64,0.75)'; ctx.lineWidth = 4;
  for (const p of [2, n / 2]) { ctx.beginPath(); ctx.moveTo(p, 0); ctx.lineTo(p, n); ctx.moveTo(0, p); ctx.lineTo(n, p); ctx.stroke(); }
  const t = new THREE.CanvasTexture(cv);
  t.colorSpace = THREE.SRGBColorSpace; t.wrapS = t.wrapT = THREE.RepeatWrapping; t.anisotropy = 16;
  return t;
}

function paintGrass() {
  const n = 1024, cv = document.createElement('canvas'); cv.width = cv.height = n;
  const ctx = cv.getContext('2d');
  ctx.fillStyle = '#7b8452'; ctx.fillRect(0, 0, n, n);
  let seed = 11; const rnd = () => (seed = (seed * 16807) % 2147483647) / 2147483647;
  for (let k = 0; k < 60000; k++) {
    const g = Math.floor(100 + rnd() * 60);
    ctx.fillStyle = `rgba(${g - 20},${g},${g - 55},0.35)`; ctx.fillRect(rnd() * n, rnd() * n, 2, 2 + rnd() * 3);
  }
  const t = new THREE.CanvasTexture(cv); t.colorSpace = THREE.SRGBColorSpace; t.wrapS = t.wrapT = THREE.RepeatWrapping; t.anisotropy = 16;
  return t;
}
function paintTrees() {
  const w = 8192, h = 256, cv = document.createElement('canvas'); cv.width = w; cv.height = h;
  const ctx = cv.getContext('2d');
  let seed = 3; const rnd = () => (seed = (seed * 16807) % 2147483647) / 2147483647;
  ctx.fillStyle = '#4a5a48';
  ctx.beginPath(); ctx.moveTo(0, h);
  let y = 150;
  for (let x = 0; x <= w; x += 6) { y += (rnd() - 0.5) * 14; y = clamp(y, 110, 205); const bump = Math.sin(x * 0.09) * 6 + Math.sin(x * 0.023) * 10; ctx.lineTo(x, y + bump); }
  ctx.lineTo(w, h); ctx.closePath(); ctx.fill();
  for (let k = 0; k < 10; k++) {   // a few distant hangars
    const x = rnd() * w, bw = 120 + rnd() * 220, bh = 14 + rnd() * 22;
    ctx.fillStyle = rnd() < 0.5 ? '#9a9fa2' : '#aeb2b1'; ctx.fillRect(x, h - bh - 46, bw, bh + 46);
    ctx.fillStyle = 'rgba(0,0,0,0.12)'; ctx.fillRect(x, h - bh - 46, bw, 4);
  }
  const t = new THREE.CanvasTexture(cv); t.colorSpace = THREE.SRGBColorSpace; t.wrapS = THREE.RepeatWrapping; t.repeat.set(3, 1);
  return t;
}
function paintFan() {
  const n = 1024, cv = document.createElement('canvas'); cv.width = cv.height = n;
  const ctx = cv.getContext('2d'); const c = n / 2;
  ctx.fillStyle = '#121416'; ctx.fillRect(0, 0, n, n);
  for (let k = 0; k < 18; k++) {
    const a = k / 18 * Math.PI * 2;
    ctx.save(); ctx.translate(c, c); ctx.rotate(a);
    const g = ctx.createLinearGradient(0, -40, 0, 40);
    g.addColorStop(0, '#2a2e33'); g.addColorStop(0.5, '#5d646b'); g.addColorStop(1, '#1d2024');
    ctx.fillStyle = g;
    ctx.beginPath(); ctx.moveTo(60, -10); ctx.bezierCurveTo(200, -40, 380, -70, 505, -60); ctx.lineTo(505, 20); ctx.bezierCurveTo(380, 25, 200, 20, 60, 14); ctx.closePath(); ctx.fill();
    ctx.restore();
  }
  const t = new THREE.CanvasTexture(cv); t.colorSpace = THREE.SRGBColorSpace; return t;
}

// ---------------------------------------------------------------------------
// scene
// ---------------------------------------------------------------------------
await document.fonts.load('500 200px "Inter Display"');

const renderer = new THREE.WebGLRenderer({ antialias: true, preserveDrawingBuffer: true });
renderer.setPixelRatio(1); renderer.setSize(W, H);
renderer.toneMapping = THREE.ACESFilmicToneMapping;
renderer.toneMappingExposure = +P.get('exp') || 0.62;
renderer.shadowMap.enabled = true; renderer.shadowMap.type = THREE.PCFSoftShadowMap;
document.body.appendChild(renderer.domElement);

const scene = new THREE.Scene();
const sunEl = THREE.MathUtils.degToRad(+P.get('el') || 34), sunAz = THREE.MathUtils.degToRad(+P.get('az') || 318);
const sunDir = new THREE.Vector3().setFromSphericalCoords(1, Math.PI / 2 - sunEl, sunAz);

// sky dome: gradient with a sun glow
const HOR = new THREE.Color(0xcbd9e6), ZEN = new THREE.Color(0x3f78c4), GND = new THREE.Color(0x8a8a80);
function skyDome(radius) {
  const m = new THREE.ShaderMaterial({
    side: THREE.BackSide, depthWrite: false, fog: false,
    uniforms: { top: { value: ZEN }, hor: { value: HOR }, gnd: { value: GND }, sunDir: { value: sunDir }, gain: { value: +P.get('skyg') || 1.25 } },
    vertexShader: 'varying vec3 vDir; void main(){ vDir = normalize(position); gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); }',
    fragmentShader: `uniform vec3 top; uniform vec3 hor; uniform vec3 gnd; uniform vec3 sunDir; uniform float gain; varying vec3 vDir;
      void main(){
        vec3 d = normalize(vDir); float h = d.y;
        vec3 c = h > 0.0 ? mix(hor, top, pow(clamp(h, 0.0, 1.0), 0.6)) : mix(hor, gnd, pow(clamp(-h * 4.0, 0.0, 1.0), 0.5));
        float s = max(dot(d, sunDir), 0.0);
        c = c * gain + vec3(1.0, 0.94, 0.84) * (pow(s, 600.0) * 30.0 + pow(s, 12.0) * 0.35);
        gl_FragColor = vec4(c, 1.0);
        #include <tonemapping_fragment>
        #include <colorspace_fragment>
      }`,
  });
  return new THREE.Mesh(new THREE.SphereGeometry(radius, 64, 32), m);
}
scene.add(skyDome(9000));

// environment: sky plus a sunlit ground, prefiltered
const pmrem = new THREE.PMREMGenerator(renderer);
const envScene = new THREE.Scene();
envScene.add(skyDome(1000));
const envGround = new THREE.Mesh(new THREE.CircleGeometry(900, 48).rotateX(-Math.PI / 2), new THREE.MeshBasicMaterial({ color: 0x9a968c }));
envGround.position.y = -1.5; envScene.add(envGround);
scene.environment = pmrem.fromScene(envScene, 0.02, 0.1, 3000).texture;
scene.environmentIntensity = +P.get('env') || 0.9;
scene.fog = new THREE.Fog(HOR.clone(), 300, 3200);

const target = new THREE.Vector3(28, 5, 0);
const sun = new THREE.DirectionalLight(0xfff4e6, +P.get('sun') || 4.2);
sun.position.copy(target).addScaledVector(sunDir, 160); sun.target.position.copy(target);
sun.castShadow = true;
Object.assign(sun.shadow.camera, { left: -48, right: 48, top: 48, bottom: -48, near: 20, far: 340 });
sun.shadow.mapSize.set(4096, 4096); sun.shadow.bias = -0.00015; sun.shadow.normalBias = 0.025;
scene.add(sun, sun.target);

// ground: concrete apron inside grass, with a distant tree line
const conc = paintConcrete(); conc.repeat.set(420 / 15, 400 / 15);
const apron = new THREE.Mesh(new THREE.PlaneGeometry(420, 400).rotateX(-Math.PI / 2),
  new THREE.MeshStandardMaterial({ map: conc, roughness: 0.92, metalness: 0 }));
apron.position.set(40, 0, 70); apron.receiveShadow = true; scene.add(apron);
const grass = new THREE.Mesh(new THREE.PlaneGeometry(9000, 9000).rotateX(-Math.PI / 2),
  new THREE.MeshStandardMaterial({ map: paintGrass(), roughness: 1, metalness: 0 }));
grass.position.y = -0.03; grass.material.map.repeat.set(9000 / 40, 9000 / 40); grass.receiveShadow = true; scene.add(grass);
const trees = new THREE.Mesh(new THREE.CylinderGeometry(2200, 2200, 70, 256, 1, true),
  new THREE.MeshBasicMaterial({ map: paintTrees(), transparent: true, side: THREE.BackSide, alphaTest: 0.02 }));
trees.position.y = 34; scene.add(trees);
const yellow = new THREE.MeshStandardMaterial({ color: 0xd8a01c, roughness: 0.75 });
const lead = new THREE.Mesh(new THREE.PlaneGeometry(400, 0.18).rotateX(-Math.PI / 2), yellow);
lead.position.set(40, 0.004, 0); lead.receiveShadow = true; scene.add(lead);
const stop = new THREE.Mesh(new THREE.PlaneGeometry(0.3, 4).rotateX(-Math.PI / 2), yellow);
stop.position.set(5.2, 0.004, 0); stop.receiveShadow = true; scene.add(stop);

// materials
const texR = paintSide(1), texL = paintSide(-1);
const livery = liveryMaterial(texR, texL);
const white = new THREE.MeshPhysicalMaterial({ color: 0xf0f1f2, roughness: 0.3, clearcoat: 0.5, clearcoatRoughness: 0.15 });
const wingMat = new THREE.MeshPhysicalMaterial({ map: paintWing(), roughness: 0.42, metalness: 0.08, clearcoat: 0.25 });
const lipMat = new THREE.MeshStandardMaterial({ color: 0xd9dcdf, roughness: 0.18, metalness: 1.0 });
const ductMat = new THREE.MeshStandardMaterial({ color: 0x8e9398, roughness: 0.45, metalness: 0.5, side: THREE.DoubleSide });
const coreMat = new THREE.MeshStandardMaterial({ color: 0xa3a8ad, roughness: 0.4, metalness: 0.6 });
const plugMat = new THREE.MeshStandardMaterial({ color: 0x6e655c, roughness: 0.55, metalness: 0.7 });
const darkMat = new THREE.MeshStandardMaterial({ color: 0x1d1f22, roughness: 0.6, metalness: 0.3, side: THREE.DoubleSide });
const tireMat = new THREE.MeshStandardMaterial({ color: 0x1a1a1b, roughness: 0.85 });
const hubMat = new THREE.MeshStandardMaterial({ color: 0x9aa0a6, roughness: 0.35, metalness: 0.8 });
const strutMat = new THREE.MeshStandardMaterial({ color: 0xb8bcc0, roughness: 0.25, metalness: 0.9 });
const greyPaint = new THREE.MeshStandardMaterial({ color: 0x8d9196, roughness: 0.5, metalness: 0.2 });

const plane = new THREE.Group(); scene.add(plane);
const add = (geo, mat, parent = plane) => { const m = new THREE.Mesh(geo, mat); m.castShadow = m.receiveShadow = true; parent.add(m); return m; };

add(fuselageGeometry(), livery);
add(finGeometry(), livery);
add(latheX([[L - 0.25, 0.33], [L + 0.05, 0.31]], 48, 7.9, 0), darkMat);
const stabR = add(stabGeometry(), white);
const stabL = add(stabGeometry(), white); stabL.scale.z = -1;

// one side's wing, engine, pylon, flap-track fairings and main gear, mirrored for the other side
const side = new THREE.Group(); plane.add(side);
add(wingGeometry(), wingMat, side);
const EY = 2.55, EZ = 9.7;
add(latheX([[22.0, 1.40], [21.6, 1.42], [21.1, 1.47], [21.0, 1.55], [21.05, 1.63], [21.2, 1.70]], 160, EY, EZ), lipMat, side);
add(latheX([[21.2, 1.70], [21.6, 1.76], [22.6, 1.785], [24.0, 1.76], [25.2, 1.66], [26.1, 1.50]], 192, EY, EZ, f => 0.15 * tri(14 * f / (2 * Math.PI))), white, side);
add(latheX([[26.05, 1.46], [25.0, 1.55], [24.0, 1.58]], 96, EY, EZ), darkMat, side);
add(latheX([[24.6, 1.22], [25.6, 1.19], [26.4, 1.12], [27.4, 0.98], [28.1, 0.80]], 160, EY, EZ, f => 0.09 * tri(12 * f / (2 * Math.PI))), coreMat, side);
add(latheX([[27.8, 0.66], [28.4, 0.58], [29.2, 0.32], [29.75, 0.02]], 64, EY, EZ), plugMat, side);
add(latheX([[21.42, 0.001], [21.55, 0.17], [21.75, 0.32], [22.0, 0.44], [22.2, 0.5]], 64, EY, EZ), darkMat, side);
const fan = new THREE.Mesh(new THREE.CircleGeometry(1.41, 96), new THREE.MeshStandardMaterial({ map: paintFan(), roughness: 0.4, metalness: 0.6 }));
fan.geometry.rotateY(-Math.PI / 2); fan.position.set(22.0, EY, EZ); side.add(fan);

const pylon = new THREE.Shape([[21.9, 4.1], [22.4, 4.6], [24.0, 4.85], [27.5, 4.9], [33.0, 4.72], [35.6, 4.3], [35.2, 4.02], [31.0, 3.78], [28.0, 3.55], [26.0, 3.62], [24.0, 3.9]].map(([x, y]) => new THREE.Vector2(x, y)));
const pyg = new THREE.ExtrudeGeometry(pylon, { depth: 0.42, bevelEnabled: true, bevelThickness: 0.07, bevelSize: 0.07, bevelSegments: 4, curveSegments: 24 });
pyg.translate(0, 0, EZ - 0.21); add(pyg, white, side);

// flap-track fairings
const canoe = (() => {
  const pts = []; for (let k = 0; k <= 32; k++) { const t = k / 32; pts.push(new THREE.Vector2(0.27 * Math.pow(Math.sin(Math.PI * Math.pow(t, 0.8)), 0.75) + 0.001, t)); }
  return new THREE.LatheGeometry(pts, 32).rotateZ(-Math.PI / 2);
})();
for (const z of [6.0, 13.2, 17.6, 22.2]) {
  const w = wingAt(z), c = w.te - w.le, len = c * 0.42 + 0.8;
  const m = add(canoe, white, side);
  m.scale.set(len, 0.72, 0.55);
  m.position.set(w.le + 0.58 * c, w.y - 0.02 * c - 0.05, z);
}

// main gear
const tireGeo = new THREE.LatheGeometry([[0.42, -0.25], [0.55, -0.26], [0.61, -0.245], [0.638, -0.18], [0.645, 0], [0.638, 0.18], [0.61, 0.245], [0.55, 0.26], [0.42, 0.25]].map(([r, h]) => new THREE.Vector2(r, h)), 64).rotateX(Math.PI / 2);
const hubGeo = new THREE.CylinderGeometry(0.42, 0.42, 0.46, 48).rotateX(Math.PI / 2);
const cyl = (a, b, r, mat, parent) => {
  const A = new THREE.Vector3(...a), B = new THREE.Vector3(...b), len = A.distanceTo(B);
  const m = add(new THREE.CylinderGeometry(r, r, len, 24), mat, parent);
  m.position.copy(A).add(B).multiplyScalar(0.5);
  m.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), B.clone().sub(A).normalize());
  return m;
};
const GX = 28.8, GZ = 4.9, RW = 0.645;
for (const ax of [GX - 0.68, GX + 0.68]) for (const dz of [-0.7, 0.7]) {
  add(tireGeo, tireMat, side).position.set(ax, RW, GZ + dz);
  add(hubGeo, hubMat, side).position.set(ax, RW, GZ + dz);
}
add(new THREE.BoxGeometry(2.0, 0.26, 0.32), strutMat, side).position.set(GX, RW + 0.05, GZ);
for (const ax of [GX - 0.68, GX + 0.68]) cyl([ax, RW, GZ - 0.95], [ax, RW, GZ + 0.95], 0.09, strutMat, side);
cyl([GX, RW + 0.1, GZ], [GX, 3.9, GZ - 0.25], 0.2, strutMat, side);
cyl([GX, 2.3, GZ], [GX - 1.5, 3.8, GZ - 1.6], 0.08, greyPaint, side);
cyl([GX, 2.6, GZ], [GX + 1.3, 3.8, GZ - 1.2], 0.08, greyPaint, side);
add(new THREE.BoxGeometry(2.1, 2.3, 0.05), white, side).position.set(GX, 2.75, GZ + 0.45);

const other = side.clone(); other.scale.z = -1; plane.add(other);

// nose gear and doors
const ntire = tireGeo.clone().scale(0.8, 0.8, 0.8);
for (const dz of [-0.3, 0.3]) {
  add(ntire, tireMat).position.set(6.0, 0.52, dz);
  add(hubGeo.clone().scale(0.75, 0.75, 0.7), hubMat).position.set(6.0, 0.52, dz);
}
cyl([6.0, 0.52, -0.45], [6.0, 0.52, 0.45], 0.06, strutMat);
cyl([6.0, 0.55, 0], [6.0, 3.3, 0], 0.13, strutMat);
cyl([6.0, 1.6, 0], [7.4, 3.1, 0], 0.06, greyPaint);
for (const s of [-1, 1]) add(new THREE.BoxGeometry(1.7, 0.75, 0.035), white).position.set(6.3, 2.75, s * 0.6);

// antennas and beacons
for (const [x, top] of [[11.5, 1], [20.5, 1], [26.0, 1], [14.0, 0], [38.0, 0]]) {
  const p = prof(x), y = top ? p.yt : p.yb - p.dip;
  const m = add(new THREE.BoxGeometry(0.30, 0.22, 0.03), white); m.position.set(x, y + (top ? 0.09 : -0.09), 0); m.rotation.z = top ? 0.35 : -0.35;
}
for (const [x, top] of [[25.0, 1], [27.0, 0]]) {
  const p = prof(x), y = top ? p.yt : p.yb - p.dip;
  const m = new THREE.Mesh(new THREE.SphereGeometry(0.12, 16, 12), new THREE.MeshStandardMaterial({ color: 0xc0201a, emissive: 0x500805, roughness: 0.2 }));
  m.position.set(x, y, 0); plane.add(m);
}

// ---------------------------------------------------------------------------
// cameras
// ---------------------------------------------------------------------------
const VIEWS = {
  side: { fov: 7.2, pos: [28.6, 3.4, 230], at: [28.6, 6.9, 0] },
  hero: { fov: 25, pos: [-22, 2.0, 36], at: [24, 6.6, 1.0] },
  tail: { fov: 30, pos: [70, 7.5, 26], at: [48.5, 11.0, 0] },
  rear: { fov: 30, pos: [86, 4.0, -40], at: [32, 7.5, 0] },
};
const v = VIEWS[VIEW];
const cam = new THREE.PerspectiveCamera(+P.get('fov') || v.fov, W / H, 0.5, 20000);
cam.position.set(...v.pos); cam.lookAt(new THREE.Vector3(...v.at));
renderer.render(scene, cam);
window.__done = true;
