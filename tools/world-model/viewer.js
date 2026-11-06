// 區域 3D 模型的檢視網頁：方塊資料在 window.MODEL（build.py 放進來），three.js 在 window.THREE。
// 座標直接用 Minecraft 的座標：X 往東、Y 往上、Z 往南。
(async function () {
  'use strict';
  const T = window.THREE, D = window.MODEL;
  const [OX, OY, OZ] = D.origin, [SX, SY, SZ] = D.size;
  const $ = (id) => document.getElementById(id);

  // ── 解開方塊資料 ──
  async function inflate(b64) {
    const bin = Uint8Array.from(atob(b64), (c) => c.charCodeAt(0));
    const stream = new Blob([bin]).stream().pipeThrough(new DecompressionStream('deflate'));
    return await new Response(stream).arrayBuffer();
  }
  const grid = new Uint16Array(await inflate(D.grid));
  const P = D.pal, NP = P.length;
  const KIND = new Uint8Array(NP), OCC = new Uint8Array(NP), MAT = new Uint8Array(NP), GLS = new Uint8Array(NP);
  const KINDS = { none: 0, cube: 1, boxes: 2, pane: 3, fence: 4, cross: 5, wall: 2 };
  P.forEach((p, i) => {
    KIND[i] = KINDS[p.k] ?? 1;
    OCC[i] = p.o ? 1 : 0;
    MAT[i] = p.m || 0;
    GLS[i] = p.g ? 1 : 0;
  });
  const isGate = P.map((p) => /fence_gate/.test(p.n));
  const at = (x, y, z) => (x < 0 || y < 0 || z < 0 || x >= SX || y >= SY || z >= SZ) ? 0 : grid[(y * SZ + z) * SX + x];

  // ── 材質拼圖 ──
  const A = D.atlas;
  function loadTexture(b64) {
    return new Promise((ok) => {
      const img = new Image();
      img.onload = () => {
        const t = new T.Texture(img);
        t.colorSpace = T.SRGBColorSpace;
        t.magFilter = T.NearestFilter;
        t.minFilter = T.NearestMipmapLinearFilter;
        t.generateMipmaps = true;
        t.anisotropy = 4;
        t.needsUpdate = true;
        ok(t);
      };
      img.src = 'data:image/png;base64,' + b64;
    });
  }
  const atlasTex = await loadTexture(A.png);
  const paintTex = await loadTexture(D.ptex);
  paintTex.magFilter = T.LinearFilter;
  paintTex.minFilter = T.LinearMipmapLinearFilter;

  const tileUV = new Float32Array((A.cols * Math.ceil((A.white + 2) / A.cols)) * 4);
  for (let t = 0; t < tileUV.length / 4; t++) {
    const col = t % A.cols, row = Math.floor(t / A.cols);
    const u0 = (col * A.cell + A.pad) / A.w, vt = 1 - (row * A.cell + A.pad) / A.h;
    tileUV.set([u0, vt - 16 / A.h, 16 / A.w, 16 / A.h], t * 4);
  }

  // ── 網格建構 ──
  const lin = (v) => Math.pow(v, 2.2);
  const SHADE = [0.72, 0.72, 1.0, 0.55, 0.86, 0.86]; // 東 西 上 下 南 北
  const AOL = [0.5, 0.68, 0.84, 1.0];
  class Buf {
    constructor() { this.p = []; this.u = []; this.c = []; this.i = []; this.n = 0; }
    quad(v, uv, col, flip) {
      const n = this.n;
      for (let k = 0; k < 4; k++) {
        this.p.push(v[k * 3], v[k * 3 + 1], v[k * 3 + 2]);
        this.u.push(uv[k * 2], uv[k * 2 + 1]);
        this.c.push(col[k * 3], col[k * 3 + 1], col[k * 3 + 2]);
      }
      if (flip) this.i.push(n + 1, n + 2, n + 3, n + 1, n + 3, n);
      else this.i.push(n, n + 1, n + 2, n, n + 2, n + 3);
      this.n += 4;
    }
    geometry() {
      const g = new T.BufferGeometry();
      g.setAttribute('position', new T.Float32BufferAttribute(this.p, 3));
      g.setAttribute('uv', new T.Float32BufferAttribute(this.u, 2));
      g.setAttribute('color', new T.Float32BufferAttribute(this.c, 3));
      g.setIndex(this.n > 65535 ? new T.Uint32BufferAttribute(this.i, 1) : new T.Uint16BufferAttribute(this.i, 1));
      g.computeBoundingSphere();
      return g;
    }
  }

  // 一個面：wx..：世界座標的盒子；l..：方塊內 0~1 的座標（算材質位置用）
  function face(buf, dir, x0, y0, z0, x1, y1, z1, lx0, ly0, lz0, lx1, ly1, lz1, tex, rgb, ao) {
    const c = (v) => Math.min(1, Math.max(0, v));
    lx0 = c(lx0); ly0 = c(ly0); lz0 = c(lz0); lx1 = c(lx1); ly1 = c(ly1); lz1 = c(lz1);
    let v, uv;
    switch (dir) {
      case 0: v = [x1, y0, z1, x1, y0, z0, x1, y1, z0, x1, y1, z1]; uv = [1 - lz1, ly0, 1 - lz0, ly0, 1 - lz0, ly1, 1 - lz1, ly1]; break;
      case 1: v = [x0, y0, z0, x0, y0, z1, x0, y1, z1, x0, y1, z0]; uv = [lz0, ly0, lz1, ly0, lz1, ly1, lz0, ly1]; break;
      case 2: v = [x0, y1, z1, x1, y1, z1, x1, y1, z0, x0, y1, z0]; uv = [lx0, 1 - lz1, lx1, 1 - lz1, lx1, 1 - lz0, lx0, 1 - lz0]; break;
      case 3: v = [x1, y0, z1, x0, y0, z1, x0, y0, z0, x1, y0, z0]; uv = [1 - lx1, 1 - lz1, 1 - lx0, 1 - lz1, 1 - lx0, 1 - lz0, 1 - lx1, 1 - lz0]; break;
      case 4: v = [x0, y0, z1, x1, y0, z1, x1, y1, z1, x0, y1, z1]; uv = [lx0, ly0, lx1, ly0, lx1, ly1, lx0, ly1]; break;
      default: v = [x1, y0, z0, x0, y0, z0, x0, y1, z0, x1, y1, z0]; uv = [1 - lx1, ly0, 1 - lx0, ly0, 1 - lx0, ly1, 1 - lx1, ly1];
    }
    const t = tex * 4, u0 = tileUV[t], v0 = tileUV[t + 1], du = tileUV[t + 2], dv = tileUV[t + 3];
    for (let k = 0; k < 8; k += 2) { uv[k] = u0 + uv[k] * du; uv[k + 1] = v0 + uv[k + 1] * dv; }
    const s = SHADE[dir];
    const col = new Array(12);
    for (let k = 0; k < 4; k++) {
      const a = ao ? AOL[ao[k]] : 1;
      col[k * 3] = lin(rgb[0] * s * a); col[k * 3 + 1] = lin(rgb[1] * s * a); col[k * 3 + 2] = lin(rgb[2] * s * a);
    }
    const flip = ao && (ao[0] + ao[2] < ao[1] + ao[3]);
    buf.quad(v, uv, col, flip);
  }

  // 方向：法線、面上的兩個軸
  const DIRS = [[1, 0, 0], [-1, 0, 0], [0, 1, 0], [0, -1, 0], [0, 0, 1], [0, 0, -1]];
  // 每個面四個角（順序同 face() 的頂點順序）相對方塊中心的偏移（-1 或 +1），用來算角落陰影
  const CORNERS = [
    [[1, -1, 1], [1, -1, -1], [1, 1, -1], [1, 1, 1]],
    [[-1, -1, -1], [-1, -1, 1], [-1, 1, 1], [-1, 1, -1]],
    [[-1, 1, 1], [1, 1, 1], [1, 1, -1], [-1, 1, -1]],
    [[1, -1, 1], [-1, -1, 1], [-1, -1, -1], [1, -1, -1]],
    [[-1, -1, 1], [1, -1, 1], [1, 1, 1], [-1, 1, 1]],
    [[1, -1, -1], [-1, -1, -1], [-1, 1, -1], [1, 1, -1]],
  ];
  function aoFor(x, y, z, dir) {
    const n = DIRS[dir], out = [0, 0, 0, 0];
    const occ = (a, b, c) => OCC[at(a, b, c)];
    for (let k = 0; k < 4; k++) {
      const cr = CORNERS[dir][k];
      const ax = [cr[0], cr[1], cr[2]];
      // 只保留面上的兩個軸
      const s1 = [0, 0, 0], s2 = [0, 0, 0];
      let first = true;
      for (let i = 0; i < 3; i++) {
        if (n[i] !== 0) continue;
        if (first) { s1[i] = ax[i]; first = false; } else s2[i] = ax[i];
      }
      const bx = x + n[0], by = y + n[1], bz = z + n[2];
      const a = occ(bx + s1[0], by + s1[1], bz + s1[2]), b = occ(bx + s2[0], by + s2[1], bz + s2[2]);
      const c = occ(bx + s1[0] + s2[0], by + s1[1] + s2[1], bz + s1[2] + s2[2]);
      out[k] = (a && b) ? 0 : 3 - (a + b + c);
    }
    return out;
  }

  const banners = D.banners, beds = D.beds;
  function instanceColor(p, x, y, z) {
    const key = `${x + OX},${y + OY},${z + OZ}`;
    if (p.banner && banners[key]) return banners[key][0].map((v) => v / 255);
    if (p.bed && beds[key]) return beds[key].map((v) => v / 255);
    return null;
  }
  const tintOf = (p) => (p.t_all ? p.t_all.map((v) => v / 255) : [1, 1, 1]);

  function connects(q, forPane) {
    if (OCC[q]) return true;
    if (forPane) return KIND[q] === 3 || (KIND[q] === 1 && GLS[q]);
    return KIND[q] === 4 || isGate[q];
  }

  // 一層一層建網格：每層分「本體」與「頂蓋」（上一層被切掉時才看得到的頂面）
  const layers = [];
  const group = new T.Group();
  const mats = [
    new T.MeshBasicMaterial({ map: atlasTex, vertexColors: true, side: T.FrontSide }),
    new T.MeshBasicMaterial({ map: atlasTex, vertexColors: true, side: T.DoubleSide, alphaTest: 0.5 }),
    new T.MeshBasicMaterial({ map: atlasTex, vertexColors: true, side: T.DoubleSide, transparent: true, depthWrite: false, opacity: 0.85 }),
  ];
  const clipPlanes = [];
  mats.forEach((m) => { m.clippingPlanes = clipPlanes; });

  const SHULKER_DIR = [3, 2, 5, 4, 1, 0]; // 方塊實體的 facing（0 下 1 上 2 北 3 南 4 西 5 東）→ 面的編號
  // 旗幟的布面另外畫，用合成好的圖樣
  const bannerBuf = new Buf();
  let tintPole = false;
  const BA = D.batlas;
  const FACE4 = { east: 0, west: 1, south: 4, north: 5 };
  const OPP4 = { east: 1, west: 0, south: 5, north: 4 };
  function addBanner(p, wx, wy, wz, tile, base) {
    const [a0, b0, c0, a1, b1, c1] = p.b[0].map((v) => v / 16);
    const front = FACE4[p.banner[1]], back = OPP4[p.banner[1]];
    const W = BA.cols * 20, H = BA.rows * 40;
    let uv;
    if (tile >= 0) {
      const col = tile % BA.cols, row = Math.floor(tile / BA.cols);
      const u0 = col * 20 / W, u1 = (col + 1) * 20 / W, vt = 1 - row * 40 / H, vb = 1 - (row + 1) * 40 / H;
      uv = [u0, vb, u1, vb, u1, vt, u0, vt];
    }
    for (let d = 0; d < 6; d++) {
      const tb = new Buf();
      face(tb, d, wx + a0, wy + b0, wz + c0, wx + a1, wy + b1, wz + c1, 0, 0, 0, 1, 1, 1, 0, [1, 1, 1], null);
      let u = uv, col;
      if (!uv || (d !== front && d !== back)) {
        const c = base.map((v) => lin(v / 255 * SHADE[d]));
        col = [...c, ...c, ...c, ...c];
        u = uv ? [uv[0] + 0.0001, uv[1] + 0.02 * (uv[5] - uv[1]), uv[0] + 0.0001, uv[1] + 0.02 * (uv[5] - uv[1]), uv[0] + 0.0001, uv[5], uv[0] + 0.0001, uv[5]] : [0, 0, 0, 0, 0, 0, 0, 0];
        if (!uv) { bannerBuf.quad(tb.p, u, col, false); continue; }
        col = [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1].map((v, i) => lin(SHADE[d]));
      } else {
        const sh = lin(SHADE[d] * 0.95 + 0.05);
        col = new Array(12).fill(sh);
      }
      bannerBuf.quad(tb.p, u, col, false);
    }
  }

  function buildLayer(y) {
    const bufs = {};
    const get = (key) => (bufs[key] ||= new Buf());
    const wy = y + OY;
    for (let z = 0; z < SZ; z++) {
      for (let x = 0; x < SX; x++) {
        const id = grid[(y * SZ + z) * SX + x];
        const k = KIND[id];
        if (k === 0) continue;
        const p = P[id];
        const wx = x + OX, wz = z + OZ;
        const gkey = MAT[id] * 2 + GLS[id];
        const tint = instanceColor(p, x, y, z) || tintOf(p);
        if (k === 1) {
          for (let d = 0; d < 6; d++) {
            const n = DIRS[d];
            const q = at(x + n[0], y + n[1], z + n[2]);
            let cap = false;
            if (OCC[q] || (q === id && MAT[id] !== 0)) {
              if (d !== 2) continue;
              cap = true;
            }
            let rgb = tint;
            if (d === 2 && p.tt) rgb = p.tt.map((v) => v / 255);
            const ao = MAT[id] === 0 ? aoFor(x, y, z, d) : null;
            let tex = p.t[d];
            if (p.door !== undefined && SHULKER_DIR[D.shulkers[`${wx},${wy},${wz}`] ?? 1] === d) tex = p.door;
            face(get((cap ? 'c' : 'b') + gkey), d, wx, wy, wz, wx + 1, wy + 1, wz + 1, 0, 0, 0, 1, 1, 1, tex, rgb, ao);
          }
          continue;
        }
        let boxes;
        if (k === 2) {
          boxes = p.b;
          if (p.banner) {
            const info = banners[`${wx},${wy},${wz}`];
            addBanner(p, wx, wy, wz, info ? info[1] : -1, info ? info[0] : [255, 255, 255]);
            boxes = p.b.slice(1);
            tintPole = true;
          }
        }
        else if (k === 3 || k === 4) {
          const pane = k === 3;
          const e = connects(at(x + 1, y, z), pane), w = connects(at(x - 1, y, z), pane);
          const s = connects(at(x, y, z + 1), pane), nn = connects(at(x, y, z - 1), pane);
          if (pane) {
            boxes = [];
            if (!(e || w || s || nn)) boxes.push([0, 0, 7, 16, 16, 9], [7, 0, 0, 9, 16, 16]);
            else {
              if (e || w) boxes.push([w ? 0 : 7, 0, 7, e ? 16 : 9, 16, 9]);
              if (s || nn) boxes.push([7, 0, nn ? 0 : 7, 9, 16, s ? 16 : 9]);
              if (!(e || w)) boxes.push([7, 0, 7, 9, 16, 9]);
            }
          } else {
            boxes = [[6, 0, 6, 10, 16, 10]];
            for (const [ok, b1, b2] of [[e, [10, 6, 7, 16, 9, 9], [10, 12, 7, 16, 15, 9]], [w, [0, 6, 7, 6, 9, 9], [0, 12, 7, 6, 15, 9]],
              [s, [7, 6, 10, 9, 9, 16], [7, 12, 10, 9, 15, 16]], [nn, [7, 6, 0, 9, 9, 6], [7, 12, 0, 9, 15, 6]]]) {
              if (ok) boxes.push(b1, b2);
            }
          }
        } else if (k === 5) {
          const b = get('b' + (1 * 2));
          const t = p.t[2];
          const cx = wx + 0.5, cz = wz + 0.5, r = 0.45;
          // 交叉的兩片
          for (const [ax, az, bx, bz] of [[-r, -r, r, r], [-r, r, r, -r]]) {
            const v = [cx + ax, wy, cz + az, cx + bx, wy, cz + bz, cx + bx, wy + 1, cz + bz, cx + ax, wy + 1, cz + az];
            const tu = tileUV[t * 4], tv = tileUV[t * 4 + 1], du = tileUV[t * 4 + 2], dv = tileUV[t * 4 + 3];
            const uv = [tu, tv, tu + du, tv, tu + du, tv + dv, tu, tv + dv];
            const col = []; for (let q = 0; q < 4; q++) col.push(lin(tint[0] * 0.9), lin(tint[1] * 0.9), lin(tint[2] * 0.9));
            b.quad(v, uv, col, false);
          }
          continue;
        }
        if (!boxes) continue;
        const btint = tintPole ? [0.62, 0.48, 0.32] : tint;
        tintPole = false;
        for (const bx of boxes) {
          const [a0, b0, c0, a1, b1, c1] = bx.map((v) => v / 16);
          for (let d = 0; d < 6; d++) {
            const n = DIRS[d];
            const onEdge = (d === 0 && a1 >= 1) || (d === 1 && a0 <= 0) || (d === 2 && b1 >= 1) || (d === 3 && b0 <= 0) || (d === 4 && c1 >= 1) || (d === 5 && c0 <= 0);
            let cap = false;
            if (onEdge && OCC[at(x + n[0], y + n[1], z + n[2])]) {
              if (d !== 2) continue;
              cap = true;
            }
            face(get((cap ? 'c' : 'b') + gkey), d, wx + a0, wy + b0, wz + c0, wx + a1, wy + b1, wz + c1, a0, b0, c0, a1, b1, c1, p.t[d], btint, null);
          }
        }
      }
    }
    const L = { body: [], cap: [] };
    for (const key in bufs) {
      const gk = +key.slice(1);
      const mesh = new T.Mesh(bufs[key].geometry(), mats[gk >> 1]);
      mesh.userData.glass = gk & 1;
      mesh.matrixAutoUpdate = false;
      if (gk >> 1 === 2) mesh.renderOrder = 2;
      (key[0] === 'c' ? L.cap : L.body).push(mesh);
      group.add(mesh);
    }
    return L;
  }

  // ── 場景 ──
  const renderer = new T.WebGLRenderer({ antialias: true, preserveDrawingBuffer: true });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
  renderer.localClippingEnabled = true;
  $('app').appendChild(renderer.domElement);
  const scene = new T.Scene();
  scene.background = new T.Color(0x9cc3ea);
  scene.add(group);
  const persp = new T.PerspectiveCamera(75, 1, 0.05, 3000);
  const ortho = new T.OrthographicCamera(-1, 1, 1, -1, -500, 1000);
  let camera = persp;

  const t0 = performance.now();
  for (let y = 0; y < SY; y++) {
    layers.push(buildLayer(y));
    if (y % 4 === 0) { $('loading').textContent = `建立模型中… ${Math.round((y + 1) / SY * 100)}%`; await new Promise((r) => setTimeout(r, 0)); }
  }
  console.log('網格建立', Math.round(performance.now() - t0), 'ms');
  const bannerTex = await loadTexture(BA.png);
  bannerTex.minFilter = T.LinearMipmapLinearFilter;
  const bannerMesh = new T.Mesh(bannerBuf.geometry(), new T.MeshBasicMaterial({ map: bannerTex, vertexColors: true, side: T.FrontSide, clippingPlanes: clipPlanes }));
  scene.add(bannerMesh);

  // ── 告示牌文字 ──
  const signGroup = new T.Group();
  scene.add(signGroup);
  (function buildSigns() {
    const SW = 160, SH = 80, COLS = 25;
    const list = [];
    for (const s of D.signs) {
      const x = s[0] - OX, y = s[1] - OY, z = s[2] - OZ;
      const id = at(x, y, z), p = P[id];
      if (!p || !p.sign) continue;
      list.push([s, p]);
    }
    const slots = [];
    for (const [s, p] of list) {
      if (s[3].trim()) slots.push([s, p, s[3], s[4], false]);
      if (s[5].trim() && p.sign[0] !== 'wall') slots.push([s, p, s[5], s[6], true]);
    }
    if (!slots.length) return;
    const rows = Math.ceil(slots.length / COLS);
    const cv = document.createElement('canvas');
    cv.width = SW * COLS; cv.height = SH * rows;
    const g = cv.getContext('2d');
    g.textAlign = 'center'; g.textBaseline = 'middle';
    const buf = new Buf();
    const FACE = { east: 0, west: 1, south: 4, north: 5 };
    const OPP = { east: 'west', west: 'east', south: 'north', north: 'south' };
    slots.forEach(([s, p, text, color, back], i) => {
      const cx = (i % COLS) * SW, cy = Math.floor(i / COLS) * SH;
      const lines = text.split('\n').slice(0, 4);
      while (lines.length && !lines[lines.length - 1].trim()) lines.pop();
      let size = 17;
      g.font = `bold ${size}px "Microsoft JhengHei", sans-serif`;
      const widest = Math.max(...lines.map((l) => g.measureText(l).width), 1);
      if (widest > SW - 8) size = Math.max(8, Math.floor(size * (SW - 8) / widest));
      g.font = `bold ${size}px "Microsoft JhengHei", sans-serif`;
      g.fillStyle = color === '#000000' ? '#111' : color;
      const all = text.split('\n').slice(0, 4);
      const lh = SH / 4;
      all.forEach((l, k) => g.fillText(l, cx + SW / 2, cy + lh * (k + 0.5)));
      // 貼在板子的正面（或背面）
      const box = p.b[0].map((v) => v / 16);
      const facing = back ? OPP[p.sign[1]] : p.sign[1];
      const d = FACE[facing];
      const wx = s[0], wy = s[1], wz = s[2];
      const e = 0.004;
      let [a0, b0, c0, a1, b1, c1] = box;
      if (d === 0) a1 += e; else if (d === 1) a0 -= e; else if (d === 4) c1 += e; else c0 -= e;
      const fake = { 0: [1 - c1, 1 - c0], 1: [c0, c1], 4: [a0, a1], 5: [1 - a1, 1 - a0] }[d];
      // 用一般的 face() 但把材質座標換成這個文字格
      const u0 = cx / cv.width, u1 = (cx + SW) / cv.width, vb = 1 - (cy + SH) / cv.height, vt = 1 - cy / cv.height;
      const tb = new Buf();
      face(tb, d, wx + a0, wy + b0, wz + c0, wx + a1, wy + b1, wz + c1, a0, b0, c0, a1, b1, c1, 0, [1, 1, 1], null);
      // 依照面上的左右位置重新指定 u（0..1 → 文字格）
      for (let k = 0; k < 4; k++) {
        const uu = [0, 1, 1, 0][k], vv = [0, 0, 1, 1][k];
        tb.u[k * 2] = u0 + uu * (u1 - u0); tb.u[k * 2 + 1] = vb + vv * (vt - vb);
        tb.c[k * 3] = tb.c[k * 3 + 1] = tb.c[k * 3 + 2] = 1;
      }
      void fake;
      buf.quad(tb.p, tb.u, tb.c, false);
    });
    const tex = new T.CanvasTexture(cv);
    tex.colorSpace = T.SRGBColorSpace;
    tex.anisotropy = 4;
    const m = new T.MeshBasicMaterial({ map: tex, transparent: true, side: T.FrontSide, depthWrite: false, polygonOffset: true, polygonOffsetFactor: -2, clippingPlanes: clipPlanes });
    const mesh = new T.Mesh(buf.geometry(), m);
    mesh.renderOrder = 3;
    signGroup.add(mesh);
    signGroup.userData.mesh = mesh;
  })();

  // ── 畫 ──
  const paintGroup = new T.Group();
  scene.add(paintGroup);
  (function buildPaintings() {
    const buf = new Buf();
    const N = [[0, 0, 1], [-1, 0, 0], [0, 0, -1], [1, 0, 0]];
    for (const [px, py, pz, dir, motif] of D.paintings) {
      const uv = D.puv[motif];
      if (!uv) continue;
      const [u0, v0, u1, v1, w, h] = uv;
      const n = N[dir % 4];
      const r = [n[2], 0, -n[0]]; // 往右的方向 = 上 × 法線
      const cx = px + n[0] * 0.01, cy = py, cz = pz + n[2] * 0.01;
      const hw = w / 2, hh = h / 2;
      const v = [cx - r[0] * hw, cy - hh, cz - r[2] * hw, cx + r[0] * hw, cy - hh, cz + r[2] * hw,
        cx + r[0] * hw, cy + hh, cz + r[2] * hw, cx - r[0] * hw, cy + hh, cz - r[2] * hw];
      buf.quad(v, [u0, v0, u1, v0, u1, v1, u0, v1], [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1], false);
    }
    const mesh = new T.Mesh(buf.geometry(), new T.MeshBasicMaterial({ map: paintTex, vertexColors: true, side: T.FrontSide, clippingPlanes: clipPlanes }));
    paintGroup.add(mesh);
  })();

  // ── NPC、盔甲座、礦車 ──
  const peopleGroup = new T.Group();
  scene.add(peopleGroup);
  (function buildPeople() {
    const buf = new Buf();
    const white = A.white;
    function box(cx, cy, cz, yaw, x0, y0, z0, x1, y1, z1, rgb) {
      // 先在原點建盒子，再依照 yaw 轉
      const tb = new Buf();
      for (let d = 0; d < 6; d++) face(tb, d, x0, y0, z0, x1, y1, z1, 0, 0, 0, 1, 1, 1, white, rgb, null);
      const a = yaw * Math.PI / 180, cs = Math.cos(a), sn = Math.sin(a);
      for (let k = 0; k < tb.p.length; k += 3) {
        const x = tb.p[k], z = tb.p[k + 2];
        tb.p[k] = cx + x * cs - z * sn; tb.p[k + 1] = cy + tb.p[k + 1]; tb.p[k + 2] = cz + x * sn + z * cs;
      }
      for (let q = 0; q < tb.n; q += 4) {
        buf.quad(tb.p.slice(q * 3, q * 3 + 12), tb.u.slice(q * 2, q * 2 + 8), tb.c.slice(q * 3, q * 3 + 12), false);
      }
    }
    const SHIRT = [[0.25, 0.45, 0.7], [0.7, 0.25, 0.25], [0.25, 0.55, 0.35], [0.55, 0.45, 0.25], [0.45, 0.3, 0.6], [0.3, 0.6, 0.6], [0.8, 0.8, 0.8]];
    for (const [x, y, z, yaw, variant] of D.people) {
      const yb = Math.floor(y + 0.01);
      const shirt = SHIRT[variant % SHIRT.length];
      box(x, yb, z, yaw, -0.25, 0, -0.125, 0.25, 0.75, 0.125, [0.25, 0.25, 0.35]);
      box(x, yb, z, yaw, -0.25, 0.75, -0.125, 0.25, 1.5, 0.125, shirt);
      box(x, yb, z, yaw, -0.25, 1.5, -0.25, 0.25, 2.0, 0.25, [0.85, 0.68, 0.55]);
    }
    const HELM = { iron: [0.8, 0.8, 0.8], netherite: [0.27, 0.25, 0.27], leather: [0.6, 0.38, 0.22], golden: [0.95, 0.8, 0.25], diamond: [0.4, 0.85, 0.8], chainmail: [0.55, 0.55, 0.55] };
    const mat = (n) => { for (const k in HELM) if (n.includes(k)) return HELM[k]; return [0.7, 0.7, 0.7]; };
    for (const [x, y, z, yaw, helm, legs, hand, shield] of D.stands) {
      const yb = y;
      box(x, yb, z, yaw, -0.375, 0, -0.375, 0.375, 0.06, 0.375, [0.75, 0.75, 0.7]);
      box(x, yb, z, yaw, -0.05, 0, -0.05, 0.05, 1.45, 0.05, [0.7, 0.55, 0.35]);
      if (legs) box(x, yb, z, yaw, -0.25, 0.1, -0.13, 0.25, 0.8, 0.13, mat(legs));
      if (helm) box(x, yb, z, yaw, -0.27, 1.45, -0.27, 0.27, 1.98, 0.27, mat(helm));
      if (shield) box(x, yb, z, yaw, -0.47, 0.35, -0.42, -0.39, 1.72, 0.33, [0.14, 0.14, 0.15]); // 盾牌：拿在身體側邊，遊戲裡看到的是深色的背面
      else if (hand && hand.includes('carpet')) box(x, yb, z, yaw, -0.55, 0.62, 0.0, -0.15, 0.67, 0.4, [0.95, 0.95, 0.95]);
    }
    for (const [x, y, z, yaw] of D.carts) box(x, y, z, yaw, -0.45, 0, -0.35, 0.45, 0.6, 0.35, [0.45, 0.45, 0.48]);
    if (buf.n) peopleGroup.add(new T.Mesh(buf.geometry(), new T.MeshBasicMaterial({ map: atlasTex, vertexColors: true, clippingPlanes: clipPlanes })));
  })();

  // ── 座標尺 ──
  const rulerGroup = new T.Group();
  scene.add(rulerGroup);
  function label(text, x, y, z, scale = 3) {
    const cv = document.createElement('canvas');
    cv.width = 128; cv.height = 48;
    const g = cv.getContext('2d');
    g.fillStyle = 'rgba(255,255,255,0.85)'; g.fillRect(0, 0, 128, 48);
    g.fillStyle = '#123'; g.font = 'bold 26px Consolas, monospace'; g.textAlign = 'center'; g.textBaseline = 'middle';
    g.fillText(text, 64, 25);
    const tex = new T.CanvasTexture(cv); tex.colorSpace = T.SRGBColorSpace;
    const sp = new T.Sprite(new T.SpriteMaterial({ map: tex, depthTest: false }));
    sp.position.set(x, y, z); sp.scale.set(scale * 2.67, scale, 1); sp.renderOrder = 10;
    return sp;
  }
  function buildRuler(yLevel) {
    rulerGroup.clear();
    const pts = [];
    const y = yLevel + 0.05;
    for (let x = Math.ceil(OX / 10) * 10; x <= OX + SX; x += 10) {
      pts.push(x, y, OZ - 3, x, y, OZ + SZ + 3);
      rulerGroup.add(label('X ' + x, x, y + 1, OZ - 6));
    }
    for (let z = Math.ceil(OZ / 10) * 10; z <= OZ + SZ; z += 10) {
      pts.push(OX - 3, y, z, OX + SX + 3, y, z);
      rulerGroup.add(label('Z ' + z, OX - 8, y + 1, z));
    }
    const g = new T.BufferGeometry(); g.setAttribute('position', new T.Float32BufferAttribute(pts, 3));
    const lines = new T.LineSegments(g, new T.LineBasicMaterial({ color: 0x1d4f91, transparent: true, opacity: 0.35, depthTest: true }));
    rulerGroup.add(lines);
    rulerGroup.add(label('北 N ↑', OX + SX / 2, y + 2, OZ - 12, 4));
  }

  // ── 顯示範圍 ──
  const hi = $('hi'), lo = $('lo');
  for (const el of [hi, lo]) { el.min = OY; el.max = OY + SY - 1; el.step = 1; }
  hi.value = OY + SY - 1; lo.value = OY;
  let showGlass = true;
  function applyRange() {
    let h = +hi.value - OY, l = +lo.value - OY;
    if (l > h) { l = h; lo.value = h + OY; }
    $('hiv').textContent = +hi.value; $('lov').textContent = +lo.value;
    layers.forEach((L, y) => {
      const vis = y >= l && y <= h;
      for (const m of L.body) m.visible = vis && (showGlass || !m.userData.glass);
      for (const m of L.cap) m.visible = vis && y === h && (showGlass || !m.userData.glass);
    });
    // 告示牌、畫、人物也跟著高度裁切
    const top = +hi.value + 1, bottom = +lo.value;
    clipPlanes.length = 0;
    clipPlanes.push(new T.Plane(new T.Vector3(0, -1, 0), top + 0.001), new T.Plane(new T.Vector3(0, 1, 0), -bottom + 0.001));
    buildRuler(+lo.value + (+lo.value === OY ? 0 : 1));
  }
  hi.oninput = lo.oninput = () => { $('floornote').textContent = ''; markFloor(null); applyRange(); };
  const floorBtns = [];
  function markFloor(btn) { floorBtns.forEach((b) => b.classList.toggle('on', b === btn)); }
  for (const f of D.floors) {
    const b = document.createElement('button');
    b.textContent = `${f.name}（Y${f.floor}）`;
    b.onclick = () => { hi.value = f.hi; lo.value = f.lo; $('floornote').textContent = f.note; markFloor(b); applyRange(); };
    $('floors').appendChild(b); floorBtns.push(b);
  }
  const roofBtn = document.createElement('button');
  roofBtn.textContent = '拿掉屋頂（Y91 以下）';
  roofBtn.onclick = () => { hi.value = 91; lo.value = OY; $('floornote').textContent = '屋頂與天花板（Y92 以上）隱藏，看得到二樓和挑高的大廳'; markFloor(roofBtn); applyRange(); };
  $('floors').appendChild(roofBtn); floorBtns.push(roofBtn);
  const allBtn = document.createElement('button');
  allBtn.textContent = '全部（含屋頂）';
  allBtn.onclick = () => { hi.value = OY + SY - 1; lo.value = OY; $('floornote').textContent = ''; markFloor(allBtn); applyRange(); };
  $('floors').appendChild(allBtn); floorBtns.push(allBtn);
  $('showGlass').onchange = (e) => { showGlass = e.target.checked; applyRange(); };
  $('showSigns').onchange = (e) => { signGroup.visible = e.target.checked; };
  $('showPaint').onchange = (e) => { paintGroup.visible = e.target.checked; };
  $('showPeople').onchange = (e) => { peopleGroup.visible = e.target.checked; };
  $('showRuler').onchange = (e) => { rulerGroup.visible = e.target.checked && mode !== 'walk'; };

  // ── 相機控制 ──
  let mode = 'orbit';
  const target = new T.Vector3(OX + SX / 2, OY + 14, OZ + SZ / 2);
  let yaw = -35 * Math.PI / 180, pitch = 48 * Math.PI / 180, dist = 215; // 環繞：方位角、仰角、距離
  const eye = new T.Vector3(); let walkYaw = 0, walkPitch = 0; // 漫遊：Minecraft 的 yaw（0 朝南）
  let topZoom = 1.6, topCenter = new T.Vector3(target.x, 0, target.z);

  function setMode(m) {
    mode = m;
    for (const [id, mm] of [['vOrbit', 'orbit'], ['vWalk', 'walk'], ['vTop', 'top']]) $(id).classList.toggle('on', mm === m);
    camera = m === 'top' ? ortho : persp;
    rulerGroup.visible = $('showRuler').checked && m !== 'walk';
    $('help').innerHTML = {
      orbit: '左鍵拖曳：旋轉　右鍵拖曳：平移　滾輪：縮放<br>W A S D：移動中心點',
      walk: '左鍵拖曳：轉頭　W A S D：前後左右<br>空白鍵／E：上升　Q：下降　滾輪：調整速度',
      top: '俯視、北方在上。左鍵或右鍵拖曳：平移　滾輪：縮放<br>搭配「顯示高度」切出某一層的平面',
    }[m];
  }
  function resize() {
    const w = window.innerWidth, h = window.innerHeight;
    renderer.setSize(w, h);
    persp.aspect = w / h; persp.updateProjectionMatrix();
  }
  window.addEventListener('resize', resize); resize();

  function updateCamera() {
    if (mode === 'orbit') {
      persp.position.set(target.x + dist * Math.cos(pitch) * Math.sin(yaw), target.y + dist * Math.sin(pitch), target.z + dist * Math.cos(pitch) * Math.cos(yaw));
      persp.up.set(0, 1, 0); persp.lookAt(target);
    } else if (mode === 'walk') {
      persp.position.copy(eye);
      const dx = -Math.sin(walkYaw) * Math.cos(walkPitch), dy = -Math.sin(walkPitch), dz = Math.cos(walkYaw) * Math.cos(walkPitch);
      persp.up.set(0, 1, 0); persp.lookAt(eye.x + dx, eye.y + dy, eye.z + dz);
    } else {
      const w = window.innerWidth, h = window.innerHeight;
      const half = h / 2 / topZoom;
      ortho.left = -half * w / h; ortho.right = half * w / h; ortho.top = half; ortho.bottom = -half;
      ortho.position.set(topCenter.x, OY + SY + 50, topCenter.z);
      ortho.up.set(0, 0, -1); ortho.lookAt(topCenter.x, 0, topCenter.z);
      ortho.updateProjectionMatrix();
    }
    // 指北針
    const fwd = new T.Vector3(); camera.getWorldDirection(fwd);
    let ang;
    if (mode === 'top') ang = 0; else ang = Math.atan2(fwd.x, -fwd.z); // 畫面朝向和北方的夾角
    $('needle').innerHTML = [['北', 0, '#c22'], ['東', 90, '#333'], ['南', 180, '#333'], ['西', 270, '#333']].map(([t, a, c]) => {
      const r = (a * Math.PI / 180) - ang;
      return `<span style="left:${Math.sin(r) * 22}px;top:${-Math.cos(r) * 22}px;color:${c}">${t}</span>`;
    }).join('');
  }

  const el = renderer.domElement;
  el.addEventListener('contextmenu', (e) => e.preventDefault());
  let drag = null;
  el.addEventListener('pointerdown', (e) => { drag = { x: e.clientX, y: e.clientY, b: e.button, moved: 0, shift: e.shiftKey }; el.setPointerCapture(e.pointerId); });
  el.addEventListener('pointerup', (e) => {
    if (drag && drag.moved < 4 && drag.b === 0) pick(e.clientX, e.clientY, drag.shift);
    drag = null;
  });
  el.addEventListener('pointermove', (e) => {
    hover(e.clientX, e.clientY);
    if (!drag) return;
    const dx = e.clientX - drag.x, dy = e.clientY - drag.y;
    drag.x = e.clientX; drag.y = e.clientY; drag.moved += Math.abs(dx) + Math.abs(dy);
    if (mode === 'orbit') {
      if (drag.b === 0) { yaw -= dx * 0.005; pitch = Math.min(1.55, Math.max(-0.2, pitch + dy * 0.005)); }
      else {
        const s = dist * 0.0012;
        const right = new T.Vector3(Math.cos(yaw), 0, -Math.sin(yaw)), fwd = new T.Vector3(-Math.sin(yaw), 0, -Math.cos(yaw));
        target.addScaledVector(right, -dx * s).addScaledVector(fwd, dy * s);
      }
    } else if (mode === 'walk') {
      walkYaw += dx * 0.004; walkPitch = Math.min(1.5, Math.max(-1.5, walkPitch + dy * 0.004));
    } else {
      topCenter.x -= dx / topZoom; topCenter.z -= dy / topZoom;
    }
  });
  let walkSpeed = 8;
  el.addEventListener('wheel', (e) => {
    e.preventDefault();
    const f = Math.exp(e.deltaY * 0.0012);
    if (mode === 'orbit') dist = Math.min(1200, Math.max(3, dist * f));
    else if (mode === 'walk') { walkSpeed = Math.min(60, Math.max(1, walkSpeed / f)); status(); }
    else topZoom = Math.min(40, Math.max(0.5, topZoom / f));
  }, { passive: false });
  const keys = new Set();
  window.addEventListener('keydown', (e) => { if (e.target.tagName !== 'INPUT') keys.add(e.key.toLowerCase()); });
  window.addEventListener('keyup', (e) => keys.delete(e.key.toLowerCase()));

  // ── 點選方塊（沿視線逐格找第一個看得到的方塊）──
  const ray = new T.Raycaster(), ndc = new T.Vector2();
  function castBlock(cx, cy) {
    ndc.set(cx / window.innerWidth * 2 - 1, -(cy / window.innerHeight) * 2 + 1);
    ray.setFromCamera(ndc, camera);
    const o = ray.ray.origin.clone(), d = ray.ray.direction;
    const yHi = +hi.value, yLo = +lo.value;
    // 從模型範圍外面開始走
    let tmin = 0;
    const box = new T.Box3(new T.Vector3(OX, yLo, OZ), new T.Vector3(OX + SX, yHi + 1, OZ + SZ));
    const hit = ray.ray.intersectBox(box, new T.Vector3());
    if (!hit) return null;
    if (!box.containsPoint(o)) tmin = hit.distanceTo(o) + 1e-4;
    let x = Math.floor(o.x + d.x * tmin), y = Math.floor(o.y + d.y * tmin), z = Math.floor(o.z + d.z * tmin);
    const sx = Math.sign(d.x), sy = Math.sign(d.y), sz = Math.sign(d.z);
    const p = o.clone().addScaledVector(d, tmin);
    const nx = (v, s) => s > 0 ? Math.floor(v) + 1 : Math.ceil(v) - 1;
    let tx = d.x ? ((sx > 0 ? x + 1 : x) - p.x) / d.x : Infinity, ty = d.y ? ((sy > 0 ? y + 1 : y) - p.y) / d.y : Infinity, tz = d.z ? ((sz > 0 ? z + 1 : z) - p.z) / d.z : Infinity;
    const dx = Math.abs(1 / d.x), dy = Math.abs(1 / d.y), dz = Math.abs(1 / d.z);
    void nx;
    for (let i = 0; i < 1500; i++) {
      if (y >= yLo && y <= yHi) {
        const id = at(x - OX, y - OY, z - OZ);
        if (id && KIND[id] && (showGlass || !GLS[id])) return { x, y, z, id };
      }
      if (tx < ty && tx < tz) { x += sx; tx += dx; } else if (ty < tz) { y += sy; ty += dy; } else { z += sz; tz += dz; }
      if (x < OX - 1 || x > OX + SX || z < OZ - 1 || z > OZ + SZ || y < OY - 1 || y > OY + SY) return null;
    }
    return null;
  }
  const signAt = {};
  for (const s of D.signs) signAt[`${s[0]},${s[1]},${s[2]}`] = s;
  let hoverText = '';
  function describe(h) {
    if (!h) return '';
    const p = P[h.id];
    const s = signAt[`${h.x},${h.y},${h.z}`];
    let t = `(${h.x}, ${h.y}, ${h.z})  ${p.n}`;
    if (s) t += `　告示牌：「${s[3].replace(/\n/g, ' ').trim()}」` + (s[5].trim() ? ` 背面「${s[5].replace(/\n/g, ' ').trim()}」` : '');
    return t;
  }
  function hover(cx, cy) { hoverText = describe(castBlock(cx, cy)); status(); }
  const marks = [];
  const markGroup = new T.Group(); scene.add(markGroup);
  function pick(cx, cy, shift) {
    const h = castBlock(cx, cy);
    if (!h) return;
    if (shift) {
      marks.push(h);
      const m = new T.Mesh(new T.BoxGeometry(1.06, 1.06, 1.06), new T.MeshBasicMaterial({ color: 0xff3355, transparent: true, opacity: 0.45, depthTest: false }));
      m.position.set(h.x + 0.5, h.y + 0.5, h.z + 0.5); m.renderOrder = 20; markGroup.add(m);
      markGroup.add(Object.assign(label(String(marks.length), h.x + 0.5, h.y + 2, h.z + 0.5, 1.5), {}));
      $('marks').textContent = marks.map((m, i) => `${i + 1}. (${m.x}, ${m.y}, ${m.z}) ${P[m.id].n}`).join('\n');
    }
    $('gx').value = h.x; $('gy').value = h.y; $('gz').value = h.z;
  }
  $('copyMarks').onclick = () => navigator.clipboard.writeText($('marks').textContent);
  $('clearMarks').onclick = () => { marks.length = 0; markGroup.clear(); $('marks').textContent = ''; };

  function status() {
    let s = '';
    if (mode === 'walk') s = `你的位置 (${Math.floor(eye.x)}, ${Math.floor(eye.y - 1.62)}, ${Math.floor(eye.z)})　朝向 ${Math.round(((walkYaw * 180 / Math.PI) % 360 + 540) % 360 - 180)}°　速度 ${walkSpeed.toFixed(0)}　`;
    $('status').textContent = s + (hoverText ? '游標指著 ' + hoverText : '把游標移到方塊上可以看座標和名稱');
  }

  function goWalk(x, y, z, yawDeg, pitchDeg) {
    eye.set(x + 0.5, y + 1.62, z + 0.5);
    walkYaw = (yawDeg || 0) * Math.PI / 180; walkPitch = (pitchDeg || 0) * Math.PI / 180;
    setMode('walk'); status();
  }
  $('vOrbit').onclick = () => {
    if (mode === 'walk') { target.copy(eye); dist = 25; yaw = -walkYaw + Math.PI; pitch = 0.5; }
    setMode('orbit');
  };
  $('vWalk').onclick = () => {
    if (mode === 'orbit') { eye.copy(persp.position); walkYaw = Math.atan2(-(target.x - eye.x), target.z - eye.z); walkPitch = -Math.atan2(target.y - eye.y, Math.hypot(target.x - eye.x, target.z - eye.z)); }
    setMode('walk'); status();
  };
  $('vTop').onclick = () => { if (mode === 'orbit') topCenter.set(target.x, 0, target.z); else if (mode === 'walk') topCenter.set(eye.x, 0, eye.z); setMode('top'); };
  $('vReset').onclick = () => { target.set(OX + SX / 2, OY + 14, OZ + SZ / 2); yaw = -35 * Math.PI / 180; pitch = 48 * Math.PI / 180; dist = 215; setMode('orbit'); };
  $('go').onclick = () => goWalk(+$('gx').value, +$('gy').value, +$('gz').value, walkYaw * 180 / Math.PI, 10);
  for (const pt of D.points) {
    const b = document.createElement('button');
    b.textContent = `${pt.name}　(${pt.p.join(', ')})`;
    b.onclick = () => { allBtn.onclick(); goWalk(pt.p[0], pt.p[1], pt.p[2], pt.yaw, pt.pitch); };
    $('points').appendChild(b);
  }
  $('hide').onclick = () => { const p = $('panel'); const h = p.style.display === 'none'; p.style.display = h ? '' : 'none'; $('hide').textContent = h ? '收起面板' : '展開面板'; $('hide').style.left = h ? '322px' : '10px'; };

  document.title = `${D.title} 3D 模型`;
  $('title').textContent = `${D.title} 3D 模型`;
  $('pointsTitle').textContent = D.pointsTitle;
  if (!D.points.length) $('pointsTitle').style.display = 'none';
  $('subtitle').textContent = `世界 ${D.world}（${D.saved} 的存檔），X ${OX}～${OX + SX - 1}、Y ${OY}～${OY + SY - 1}、Z ${OZ}～${OZ + SZ - 1}`;

  // ── 動畫迴圈 ──
  let last = performance.now();
  function frame(now) {
    const dt = Math.min(0.1, (now - last) / 1000); last = now;
    if (keys.size) {
      const f = (keys.has('w') ? 1 : 0) - (keys.has('s') ? 1 : 0), r = (keys.has('d') ? 1 : 0) - (keys.has('a') ? 1 : 0);
      const u = (keys.has(' ') || keys.has('e') ? 1 : 0) - (keys.has('q') ? 1 : 0);
      if (mode === 'walk') {
        const fx = -Math.sin(walkYaw), fz = Math.cos(walkYaw);
        eye.x += (fx * f - fz * r) * walkSpeed * dt; eye.z += (fz * f + fx * r) * walkSpeed * dt; eye.y += u * walkSpeed * dt;
        status();
      } else if (mode === 'orbit') {
        const s = dist * 0.8 * dt;
        const right = new T.Vector3(Math.cos(yaw), 0, -Math.sin(yaw)), fwd = new T.Vector3(-Math.sin(yaw), 0, -Math.cos(yaw));
        target.addScaledVector(fwd, f * s).addScaledVector(right, r * s); target.y += u * s;
      } else {
        topCenter.x += r * 60 / topZoom * dt * 10; topCenter.z -= f * 60 / topZoom * dt * 10;
      }
    }
    updateCamera();
    renderer.render(scene, camera);
    requestAnimationFrame(frame);
  }
  setMode('orbit');
  roofBtn.onclick();
  status();
  $('loading').style.display = 'none';
  requestAnimationFrame(frame);
  // 給測試用：從外面控制相機
  // 給截圖程式與除錯用：從外面控制相機（yaw、pitch 用 Minecraft 的定義）
  window.MODEL_VIEW = { goWalk, setMode, applyRange, hi, lo, get mode() { return mode; }, orbit: (ty, tp, td, tx, tyy, tz) => { yaw = ty; pitch = tp; dist = td; if (tx !== undefined) target.set(tx, tyy, tz); setMode('orbit'); }, top: (x, z, zoom) => { topCenter.set(x, 0, z); topZoom = zoom; setMode('top'); }, render: () => { updateCamera(); renderer.render(scene, camera); } };
})().catch((e) => { document.getElementById('loading').textContent = '載入失敗：' + e.message; console.error(e); });
