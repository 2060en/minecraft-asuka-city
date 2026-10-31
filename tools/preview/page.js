// Browser side of the preview renderer. Builds every panel of a sheet with
// three.js and draws them into one canvas so render.mjs can screenshot it.
// Units: 1 unit = 1 texture pixel = 1/16 block. A full block spans 16 units.
import * as THREE from 'three';

// Minecraft-style flat shading per face, in BoxGeometry material order:
// east (+x), west (-x), up (+y), down (-y), south (+z), north (-z).
const FACES = ['east', 'west', 'up', 'down', 'south', 'north'];
const SHADE = { east: 0.6, west: 0.6, up: 1.0, down: 0.5, south: 0.8, north: 0.8 };

const textureCache = new Map();
function loadTexture(url) {
  if (!textureCache.has(url)) {
    textureCache.set(url, new THREE.TextureLoader().loadAsync(url).then((tex) => {
      tex.magFilter = THREE.NearestFilter;
      tex.minFilter = THREE.NearestFilter;
      tex.generateMipmaps = false;
      tex.colorSpace = THREE.SRGBColorSpace;
      return tex;
    }));
  }
  return textureCache.get(url);
}

// Map one face of a BoxGeometry to a Bedrock per-face UV rectangle.
// BoxGeometry face vertices run top-left, top-right, bottom-left, bottom-right
// as seen from outside the box, which matches how Bedrock reads a face.
function setFaceUV(geometry, faceIndex, face, texW, texH) {
  const uv = geometry.attributes.uv;
  const [u, v] = face.uv;
  const [w, h] = face.uv_size;
  const u0 = u / texW, u1 = (u + w) / texW;
  const vTop = 1 - v / texH, vBottom = 1 - (v + h) / texH;
  const base = faceIndex * 4;
  uv.setXY(base + 0, u0, vTop);
  uv.setXY(base + 1, u1, vTop);
  uv.setXY(base + 2, u0, vBottom);
  uv.setXY(base + 3, u1, vBottom);
}

function shadedMaterial(face, opts) {
  const s = SHADE[face];
  return new THREE.MeshBasicMaterial({
    ...opts,
    color: new THREE.Color(s, s, s).multiply(new THREE.Color(opts.tint ?? '#ffffff')),
    transparent: true,
    alphaTest: 0.1,
  });
}

function boxMesh(origin, size, materials) {
  const [w, h, d] = size.map((x) => Math.max(x, 0.001));
  const geometry = new THREE.BoxGeometry(w, h, d);
  const mesh = new THREE.Mesh(geometry, materials);
  mesh.position.set(origin[0] + w / 2, origin[1] + h / 2, origin[2] + d / 2);
  return mesh;
}

// A plain coloured cube, used for context such as a table or the floor.
function buildBlock(obj) {
  const size = obj.size ?? [16, 16, 16];
  const origin = obj.origin ?? [-size[0] / 2, -size[1], -size[2] / 2];
  const colors = typeof obj.color === 'string' ? Object.fromEntries(FACES.map((f) => [f, obj.color])) : obj.color;
  const materials = FACES.map((f) => shadedMaterial(f, { tint: colors[f] ?? '#888888' }));
  return boxMesh(origin, size, materials);
}

// A Bedrock geometry file (format 1.12.0+) with per-face UVs.
// `bones` limits the render to those bones and their children.
async function buildGeo(obj) {
  const json = await (await fetch(obj.geo)).json();
  const geos = json['minecraft:geometry'];
  const g = obj.identifier ? geos.find((x) => x.description.identifier === obj.identifier) : geos[0];
  const texW = g.description.texture_width;
  const texH = g.description.texture_height;
  const texture = await loadTexture(obj.texture);
  const parents = Object.fromEntries(g.bones.map((b) => [b.name, b.parent]));
  const wanted = (name) => {
    if (!obj.bones) return true;
    for (let n = name; n; n = parents[n]) if (obj.bones.includes(n)) return true;
    return false;
  };
  const group = new THREE.Group();
  for (const bone of g.bones) {
    if (!wanted(bone.name)) continue;
    for (const cube of bone.cubes ?? []) {
      const geometry = new THREE.BoxGeometry(...cube.size.map((x) => Math.max(x, 0.001)));
      const materials = FACES.map((f, i) => {
        const face = cube.uv?.[f];
        if (!face) return new THREE.MeshBasicMaterial({ visible: false });
        setFaceUV(geometry, i, face, texW, texH);
        return shadedMaterial(f, { map: texture });
      });
      const mesh = new THREE.Mesh(geometry, materials);
      const [w, h, d] = cube.size;
      mesh.position.set(cube.origin[0] + w / 2, cube.origin[1] + h / 2, cube.origin[2] + d / 2);
      if (cube.rotation) {
        // Rotate around the cube's pivot (degrees, applied Z, Y, X).
        const pivot = new THREE.Vector3(...(cube.pivot ?? [0, 0, 0]));
        const holder = new THREE.Group();
        holder.position.copy(pivot);
        holder.rotation.set(...cube.rotation.map((a) => THREE.MathUtils.degToRad(a)), 'ZYX');
        mesh.position.sub(pivot);
        holder.add(mesh);
        group.add(holder);
      } else {
        group.add(mesh);
      }
    }
  }
  return group;
}

function makeCamera(cam, aspect) {
  const size = cam.size ?? 24;
  const camera = new THREE.OrthographicCamera(-size * aspect / 2, size * aspect / 2, size / 2, -size / 2, -1000, 1000);
  const az = THREE.MathUtils.degToRad(cam.azimuth ?? 35);
  const el = THREE.MathUtils.degToRad(cam.elevation ?? 30);
  const target = new THREE.Vector3(...(cam.target ?? [0, 4, 0]));
  // Azimuth 0 looks from the south (+z); 90 looks from the east (+x).
  const dir = new THREE.Vector3(Math.sin(az) * Math.cos(el), Math.sin(el), Math.cos(az) * Math.cos(el));
  camera.position.copy(target).addScaledVector(dir, 100);
  camera.lookAt(target);
  return camera;
}

async function buildScene(panel) {
  const scene = new THREE.Scene();
  for (const obj of panel.objects ?? []) {
    let node;
    if (obj.type === 'block') node = buildBlock(obj);
    else if (obj.type === 'geo') node = await buildGeo(obj);
    else throw new Error(`unknown object type: ${obj.type}`);
    if (obj.position) node.position.add(new THREE.Vector3(...obj.position));
    if (obj.rotationY) node.rotation.y = THREE.MathUtils.degToRad(obj.rotationY);
    scene.add(node);
  }
  return scene;
}

export async function renderSheet(sheet) {
  const cols = sheet.columns ?? sheet.panels.length;
  const rows = Math.ceil(sheet.panels.length / cols);
  const pw = sheet.panelWidth ?? 320;
  const ph = sheet.panelHeight ?? 320;
  const titleH = sheet.title ? 48 : 0;
  const labelH = 36;
  const width = cols * pw;
  const height = titleH + rows * (ph + labelH);

  const root = document.getElementById('sheet');
  root.style.width = `${width}px`;
  root.style.height = `${height}px`;
  root.style.background = sheet.background ?? '#eef1f4';

  const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true, preserveDrawingBuffer: true });
  renderer.setPixelRatio(1);
  renderer.setSize(width, height);
  renderer.setScissorTest(true);
  renderer.setClearColor(0x000000, 0);
  renderer.domElement.style.position = 'absolute';
  renderer.domElement.style.left = '0';
  renderer.domElement.style.top = '0';
  root.appendChild(renderer.domElement);

  if (sheet.title) {
    const t = document.createElement('div');
    t.className = 'title';
    t.textContent = sheet.title;
    root.appendChild(t);
  }

  for (const [i, panel] of sheet.panels.entries()) {
    const c = i % cols;
    const r = Math.floor(i / cols);
    const x = c * pw;
    const yTop = titleH + r * (ph + labelH);
    const scene = await buildScene(panel);
    const camera = makeCamera(panel.camera ?? {}, pw / ph);
    // WebGL viewports count from the bottom edge.
    const yGL = height - yTop - ph;
    renderer.setViewport(x, yGL, pw, ph);
    renderer.setScissor(x, yGL, pw, ph);
    renderer.render(scene, camera);

    const label = document.createElement('div');
    label.className = 'label';
    label.style.left = `${x}px`;
    label.style.top = `${yTop + ph}px`;
    label.style.width = `${pw}px`;
    label.textContent = panel.label ?? '';
    root.appendChild(label);
  }
  return { width, height };
}
