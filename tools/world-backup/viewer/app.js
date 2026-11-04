// 雲端地圖的檢視網頁：讀取 data/index.json 與每次備份的清單，用 Leaflet 顯示 uNmINeD 的圖磚。
//
// 座標：遊戲的 X（東西）對應地圖的橫軸，Z（南北）對應縱軸，北方在上。
// Leaflet 的 CRS.Simple 在 zoom 0 時 1 單位 = 1 像素，和 uNmINeD 的 zoom 0（1 格 1 像素）一致，
// 所以 Leaflet 的圖磚編號和 uNmINeD 的圖磚編號完全相同，只要把方塊座標 (x, z) 對到 LatLng(-z, x)。

/* global L */

const DATA = 'data/';
const EMPTY_TILE = 'data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==';
const TILE_SIZE = 256;

const els = {
  title: /** @type {HTMLElement} */ (document.getElementById('title')),
  select: /** @type {HTMLSelectElement} */ (document.getElementById('snapshot')),
  coords: /** @type {HTMLOutputElement} */ (document.getElementById('coords')),
  message: /** @type {HTMLElement} */ (document.getElementById('message')),
  crosshair: /** @type {HTMLElement} */ (document.getElementById('crosshair')),
  map: /** @type {HTMLElement} */ (document.getElementById('map')),
};

/** @param {string} text */
function showMessage(text) {
  els.message.textContent = text;
  els.message.hidden = false;
}

/**
 * @param {string} path
 * @param {boolean} [fresh] 不用快取（index.json 每次備份都會變）
 */
async function getJson(path, fresh = false) {
  const response = await fetch(DATA + path, fresh ? { cache: 'no-cache' } : {});
  if (response.status === 403 || response.status === 503) throw new Error(await response.text());
  if (!response.ok) throw new Error(`讀取 ${path} 失敗（${response.status}）`);
  return response.json();
}

/** 網址 # 後面的狀態：s=備份、x、z、zoom */
function readHash() {
  const params = new URLSearchParams(location.hash.slice(1));
  const num = (/** @type {string} */ key) => {
    const v = params.get(key);
    return v !== null && v !== '' && Number.isFinite(Number(v)) ? Number(v) : undefined;
  };
  return { snapshot: params.get('s') ?? undefined, x: num('x'), z: num('z'), zoom: num('zoom') };
}

/** @param {{ snapshot: string, x: number, z: number, zoom: number }} state */
function writeHash(state) {
  const params = new URLSearchParams({ s: state.snapshot, x: String(Math.round(state.x)), z: String(Math.round(state.z)), zoom: String(state.zoom) });
  history.replaceState(null, '', `#${params}`);
}

/** @param {string} iso */
function formatDate(iso) {
  return new Date(iso).toLocaleString('zh-TW', { year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', hour12: false });
}

/** @param {any} manifest */
function zoomLevels(manifest) {
  return Object.keys(manifest.tiles)
    .map(Number)
    .filter((z) => Object.keys(manifest.tiles[z]).length > 0)
    .sort((a, b) => a - b);
}

/** 地圖涵蓋的範圍（方塊座標），用最接近 zoom 0 的等級計算 */
function mapExtent(manifest) {
  const levels = zoomLevels(manifest);
  const zoom = levels.reduce((best, z) => (Math.abs(z) < Math.abs(best) ? z : best), levels[0]);
  const size = TILE_SIZE / 2 ** zoom;
  let minX = Infinity;
  let minZ = Infinity;
  let maxX = -Infinity;
  let maxZ = -Infinity;
  for (const key of Object.keys(manifest.tiles[zoom])) {
    const [x, y] = key.split(',').map(Number);
    minX = Math.min(minX, x * size);
    minZ = Math.min(minZ, y * size);
    maxX = Math.max(maxX, (x + 1) * size);
    maxZ = Math.max(maxZ, (y + 1) * size);
  }
  return { minX, minZ, maxX, maxZ };
}

/** @param {number} x @param {number} z */
const toLatLng = (x, z) => L.latLng(-z, x);
/** @param {L.LatLng} latlng */
const toBlock = (latlng) => ({ x: Math.floor(latlng.lng), z: Math.floor(-latlng.lat) });

async function main() {
  const index = await getJson('index.json', true);
  const snapshots = index.snapshots ?? [];
  if (snapshots.length === 0) {
    showMessage('雲端還沒有任何備份的地圖。執行一次 backup.bat 之後就會出現。');
    return;
  }

  for (const s of snapshots) {
    const option = document.createElement('option');
    option.value = s.id;
    option.textContent = `${formatDate(s.createdAt)}${s.note ? `　${s.note}` : ''}`;
    els.select.append(option);
  }

  const initial = readHash();
  let current = snapshots.some((s) => s.id === initial.snapshot) ? initial.snapshot : snapshots[0].id;
  els.select.value = current;
  let manifest = await getJson(`snapshots/${current}.json`);

  const levels = zoomLevels(manifest);
  const props = manifest.properties ?? {};
  if (props.worldName) els.title.textContent = String(props.worldName);
  if (props.background) els.map.style.background = String(props.background);

  const minNative = levels[0];
  const maxNative = levels[levels.length - 1];
  const extent = mapExtent(manifest);
  const bounds = L.latLngBounds(toLatLng(extent.minX, extent.maxZ), toLatLng(extent.maxX, extent.minZ));

  const map = L.map(els.map, {
    crs: L.CRS.Simple,
    minZoom: minNative,
    maxZoom: maxNative + 3, // 超過原始解析度時直接放大像素
    zoomSnap: 1,
    attributionControl: false,
    maxBounds: bounds.pad(0.5),
    maxBoundsViscosity: 0.8,
  });

  const MapLayer = L.TileLayer.extend({
    /** @param {L.Coords} coords */
    getTileUrl(coords) {
      const hash = manifest.tiles[coords.z]?.[`${coords.x},${coords.y}`];
      return hash ? `${DATA}tiles/${hash.slice(0, 2)}/${hash}.${manifest.ext}` : EMPTY_TILE;
    },
  });
  const layer = new MapLayer('', {
    tileSize: TILE_SIZE,
    minNativeZoom: minNative,
    maxNativeZoom: maxNative,
    minZoom: minNative,
    maxZoom: maxNative + 3,
    noWrap: true,
    bounds,
    keepBuffer: 4,
    errorTileUrl: EMPTY_TILE,
  });
  layer.addTo(map);

  const startZoom = Math.min(maxNative + 3, Math.max(minNative, initial.zoom ?? Number(props.defaultZoom ?? 0)));
  const startX = initial.x ?? Number(props.centerX ?? (extent.minX + extent.maxX) / 2);
  const startZ = initial.z ?? Number(props.centerZ ?? (extent.minZ + extent.maxZ) / 2);
  map.setView(toLatLng(startX, startZ), startZoom);

  // 座標顯示：滑鼠在地圖上時顯示游標位置，否則（例如手機）顯示畫面中央十字的位置
  const showCoords = (/** @type {{ x: number, z: number }} */ p) => {
    els.coords.textContent = `X ${p.x}　Z ${p.z}`;
  };
  const placeCrosshair = () => {
    const rect = els.map.getBoundingClientRect();
    els.crosshair.style.top = `${rect.top + rect.height / 2}px`;
  };
  const onMove = () => {
    const center = map.getCenter();
    showCoords(toBlock(center));
    writeHash({ snapshot: current, ...toBlock(center), zoom: map.getZoom() });
  };
  map.on('moveend zoomend', onMove);
  map.on('mousemove', (e) => showCoords(toBlock(e.latlng)));
  map.on('mouseout', () => showCoords(toBlock(map.getCenter())));
  window.addEventListener('resize', placeCrosshair);
  placeCrosshair();
  onMove();

  /** @param {string} id */
  const switchSnapshot = async (id) => {
    if (id === current) return;
    try {
      manifest = await getJson(`snapshots/${id}.json`);
      current = id;
      els.select.value = id;
      layer.redraw();
      onMove();
    } catch (error) {
      showMessage(error instanceof Error ? error.message : String(error));
      els.select.value = current;
    }
  };
  els.select.addEventListener('change', () => switchSnapshot(els.select.value));

  // 在同一個分頁貼上別的分享連結（只有 # 後面不同）時，跳到連結裡的位置和備份
  window.addEventListener('hashchange', async () => {
    const next = readHash();
    if (next.snapshot && next.snapshot !== current && snapshots.some((s) => s.id === next.snapshot)) await switchSnapshot(next.snapshot);
    const center = toBlock(map.getCenter());
    const zoom = Math.min(maxNative + 3, Math.max(minNative, next.zoom ?? map.getZoom()));
    map.setView(toLatLng(next.x ?? center.x, next.z ?? center.z), zoom);
  });
}

main().catch((error) => showMessage(error instanceof Error ? error.message : String(error)));
