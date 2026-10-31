// Covermood-Editor: Stellen im Cover je Licht, Farbstil, Bewegung, Einschränkungen. Ohne Build, ohne Abhängigkeiten.
// Jede Änderung wirkt sofort auf die Vorschau und – nach kurzer Pause – auf die Lichter; gespeichert wird von selbst.
const MIN = 0.03;
const STRUCTURAL = ["source", "mode", "style", "bri_mode", "default_color"]; // ändern, was zu sehen ist – sonst genügt der Wert
const HUES = [200, 35, 140, 330, 60, 270, 10, 170, 100, 300, 230, 80];
const GATE_DOMAINS = ["input_boolean", "switch", "binary_sensor", "light"];
const T = {
  de: {
    room: "Raum",
    idle: "Nichts spielt – gezeigt wird das letzte Cover.",
    nocover: "Noch kein Cover. Starte Musik in diesem Raum – sobald ein Titel ein Cover hat, erscheint es hier und wechselt mit jedem Titel.",
    norooms: "Es ist noch kein Raum eingerichtet.",
    hint: "Ziehe jedes Rechteck auf die Stelle, deren Farbe das Licht bekommen soll; das Quadrat unten rechts ändert die Größe. Ersatzpunkte (gestrichelt) greifen, wenn der Hauptpunkt gerade schwarz ist.",
    needpoints: "Für freie Stellen im Cover wähle bei „Farben aus dem Cover“ die Option „Eigene Punkte“.",
    bulbs: "Vorschau: so leuchten die Leuchtmittel im Raum",
    lights: "Lichter und Stellen im Cover",
    source: "Farben aus dem Cover",
    sources: { palette: "Automatisch", zones: "Zonen", regions: "Eigene Punkte" },
    points: "Anzahl Farben",
    main: "Hauptpunkt",
    alt: "Ersatzpunkt",
    addalt: "+ Ersatzpunkt",
    del: "Entfernen",
    fallback: "Alle Punkte zu dunkel – nimmt eine prägende Farbe des Covers.",
    nocolor: "Cover ganz dunkel – das Licht bleibt, wie es ist.",
    color: "Farbe",
    style: "Stil",
    styles: { vibrant: "Lebendig", pastel: "Pastell", faithful: "Originalgetreu", intense: "Intensiv" },
    styleHints: {
      vibrant: "kräftige, satte Farben",
      pastel: "weich und hell, wenig gesättigt",
      faithful: "so, wie das Cover es zeigt",
      intense: "maximal gesättigt, dramatisch",
    },
    minsat: "Mindestsättigung",
    brimode: "Helligkeit der Lichter",
    brimodes: { keep: "Nicht ändern", fixed: "Fester Wert", cover: "Folgt dem Cover" },
    bri: "Helligkeit",
    brimax: "Höchste Helligkeit",
    brimin: "Mindesthelligkeit",
    motion: "Bewegung",
    mode: "Stimmung",
    modes: { calm: "Ruhig", static: "Statisch", party: "Party" },
    fade: "Überblendzeit bei neuem Cover",
    every: "Farben wandern alle",
    still: "stehen still",
    wanderOff: "Eigene Punkte wandern nicht – jedes Licht behält seine Stelle.",
    limits: "Wann und wie",
    onlySources: "Nur bei diesen Quellen",
    anySource: "Jede Quelle",
    onlyWhile: "Nur solange diese Entität an ist",
    onlyWhilePh: "z. B. input_boolean.party – leer = immer",
    turnOn: "Ausgeschaltete Lichter beim Start einschalten",
    restore: "Lichter danach zurücksetzen",
    defColor: "Standardfarbe am Ende (statt Zurücksetzen)",
    test: "Auf Lichtern testen",
    testing: "Test läuft – die Lichter kehren gleich zurück.",
    reset: "Streifen wiederherstellen",
    saving: "Speichert …",
    saved: "Gespeichert ✓",
    fail: "Fehler",
  },
  en: {
    room: "Room",
    idle: "Nothing is playing – showing the last cover.",
    nocover: "No cover yet. Play music in this room – once a track has cover art it shows up here and changes with every track.",
    norooms: "No room is set up yet.",
    hint: "Drag each rectangle to the spot whose color the light should get; the square at the bottom right resizes it. Backup spots (dashed) take over when the main spot is currently black.",
    needpoints: "To pick spots on the cover, choose “Own points” under “Colors from the cover”.",
    bulbs: "Preview: how the bulbs glow in the room",
    lights: "Lights and spots on the cover",
    source: "Colors from the cover",
    sources: { palette: "Automatic", zones: "Zones", regions: "Own points" },
    points: "Number of colors",
    main: "Main spot",
    alt: "Backup spot",
    addalt: "+ Backup spot",
    del: "Remove",
    fallback: "All spots too dark – uses a dominant color of the cover.",
    nocolor: "Cover is entirely dark – the light stays as it is.",
    color: "Color",
    style: "Style",
    styles: { vibrant: "Vibrant", pastel: "Pastel", faithful: "Faithful", intense: "Intense" },
    styleHints: {
      vibrant: "strong, saturated colors",
      pastel: "soft and light, little saturation",
      faithful: "as the cover shows them",
      intense: "maximum saturation, dramatic",
    },
    minsat: "Minimum saturation",
    brimode: "Brightness of the lights",
    brimodes: { keep: "Leave alone", fixed: "Fixed value", cover: "Follow the cover" },
    bri: "Brightness",
    brimax: "Maximum brightness",
    brimin: "Minimum brightness",
    motion: "Motion",
    mode: "Mood",
    modes: { calm: "Calm", static: "Static", party: "Party" },
    fade: "Fade time on a new cover",
    every: "Colors drift every",
    still: "stand still",
    wanderOff: "Own points don't drift – each light keeps its spot.",
    limits: "When and how",
    onlySources: "Only for these sources",
    anySource: "Any source",
    onlyWhile: "Only while this entity is on",
    onlyWhilePh: "e.g. input_boolean.party – empty = always",
    turnOn: "Switch on lights that are off when music starts",
    restore: "Restore the lights afterwards",
    defColor: "Default color at the end (instead of restoring)",
    test: "Test on lights",
    testing: "Test running – the lights return shortly.",
    reset: "Restore stripes",
    saving: "Saving …",
    saved: "Saved ✓",
    fail: "Error",
  },
};
const esc = (s) => String(s ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[c]);
const clamp = (v, lo, hi) => Math.min(hi, Math.max(lo, v));
const lightColor = (l) => `hsl(${HUES[l % HUES.length]} 90% 60%)`;
const hsToHex = (h, s) => {
  const f = (n) => {
    const k = (n + h / 60) % 6;
    return Math.round(255 * (1 - (s / 100) * Math.max(0, Math.min(k, 4 - k, 1))));
  };
  return "#" + [5, 3, 1].map((n) => f(n).toString(16).padStart(2, "0")).join("");
};
const hexToHs = (hex) => {
  const [r, g, b] = [1, 3, 5].map((i) => parseInt(hex.slice(i, i + 2), 16) / 255);
  const max = Math.max(r, g, b), d = max - Math.min(r, g, b);
  const h = d === 0 ? 0 : max === r ? ((g - b) / d) % 6 : max === g ? (b - r) / d + 2 : (r - g) / d + 4;
  return [Math.round((h * 60 + 360) % 360), Math.round(max === 0 ? 0 : (d / max) * 100)];
};

class CovermoodPanel extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._data = null; // { rooms, modes, max_spots }
    this._i = 0;
    this._s = null; // Einstellungen des gewählten Raums (Arbeitskopie)
    this._sel = 0; // gewähltes Licht
    this._image = null;
    this._now = {};
    this._res = [];
    this._unsub = null;
    this._token = 0;
    this.shadowRoot.addEventListener("input", (e) => this._onInput(e));
    this.shadowRoot.addEventListener("change", (e) => this._onInput(e, true));
    this.shadowRoot.addEventListener("click", (e) => this._onClick(e));
    this.shadowRoot.addEventListener("pointerdown", (e) => this._onDown(e));
    this._open = { lights: true, color: true, motion: true, limits: false }; // welche Abschnitte aufgeklappt sind
    this.shadowRoot.addEventListener("toggle", (e) => (this._open[e.target.dataset.sec] = e.target.open), true);
  }

  // Home Assistant setzt diese Eigenschaften; gebraucht wird hass
  set hass(hass) {
    const first = !this._hass;
    this._hass = hass;
    if (first) this._load();
  }
  set narrow(_) {}
  set panel(_) {}
  set route(_) {}

  connectedCallback() {
    if (this._data && !this._unsub) this._subscribe();
  }
  disconnectedCallback() {
    this._unsubscribe();
  }

  get t() {
    return T[(this._hass?.language || "en").slice(0, 2)] || T.en;
  }
  get room() {
    return this._data?.rooms[this._i];
  }

  async _load() {
    this._data = await this._hass.callWS({ type: "covermood/rooms" });
    await this._select(clamp(this._i, 0, Math.max(0, this._data.rooms.length - 1)));
  }

  async _select(i) {
    this._i = i;
    this._sel = 0;
    this._image = null;
    this._now = {};
    this._res = [];
    this._unsubscribe();
    const room = this.room;
    this._s = room ? structuredClone(room.settings) : null;
    if (this._s) {
      const m = this._data.modes[this._s.mode];
      this._s.fade ??= m.fade; // die Stimmung liefert, was nicht überschrieben ist
      this._s.every ??= m.every;
    }
    this._draw();
    if (room) await this._subscribe();
  }

  // --- Live: Cover und Titel ---

  async _subscribe() {
    const room = this.room;
    if (!room) return;
    const token = ++this._token;
    const unsub = await this._hass.connection.subscribeMessage((ev) => token === this._token && this._onEvent(ev), {
      type: "covermood/subscribe",
      room_id: room.id,
    });
    if (token !== this._token) unsub();
    else this._unsub = unsub;
  }

  _unsubscribe() {
    this._token++;
    this._unsub?.();
    this._unsub = null;
  }

  _onEvent(ev) {
    this._now = ev;
    if ("image" in ev && ev.image !== this._image) {
      const hadImage = !!this._image;
      this._image = ev.image;
      const img = this.shadowRoot.querySelector("#stage img");
      if (hadImage && ev.image && img) img.src = ev.image;
      else this._draw();
      this._preview();
    }
    this._paintNow();
  }

  _paintNow() {
    const el = this.shadowRoot.querySelector(".now");
    if (!el) return;
    const n = this._now;
    el.innerHTML = n.playing
      ? `<i class="dot"></i>${esc(n.title || "")}${n.artist ? ` <span>– ${esc(n.artist)}</span>` : ""}`
      : `<span>${this.t.idle}</span>`;
  }

  // --- Zeichnen ---

  _draw() {
    const t = this.t;
    const rooms = this._data?.rooms || [];
    const room = this.room;
    const s = this._s;
    if (!room) {
      this.shadowRoot.innerHTML = `<style>${CSS}</style><div class="wrap"><p class="hint">${t.norooms}</p></div>`;
      return;
    }
    const regions = s.source === "regions";
    const stage = this._image
      ? `<div class="stage" id="stage"><img src="${this._image}" draggable="false">${regions ? this._boxes() : ""}</div>
         <div class="room" title="${t.bulbs}">${room.lights
           .map((_, l) => `<b class="bulb" data-bulb="${l}" data-n="${l + 1}"></b>`)
           .join("")}</div>
         <p class="hint">${regions ? t.hint : t.needpoints}</p>`
      : `<div class="stage"><div class="empty">${t.nocover}</div></div>`;
    this.shadowRoot.innerHTML = `<style>${CSS}</style>
      <div class="wrap">
        <header>
          <h1>Covermood</h1>
          <select id="room" aria-label="${t.room}">${rooms
            .map((r, i) => `<option value="${i}"${i === this._i ? " selected" : ""}>${esc(r.name)}</option>`)
            .join("")}</select>
          <div class="now" aria-live="polite"></div>
          <span id="msg" role="status"></span>
        </header>
        <div class="grid">
          <section class="main">${stage}</section>
          <aside class="side">
            ${this._secLights()}${this._secColor()}${this._secMotion()}${this._secLimits()}
            <div class="actions">
              <button id="test"${this._image ? "" : " disabled"}>${t.test}</button>
              ${regions ? `<button id="reset" class="plain">${t.reset}</button>` : ""}
            </div>
          </aside>
        </div>
      </div>`;
    this._paintNow();
    this._paintRes();
  }

  _seg(k, options, value) {
    return `<div class="seg" role="group">${Object.entries(options)
      .map(([v, label]) => `<button type="button" data-k="${k}" data-v="${v}" aria-pressed="${v === value}">${esc(label)}</button>`)
      .join("")}</div>`;
  }

  _slider(k, label, min, max, step, dis = false) {
    return `<label class="sl${dis ? " off" : ""}"><span>${label}<b data-v="${k}">${this._fmt(k, this._s[k])}</b></span>
      <input type="range" data-k="${k}" data-t="n" min="${min}" max="${max}" step="${step}" value="${this._s[k]}"${dis ? " disabled" : ""}></label>`;
  }

  _check(k, label) {
    return `<label class="ck"><input type="checkbox" data-k="${k}" data-t="b"${this._s[k] ? " checked" : ""}> ${label}</label>`;
  }

  _fmt(k, v) {
    if (k === "every") return v === 0 ? this.t.still : v >= 60 ? `${Math.round(v / 6) / 10} min` : `${v} s`;
    if (k === "fade") return `${v} s`;
    if (k === "points") return String(v);
    return `${v} %`;
  }

  _secLights() {
    const t = this.t, s = this._s, room = this.room;
    const cards = s.source === "regions"
      ? room.lights
          .map((light, l) => {
            const spots = s.regions[light.entity_id];
            return `<div class="card${l === this._sel ? " sel" : ""}" data-l="${l}" style="--c:${lightColor(l)}">
              <div class="head"><b class="chip" data-chip="${l}"></b><span>${l + 1} · ${esc(light.name)}</span><small data-bri="${l}"></small></div>
              <ul class="spots">${spots
                .map(
                  (_, k) => `<li class="spot"><span>${k ? `${t.alt} ${k}` : t.main}</span>
                    <em data-used="${l}-${k}">✓</em>
                    <button type="button" class="x" data-del="${l}-${k}" title="${t.del}" aria-label="${t.del}"${spots.length < 2 ? " disabled" : ""}>×</button></li>`,
                )
                .join("")}</ul>
              <button type="button" class="plain add" data-add="${l}"${spots.length >= this._data.max_spots ? " disabled" : ""}>${t.addalt}</button>
              <p class="note" data-note="${l}"></p>
            </div>`;
          })
          .join("")
      : `<ul class="plainlist">${room.lights
          .map((light, l) => `<li><b class="chip" data-chip="${l}"></b>${l + 1} · ${esc(light.name)}<small data-bri="${l}"></small></li>`)
          .join("")}</ul>`;
    return `<details data-sec="lights"${this._open.lights ? " open" : ""}><summary>${t.lights}</summary>
      <div class="field"><span>${t.source}</span>${this._seg("source", t.sources, s.source)}</div>
      ${s.source === "regions" ? "" : this._slider("points", t.points, 2, 12, 1)}
      ${cards}</details>`;
  }

  _secColor() {
    const t = this.t, s = this._s;
    return `<details data-sec="color"${this._open.color ? " open" : ""}><summary>${t.color}</summary>
      <div class="field"><span>${t.style}</span>${this._seg("style", t.styles, s.style)}<small>${t.styleHints[s.style]}</small></div>
      ${this._slider("min_sat", t.minsat, 0, 100, 1)}
      <div class="field"><span>${t.brimode}</span>${this._seg("bri_mode", t.brimodes, s.bri_mode)}</div>
      ${s.bri_mode === "keep" ? "" : this._slider("brightness", s.bri_mode === "cover" ? t.brimax : t.bri, 1, 100, 1)}
      ${s.bri_mode === "cover" ? this._slider("min_bri", t.brimin, 1, 100, 1) : ""}</details>`;
  }

  _secMotion() {
    const t = this.t, s = this._s;
    const still = s.source === "regions";
    return `<details data-sec="motion"${this._open.motion ? " open" : ""}><summary>${t.motion}</summary>
      <div class="field"><span>${t.mode}</span>${this._seg("mode", t.modes, s.mode)}</div>
      ${this._slider("fade", t.fade, 0, 30, 0.5)}
      ${this._slider("every", t.every, 0, 120, 1, still)}
      ${still ? `<small class="note">${t.wanderOff}</small>` : ""}</details>`;
  }

  _secLimits() {
    const t = this.t, s = this._s, room = this.room;
    const names = [...new Set([...room.sources, ...s.only_sources])];
    const entities = Object.keys(this._hass?.states || {})
      .filter((id) => GATE_DOMAINS.includes(id.split(".")[0]))
      .sort();
    return `<details data-sec="limits"${this._open.limits ? " open" : ""}><summary>${t.limits}</summary>
      <div class="field"><span>${t.onlySources}</span>${
        names.length
          ? names
              .map((n) => `<label class="ck"><input type="checkbox" data-src="${esc(n)}"${s.only_sources.includes(n) ? " checked" : ""}> ${esc(n)}</label>`)
              .join("")
          : `<small>${t.anySource}</small>`
      }</div>
      <label class="field"><span>${t.onlyWhile}</span>
        <input type="text" list="gate" data-k="only_while" data-t="e" value="${esc(s.only_while || "")}" placeholder="${t.onlyWhilePh}">
        <datalist id="gate">${entities.map((id) => `<option value="${id}">${esc(this._hass.states[id].attributes.friendly_name || "")}</option>`).join("")}</datalist></label>
      ${this._check("turn_on", t.turnOn)}${this._check("restore", t.restore)}
      <label class="ck"><input type="checkbox" data-k="default_on" data-t="b"${s.default_color ? " checked" : ""}> ${t.defColor}</label>
      ${s.default_color ? `<input type="color" data-k="default_color" data-t="c" value="${hsToHex(...s.default_color)}">` : ""}</details>`;
  }

  _boxes() {
    return this.room.lights
      .flatMap((light, l) =>
        this._s.regions[light.entity_id].map(
          (r, k) => `<div class="box${k ? " alt" : ""}${l === this._sel ? " sel" : ""}" data-l="${l}" data-k="${k}" style="--c:${lightColor(l)};${this._rectStyle(r)}">
            <span>${l + 1}${k ? "abcdefgh"[k - 1] : ""}</span><i class="grip"></i></div>`,
        ),
      )
      .join("");
  }

  _rectStyle([x, y, w, h]) {
    return `left:${x * 100}%;top:${y * 100}%;width:${w * 100}%;height:${h * 100}%`;
  }

  // Ergebnis der Vorschau in die schon gezeichneten Elemente eintragen (ohne neu zu zeichnen)
  _paintRes() {
    const $$ = (s) => this.shadowRoot.querySelectorAll(s);
    const t = this.t;
    this._res.forEach((r, l) => {
      $$(`[data-chip="${l}"]`).forEach((el) => (el.style.background = r.color || "transparent"));
      $$(`[data-bulb="${l}"]`).forEach((el) => {
        el.style.setProperty("--c", r.color || "#333");
        el.style.setProperty("--b", (r.bri ?? 100) / 100);
      });
      $$(`[data-bri="${l}"]`).forEach((el) => (el.textContent = r.bri == null ? "" : `${r.bri} %`));
      $$(`[data-note="${l}"]`).forEach((el) => (el.textContent = r.used === -1 ? (r.color ? t.fallback : t.nocolor) : ""));
      $$(`.box[data-l="${l}"]`).forEach((el) => el.classList.toggle("used", +el.dataset.k === r.used));
      $$(`[data-used^="${l}-"]`).forEach((el) => el.classList.toggle("on", +el.dataset.used.split("-")[1] === r.used));
    });
  }

  // --- Bedienung ---

  _onClick(e) {
    const b = e.target.closest("button, .card");
    if (!b) return;
    const { k, v, add, del, l } = b.dataset;
    if (b.id === "test") return this._test();
    if (b.id === "reset") return this._resetStripes();
    if (k && v !== undefined) return this._set(k, v);
    if (add !== undefined) return this._addSpot(+add);
    if (del !== undefined) return this._delSpot(...del.split("-").map(Number));
    if (b.classList.contains("card") && l !== undefined) this._choose(+l);
  }

  _onInput(e, committed = false) {
    const el = e.target;
    if (el.id === "room") return committed && this._select(+el.value);
    if (el.dataset.src !== undefined) {
      if (!committed) return;
      const rest = this._s.only_sources.filter((n) => n !== el.dataset.src);
      return this._set("only_sources", el.checked ? [...rest, el.dataset.src] : rest);
    }
    const { k, t } = el.dataset;
    if (!k || t === undefined) return;
    // Regler laufend, alles andere erst beim Übernehmen
    if ((t === "n") === committed) return;
    if (k === "default_on") return this._set("default_color", el.checked ? [30, 80] : null);
    const value = t === "n" ? +el.value : t === "b" ? el.checked : t === "c" ? hexToHs(el.value) : el.value.trim() || null;
    this._set(k, value, t === "n", t === "c");
  }

  // Ändert eine Einstellung; `live` heißt: nur den Wert neben dem Regler nachführen, `keep`: nichts neu zeichnen
  _set(k, value, live = false, keep = false) {
    this._s[k] = value;
    if (k === "mode") Object.assign(this._s, this._data.modes[value]);
    if (live) this.shadowRoot.querySelector(`[data-v="${k}"]`).textContent = this._fmt(k, value);
    else if (!keep && STRUCTURAL.includes(k)) this._draw();
    this._changed();
  }

  _choose(l) {
    this._sel = l;
    this.shadowRoot.querySelectorAll(".card, .box").forEach((el) => el.classList.toggle("sel", +el.dataset.l === l));
  }

  _spots(l) {
    return this._s.regions[this.room.lights[l].entity_id];
  }

  _addSpot(l) {
    const spots = this._spots(l);
    const n = spots.length;
    spots.push([clamp(0.3 + 0.12 * n, 0, 0.84), clamp(0.3 + 0.1 * n, 0, 0.84), 0.14, 0.14]);
    this._sel = l;
    this._draw();
    this._changed();
  }

  _delSpot(l, k) {
    this._spots(l).splice(k, 1);
    this._draw();
    this._changed();
  }

  _resetStripes() {
    const lights = this.room.lights;
    lights.forEach((light, l) => (this._s.regions[light.entity_id] = [[l / lights.length, 0, 1 / lights.length, 1]]));
    this._draw();
    this._changed();
  }

  _onDown(e) {
    const box = e.target.closest(".box");
    if (!box) return;
    e.preventDefault();
    const [l, k] = [+box.dataset.l, +box.dataset.k];
    this._choose(l);
    const stage = this.shadowRoot.querySelector("#stage").getBoundingClientRect();
    const [x0, y0, w0, h0] = this._spots(l)[k];
    const size = e.target.classList.contains("grip");
    const move = (ev) => {
      const dx = (ev.clientX - e.clientX) / stage.width, dy = (ev.clientY - e.clientY) / stage.height;
      const r = size
        ? [x0, y0, clamp(w0 + dx, MIN, 1 - x0), clamp(h0 + dy, MIN, 1 - y0)]
        : [clamp(x0 + dx, 0, 1 - w0), clamp(y0 + dy, 0, 1 - h0), w0, h0];
      this._spots(l)[k] = r;
      box.style.cssText = `--c:${lightColor(l)};${this._rectStyle(r)}`;
      this._previewSoon();
    };
    const up = () => {
      window.removeEventListener("pointermove", move);
      this._changed();
    };
    window.addEventListener("pointermove", move);
    window.addEventListener("pointerup", up, { once: true });
  }

  // --- Vorschau, Speichern, Test ---

  _changed() {
    this._previewSoon();
    clearTimeout(this._saveTimer);
    this._say(this.t.saving);
    this._saveTimer = setTimeout(() => this._save(), 600);
  }

  _previewSoon() {
    clearTimeout(this._previewTimer);
    this._previewTimer = setTimeout(() => this._preview(), 100);
  }

  async _preview() {
    if (!this.room || !this._image) return;
    try {
      this._res = await this._hass.callWS({ type: "covermood/preview", room_id: this.room.id, settings: this._s });
    } catch (_) {
      return; // Vorschau ist nur Zugabe
    }
    this._paintRes();
  }

  async _save() {
    try {
      await this._hass.callWS({ type: "covermood/update", room_id: this.room.id, settings: this._s });
      this._say(this.t.saved, 2500);
    } catch (err) {
      this._say(`${this.t.fail}: ${err.message || err.code || err}`);
    }
  }

  async _test() {
    const btn = this.shadowRoot.querySelector("#test");
    btn.disabled = true;
    try {
      const { seconds } = await this._hass.callWS({ type: "covermood/test", room_id: this.room.id, settings: this._s });
      this._say(this.t.testing, seconds * 1000);
      setTimeout(() => (btn.disabled = false), seconds * 1000);
    } catch (err) {
      btn.disabled = false;
      this._say(`${this.t.fail}: ${err.message || err.code || err}`);
    }
  }

  _say(text, clearAfter) {
    const msg = this.shadowRoot.querySelector("#msg");
    if (!msg) return;
    msg.textContent = text;
    clearTimeout(this._sayTimer);
    if (clearAfter) this._sayTimer = setTimeout(() => (msg.textContent = ""), clearAfter);
  }
}

const CSS = `
  :host { display: block; min-height: 100%; background: var(--primary-background-color); color: var(--primary-text-color); }
  * { box-sizing: border-box; }
  .wrap { max-width: 1280px; margin: 0 auto; padding: 16px; }
  header { display: flex; flex-wrap: wrap; align-items: center; gap: 8px 16px; margin-bottom: 16px; }
  h1 { font-size: 22px; font-weight: 500; margin: 0; }
  select, input[type=text] { font: inherit; padding: 8px 12px; border-radius: 8px; border: 1px solid var(--divider-color); background: var(--card-background-color); color: inherit; }
  input[type=text] { width: 100%; }
  .now { flex: 1 1 240px; min-width: 0; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .now span, small, .note { color: var(--secondary-text-color); }
  .dot { display: inline-block; width: 8px; height: 8px; margin-right: 8px; border-radius: 50%; background: #4caf50; animation: pulse 1.6s ease-in-out infinite; }
  @keyframes pulse { 50% { opacity: .35; } }
  @media (prefers-reduced-motion: reduce) { .dot { animation: none; } .bulb { transition: none; } }
  #msg { color: var(--secondary-text-color); min-height: 1.2em; }
  .grid { display: grid; grid-template-columns: minmax(0, 1.25fr) minmax(300px, 1fr); gap: 24px; align-items: start; }
  @media (max-width: 900px) { .grid { grid-template-columns: 1fr; } }
  .main { position: sticky; top: 8px; }
  @media (max-width: 900px) { .main { position: static; } }
  .hint { color: var(--secondary-text-color); line-height: 1.4; margin: 12px 0 0; }
  .stage { position: relative; line-height: 0; border-radius: 12px; overflow: hidden; background: var(--card-background-color); user-select: none; -webkit-user-select: none; }
  .stage img { width: 100%; display: block; pointer-events: none; }
  .empty { line-height: 1.5; padding: 64px 24px; text-align: center; color: var(--secondary-text-color); }
  .box { position: absolute; border: 2px solid var(--c); border-radius: 3px; cursor: move; touch-action: none;
    box-shadow: 0 0 0 1px rgba(0,0,0,.7), inset 0 0 0 1px rgba(0,0,0,.7); transition: background .15s; }
  .box.alt { border-style: dashed; }
  .box.sel { background: color-mix(in srgb, var(--c) 18%, transparent); z-index: 1; }
  .box:not(.used) { opacity: .7; }
  .box span { position: absolute; left: 3px; top: 3px; font: 600 11px/1.3 system-ui; color: #000; background: var(--c); padding: 0 6px; border-radius: 9px; }
  .grip { position: absolute; right: -2px; bottom: -2px; width: 14px; height: 14px; background: var(--c); border: 1px solid rgba(0,0,0,.7); cursor: nwse-resize; }
  .room { display: flex; justify-content: space-around; align-items: center; margin-top: 12px; padding: 36px 12px; border-radius: 12px; background: #0b0b0d; }
  .bulb { --b: 1; position: relative; width: 34px; height: 34px; border-radius: 50%; background: var(--c, #333); filter: brightness(calc(.35 + .65 * var(--b)));
    transition: background .4s, filter .4s, box-shadow .4s;
    box-shadow: 0 0 14px 5px var(--c, #333), 0 0 56px 22px color-mix(in srgb, var(--c, #333) 55%, transparent); }
  .bulb::after { content: attr(data-n); position: absolute; inset: 0; display: grid; place-items: center; font: 600 12px system-ui; color: rgba(0,0,0,.55); }
  details { background: var(--card-background-color); border-radius: 12px; padding: 4px 16px; margin-bottom: 12px; }
  summary { cursor: pointer; font-weight: 500; padding: 12px 0; }
  .field { display: flex; flex-direction: column; gap: 6px; padding: 8px 0; }
  .field > span, .sl > span { font-size: 13px; color: var(--secondary-text-color); display: flex; justify-content: space-between; }
  .sl { display: block; padding: 8px 0; }
  .sl.off { opacity: .4; }
  .sl b { color: var(--primary-text-color); font-weight: 500; }
  input[type=range] { width: 100%; accent-color: var(--primary-color); }
  .ck { display: flex; align-items: center; gap: 8px; padding: 6px 0; }
  .seg { display: flex; flex-wrap: wrap; border: 1px solid var(--divider-color); border-radius: 999px; overflow: hidden; width: fit-content; max-width: 100%; }
  .seg button { border-radius: 0; padding: 7px 14px; background: transparent; color: var(--primary-text-color); font-size: 14px; }
  .seg button[aria-pressed=true] { background: var(--primary-color); color: var(--text-primary-color, #fff); }
  .card { border: 1px solid var(--divider-color); border-left: 4px solid var(--c); border-radius: 8px; padding: 8px 12px; margin: 8px 0; cursor: pointer; }
  .card.sel { background: color-mix(in srgb, var(--c) 10%, transparent); }
  .head { display: flex; align-items: center; gap: 10px; }
  .head span { flex: 1; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .chip { width: 24px; height: 24px; border-radius: 50%; border: 1px solid var(--divider-color); flex: none; }
  .spots { list-style: none; margin: 6px 0 0; padding: 0; }
  .spot { display: flex; align-items: center; gap: 8px; padding: 2px 0; font-size: 14px; }
  .spot span { flex: 1; }
  .spot em { font-style: normal; visibility: hidden; color: #4caf50; }
  .spot em.on { visibility: visible; }
  .x { padding: 0 8px; font-size: 18px; line-height: 1.2; background: transparent; color: var(--secondary-text-color); }
  .add { padding: 4px 8px; font-size: 13px; }
  .note { font-size: 13px; margin: 4px 0 0; }
  .note:empty { display: none; }
  .plainlist { list-style: none; margin: 0; padding: 0; }
  .plainlist li { display: flex; align-items: center; gap: 10px; padding: 6px 0; }
  .actions { display: flex; align-items: center; gap: 12px; margin-top: 8px; flex-wrap: wrap; }
  button { font: inherit; padding: 10px 20px; border-radius: 999px; border: 0; background: var(--primary-color); color: var(--text-primary-color, #fff); cursor: pointer; }
  button.plain { background: transparent; color: var(--primary-color); }
  button:disabled { opacity: .4; cursor: default; }
  button:focus-visible, input:focus-visible, select:focus-visible { outline: 2px solid var(--primary-color); outline-offset: 2px; }
`;

// Nach einem Neustart lädt ein offener Tab das Modul ein zweites Mal – dann nicht noch einmal definieren
if (!customElements.get("covermood-panel")) customElements.define("covermood-panel", CovermoodPanel);
