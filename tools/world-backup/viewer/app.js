// 雲端地圖的檢視網頁：讀取 data/index.json 與每次備份的清單，用 Leaflet 顯示 uNmINeD 的圖磚。
//
// 座標：遊戲的 X（東西）對應地圖的橫軸，Z（南北）對應縱軸，北方在上。
// Leaflet 的 CRS.Simple 在 zoom 0 時 1 單位 = 1 像素，和 uNmINeD 的 zoom 0（1 格 1 像素）一致，
// 所以 Leaflet 的圖磚編號和 uNmINeD 的圖磚編號完全相同，只要把方塊座標 (x, z) 對到 LatLng(-z, x)。

/* global L */

const DATA = 'data/';
const EMPTY_TILE = 'data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==';
const TILE_SIZE = 256;
/** 海水的顏色。世界範圍外也填這個顏色，手機上才不會有黑邊，也看不出世界主體的方形邊界 */
const SEA = '#0849ab';
/** 第一次打開時框住的範圍（方塊座標）：四座主要的島。海面比島大很多，框整個海面的話手機上島會太小 */
const HOME = { minX: -5000, maxX: 6000, minZ: -6200, maxZ: 5000 };

const get = (/** @type {string} */ id) => /** @type {HTMLElement} */ (document.getElementById(id));
const els = {
  map: get('map'),
  x: get('x'),
  z: get('z'),
  save: get('save'),
  zoomIn: get('zoom-in'),
  zoomOut: get('zoom-out'),
  open: get('open'),
  current: get('current'),
  scrim: get('scrim'),
  sheet: get('sheet'),
  head: get('sheet-head'),
  list: get('list'),
  snackbar: get('snackbar'),
  message: get('message'),
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
const formatDay = (iso) => new Date(iso).toLocaleDateString('zh-TW', { year: 'numeric', month: 'long', day: 'numeric' });
/** @param {string} iso */
const formatTime = (iso) => new Date(iso).toLocaleTimeString('zh-TW', { hour: '2-digit', minute: '2-digit', hour12: false });

/**
 * 把備份依日期分組（清單已經是新的在前）。
 * @param {{ createdAt: string }[]} snapshots
 * @returns {[string, any[]][]}
 */
function groupByDay(snapshots) {
  /** @type {Map<string, any[]>} */
  const days = new Map();
  for (const s of snapshots) {
    const day = formatDay(s.createdAt);
    days.set(day, [...(days.get(day) ?? []), s]);
  }
  return [...days];
}

/** @param {any} manifest */
function zoomLevels(manifest) {
  return Object.keys(manifest.tiles)
    .map(Number)
    .filter((z) => Object.keys(manifest.tiles[z]).length > 0)
    .sort((a, b) => a - b);
}

/** @param {number} x @param {number} z */
const toLatLng = (x, z) => L.latLng(-z, x);
/** @param {L.LatLng} latlng */
const toBlock = (latlng) => ({ x: Math.floor(latlng.lng), z: Math.floor(-latlng.lat) });

/** @param {boolean} open */
function setSheet(open) {
  els.sheet.style.transform = '';
  els.sheet.classList.remove('dragging');
  els.sheet.classList.toggle('open', open);
  els.scrim.classList.toggle('open', open);
}

// 往下拖關掉面板：手指和面板一起動，放手時看拖了多遠和多快
els.head.addEventListener('pointerdown', (event) => {
  els.head.setPointerCapture(event.pointerId);
  const startY = event.clientY;
  let history = [{ y: event.clientY, t: event.timeStamp }];
  const move = (/** @type {PointerEvent} */ e) => {
    history = [...history.slice(-4), { y: e.clientY, t: e.timeStamp }];
    els.sheet.classList.add('dragging');
    els.sheet.style.transform = `translateY(${Math.max(0, e.clientY - startY)}px)`;
  };
  const end = (/** @type {PointerEvent} */ e) => {
    els.head.removeEventListener('pointermove', move);
    els.head.removeEventListener('pointerup', end);
    els.head.removeEventListener('pointercancel', end);
    const first = history[0];
    const last = history[history.length - 1];
    const speed = (last.y - first.y) / Math.max(last.t - first.t, 1);
    setSheet(!(e.clientY - startY > els.sheet.offsetHeight / 3 || speed > 0.6));
  };
  els.head.addEventListener('pointermove', move);
  els.head.addEventListener('pointerup', end);
  els.head.addEventListener('pointercancel', end);
});

let snackbarTimer = 0;
/** @param {string} text */
function snackbar(text) {
  els.snackbar.textContent = text;
  els.snackbar.classList.add('show');
  document.body.classList.add('has-snackbar');
  clearTimeout(snackbarTimer);
  snackbarTimer = window.setTimeout(() => {
    els.snackbar.classList.remove('show');
    document.body.classList.remove('has-snackbar');
  }, 3000);
}

// 水波：從手指按下的位置擴散
document.addEventListener('pointerdown', (event) => {
  const host = /** @type {HTMLElement | null} */ (/** @type {Element} */ (event.target).closest?.('.ripple'));
  if (!host) return;
  const rect = host.getBoundingClientRect();
  const size = Math.hypot(rect.width, rect.height) * 2;
  const wave = document.createElement('span');
  wave.className = 'wave';
  wave.style.cssText = `width:${size}px;height:${size}px;left:${event.clientX - rect.left - size / 2}px;top:${event.clientY - rect.top - size / 2}px`;
  wave.addEventListener('animationend', () => wave.remove());
  host.append(wave);
});

async function main() {
  const index = await getJson('index.json', true);
  const snapshots = index.snapshots ?? [];
  if (snapshots.length === 0) {
    showMessage('雲端還沒有任何備份的地圖。執行一次 backup.bat 之後就會出現。');
    return;
  }

  const initial = readHash();
  let current = snapshots.some((/** @type {any} */ s) => s.id === initial.snapshot) ? initial.snapshot : snapshots[0].id;
  let manifest = await getJson(`snapshots/${current}.json`);

  const levels = zoomLevels(manifest);
  const minNative = levels[0];
  const maxNative = levels[levels.length - 1];
  els.map.style.background = SEA;

  // 拖曳範圍限制在世界主體（清單裡的第一塊區域）再往外一點。外面是一片海，網址又記著位置，
  // 滑太遠的話連重新整理都回不來；限制之後只要縮小就看得到島。遠處的零星區域網頁上到不了，MCP 還查得到
  const world = manifest.areas[0];
  const map = L.map(els.map, {
    crs: L.CRS.Simple,
    minZoom: minNative,
    maxZoom: maxNative + 3, // 超過原始解析度時直接放大像素
    zoomSnap: 1,
    maxBounds: L.latLngBounds(toLatLng(world.minX, world.maxZ), toLatLng(world.maxX, world.minZ)).pad(0.3),
    maxBoundsViscosity: 1,
    attributionControl: false,
    zoomControl: false, // 手機用雙指，電腦才顯示自己的放大縮小按鈕
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
    keepBuffer: 4,
    errorTileUrl: EMPTY_TILE,
  });
  layer.addTo(map);

  // 第一次打開看四座主要的島；分享連結或書籤帶著位置時，就到那個位置
  if (initial.x !== undefined && initial.z !== undefined) {
    map.setView(toLatLng(initial.x, initial.z), Math.min(maxNative + 3, Math.max(minNative, initial.zoom ?? 0)));
  } else {
    map.fitBounds(L.latLngBounds(toLatLng(HOME.minX, HOME.maxZ), toLatLng(HOME.maxX, HOME.minZ)));
  }
  els.zoomIn.addEventListener('click', () => map.zoomIn());
  els.zoomOut.addEventListener('click', () => map.zoomOut());

  // 存成圖片：把畫面上的圖磚畫到同一張畫布。圖磚和網頁同一個網址，畫布才能輸出
  const saveImage = async () => {
    if (layer.isLoading()) await new Promise((resolve) => layer.once('load', resolve));
    const box = els.map.getBoundingClientRect();
    const scale = window.devicePixelRatio || 1;
    const canvas = document.createElement('canvas');
    canvas.width = Math.round(box.width * scale);
    canvas.height = Math.round(box.height * scale);
    const ctx = /** @type {CanvasRenderingContext2D} */ (canvas.getContext('2d'));
    ctx.imageSmoothingEnabled = false; // 和畫面一樣保持方塊的邊緣清楚
    ctx.fillStyle = SEA;
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    // 縮放中可能留著別的等級的圖磚墊在底下，照畫面的上下順序畫
    const tileLevels = [...els.map.querySelectorAll('.leaflet-tile-container')].sort((a, b) => Number(getComputedStyle(a).zIndex) - Number(getComputedStyle(b).zIndex));
    for (const level of tileLevels) {
      for (const tile of level.querySelectorAll('img.leaflet-tile-loaded')) {
        const r = tile.getBoundingClientRect();
        // 四個邊各自取整數，相鄰的圖磚才不會有縫
        const left = Math.round((r.left - box.left) * scale);
        const top = Math.round((r.top - box.top) * scale);
        ctx.drawImage(/** @type {HTMLImageElement} */ (tile), left, top, Math.round((r.right - box.left) * scale) - left, Math.round((r.bottom - box.top) * scale) - top);
      }
    }
    const blob = await new Promise((resolve) => canvas.toBlob(resolve, 'image/png'));
    if (!blob) throw new Error('圖片太大，存不了。');
    const center = toBlock(map.getCenter());
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = `asuka-map-${current}-X${center.x}-Z${center.z}.png`;
    link.click();
    setTimeout(() => URL.revokeObjectURL(link.href), 60000);
  };
  els.save.addEventListener('click', async () => {
    els.save.classList.add('busy');
    try {
      await saveImage();
      navigator.vibrate?.(12);
      snackbar('已存成圖片');
    } catch (error) {
      showMessage(error instanceof Error ? error.message : String(error));
    } finally {
      els.save.classList.remove('busy');
    }
  });

  // 移動地圖時主要按鈕收成圖示，停下來一下子再展開
  let expandTimer = 0;
  map.on('dragstart zoomstart', () => {
    clearTimeout(expandTimer);
    els.save.classList.add('collapsed');
  });
  map.on('moveend zoomend', () => {
    clearTimeout(expandTimer);
    expandTimer = window.setTimeout(() => els.save.classList.remove('collapsed'), 1200);
  });

  // 座標顯示：滑鼠在地圖上時顯示游標位置，否則（例如手機）顯示畫面中央十字的位置
  const showCoords = (/** @type {{ x: number, z: number }} */ p) => {
    els.x.textContent = String(p.x);
    els.z.textContent = String(p.z);
  };
  const onMove = () => {
    const center = toBlock(map.getCenter());
    showCoords(center);
    writeHash({ snapshot: current, ...center, zoom: map.getZoom() });
  };
  map.on('moveend zoomend', onMove);
  map.on('mousemove', (e) => showCoords(toBlock(e.latlng)));
  map.on('mouseout', () => showCoords(toBlock(map.getCenter())));
  onMove();

  // 備份清單
  const latest = snapshots[0].id;
  const rows = new Map();
  const markCurrent = () => {
    for (const [id, row] of rows) row.setAttribute('aria-current', String(id === current));
    const s = snapshots.find((/** @type {any} */ item) => item.id === current);
    els.current.textContent = `${formatDay(s.createdAt)} ${formatTime(s.createdAt)}${s.id === latest ? '・最新' : ''}`;
  };

  /** @param {string} id */
  const switchSnapshot = async (id) => {
    if (id === current) return;
    try {
      manifest = await getJson(`snapshots/${id}.json`);
      current = id;
      layer.redraw();
      onMove();
      markCurrent();
    } catch (error) {
      showMessage(error instanceof Error ? error.message : String(error));
    }
  };

  for (const [day, items] of groupByDay(snapshots)) {
    const title = document.createElement('h3');
    title.textContent = day;
    els.list.append(title);
    for (const s of items) {
      const row = document.createElement('button');
      row.type = 'button';
      row.className = 'row ripple';
      const text = document.createElement('span');
      text.className = 'row-text';
      const time = document.createElement('span');
      time.className = 'row-time';
      time.textContent = formatTime(s.createdAt);
      if (s.id === latest) {
        const tag = document.createElement('em');
        tag.textContent = '最新';
        time.append(tag);
      }
      text.append(time);
      if (s.note) {
        const note = document.createElement('span');
        note.className = 'row-note';
        note.textContent = s.note;
        text.append(note);
      }
      row.append(text);
      row.insertAdjacentHTML('beforeend', '<svg class="row-check" viewBox="0 0 24 24" aria-hidden="true"><path d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z"/></svg>');
      row.addEventListener('click', async () => {
        await switchSnapshot(s.id);
        setTimeout(() => setSheet(false), 180); // 先看到選取移過去再收起來
      });
      rows.set(s.id, row);
      els.list.append(row);
    }
  }
  markCurrent();

  els.open.addEventListener('click', () => setSheet(true));
  els.scrim.addEventListener('click', () => setSheet(false));
  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape') setSheet(false);
  });

  // 在同一個分頁貼上別的分享連結（只有 # 後面不同）時，跳到連結裡的位置和備份
  window.addEventListener('hashchange', async () => {
    const next = readHash();
    if (next.snapshot && next.snapshot !== current && snapshots.some((/** @type {any} */ s) => s.id === next.snapshot)) await switchSnapshot(next.snapshot);
    const center = toBlock(map.getCenter());
    const zoom = Math.min(maxNative + 3, Math.max(minNative, next.zoom ?? map.getZoom()));
    map.setView(toLatLng(next.x ?? center.x, next.z ?? center.z), zoom);
  });
}

// 讓手機上的 :active（按下去的回饋）立刻生效
document.addEventListener('touchstart', () => {}, { passive: true });
main().catch((error) => showMessage(error instanceof Error ? error.message : String(error)));
