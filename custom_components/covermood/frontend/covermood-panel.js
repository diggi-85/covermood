// Covermood-Editor: Stellen im Cover je Licht (fest oder pendelnd), Farbstil, Bewegung, Regeln, Vorlagen.
// Ohne Build, ohne Abhängigkeiten. Jede Änderung wirkt sofort auf die Vorschau und – nach kurzer Pause – auf die
// Lichter; gespeichert wird von selbst.
const MIN = 0.03;
// Ändern, was zu sehen ist – bei allen anderen Einstellungen genügt es, den Wert nachzuführen
const STRUCTURAL = ["source", "mode", "style", "bri_mode", "default_color", "drift_points"];
const HUES = [200, 35, 140, 330, 60, 270, 10, 170, 100, 300, 230, 80];
const GATE_DOMAINS = ["input_boolean", "switch", "binary_sensor", "light"];
const TABS = ["spots", "color", "motion", "rules", "presets"];
const T = {
  de: {
    room: "Raum",
    idle: "Nichts spielt – gezeigt wird das letzte Cover.",
    power: "Aktiv",
    off: "Covermood ist für diesen Raum aus – die Lichter bleiben unberührt.",
    nocover: "Noch kein Cover. Starte Musik in diesem Raum – sobald ein Titel ein Cover hat, erscheint es hier und wechselt mit jedem Titel.",
    norooms: "Es ist noch kein Raum eingerichtet.",
    hint: "Ziehe ein Rechteck auf die Stelle, deren Farbe das Licht bekommen soll; die Ecke unten rechts ändert die Größe.",
    needpoints: "Für freie Stellen im Cover wähle unter „Punkte“ die Option „Eigene Punkte“.",
    wall: "So leuchtet der Raum",
    tabs: { spots: "Punkte", color: "Farbe", motion: "Bewegung", rules: "Regeln", presets: "Vorlagen" },
    source: "Farben aus dem Cover",
    sources: { palette: "Automatisch", zones: "Zonen", regions: "Eigene Punkte" },
    points: "Anzahl Farben",
    main: "Hauptpunkt",
    alt: "Ersatzpunkt",
    target: "Ziel der Bewegung",
    addalt: "Ersatzpunkt",
    addpath: "Bewegung",
    del: "Entfernen",
    altHint: "Ersatzpunkte (gestrichelt) greifen, wenn der Hauptpunkt gerade schwarz ist.",
    pathHint: "Mit „Bewegung“ pendelt der Hauptpunkt langsam zu einem zweiten Punkt und zurück.",
    fallback: "Alle Punkte zu dunkel – nimmt eine prägende Farbe des Covers.",
    nocolor: "Cover ganz dunkel – das Licht bleibt, wie es ist.",
    album: "Nur für dieses Album",
    albumHint: "Die Punkte gelten dann nur, wenn dieses Album läuft. Alle anderen behalten die Punkte des Raums.",
    tune: "Leuchtmittel abgleichen",
    tuneHue: "Farbton",
    tuneSat: "Sättigung",
    tuneHint: "Zeigt diese Lampe Farben anders als die anderen, gleichst du sie hier an. Wirkt nur auf die echte Lampe.",
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
    mode: "Stimmung",
    modes: { calm: "Ruhig", static: "Statisch", party: "Party" },
    fade: "Überblendzeit bei neuem Cover",
    every: "Farben wandern alle",
    still: "stehen still",
    drift: "Eigene Punkte reihum wandern lassen",
    driftHint: "Jede Lampe läuft dann über die Farben der anderen Lampen. Aus: jede Lampe behält ihre Stelle.",
    period: "Punkte pendeln hin und zurück in",
    periodHint: "Gilt für Lichter mit „Bewegung“. Die Lampen bekommen alle 3 Sekunden einen weichen Schritt.",
    onlySources: "Nur bei diesen Quellen",
    anySource: "Jede Quelle",
    onlyWhile: "Nur solange diese Entität an ist",
    onlyWhilePh: "z. B. input_boolean.party – leer = immer",
    turnOn: "Ausgeschaltete Lichter beim Start einschalten",
    restore: "Lichter danach zurücksetzen",
    defColor: "Standardfarbe am Ende (statt Zurücksetzen)",
    presetsHint: "Eine Vorlage hält Stil, Helligkeit, Stimmung und Tempo fest. Abrufen kannst du sie hier oder in Automationen mit der Aktion „Covermood: Aussehen anwenden“.",
    presetName: "Name der Vorlage",
    presetSave: "Aktuelles Aussehen speichern",
    presetApply: "Anwenden",
    nopresets: "Noch keine Vorlage.",
    test: "Auf Lichtern testen",
    testing: "Test läuft – die Lichter kehren gleich zurück.",
    reset: "Punkte zurücksetzen",
    saving: "Speichert …",
    saved: "Gespeichert",
    fail: "Fehler",
  },
  en: {
    room: "Room",
    idle: "Nothing is playing – showing the last cover.",
    power: "Active",
    off: "Covermood is off for this room – the lights are left alone.",
    nocover: "No cover yet. Play music in this room – once a track has cover art it shows up here and changes with every track.",
    norooms: "No room is set up yet.",
    hint: "Drag a rectangle to the spot whose color the light should get; the corner at the bottom right resizes it.",
    needpoints: "To pick spots on the cover, choose “Own points” under “Spots”.",
    wall: "How the room glows",
    tabs: { spots: "Spots", color: "Color", motion: "Motion", rules: "Rules", presets: "Presets" },
    source: "Colors from the cover",
    sources: { palette: "Automatic", zones: "Zones", regions: "Own points" },
    points: "Number of colors",
    main: "Main spot",
    alt: "Backup spot",
    target: "Target of the motion",
    addalt: "Backup spot",
    addpath: "Motion",
    del: "Remove",
    altHint: "Backup spots (dashed) take over when the main spot is currently black.",
    pathHint: "With “Motion” the main spot slowly swings to a second spot and back.",
    fallback: "All spots too dark – uses a dominant color of the cover.",
    nocolor: "Cover is entirely dark – the light stays as it is.",
    album: "Only for this album",
    albumHint: "The spots then apply only while this album plays. All others keep the room's spots.",
    tune: "Match this bulb",
    tuneHue: "Hue",
    tuneSat: "Saturation",
    tuneHint: "If this lamp shows colors differently from the others, adjust it here. Only affects the real lamp.",
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
    mode: "Mood",
    modes: { calm: "Calm", static: "Static", party: "Party" },
    fade: "Fade time on a new cover",
    every: "Colors drift every",
    still: "stand still",
    drift: "Let own points drift around the lamps",
    driftHint: "Each lamp then runs through the colors of the other lamps. Off: each lamp keeps its spot.",
    period: "Spots swing there and back in",
    periodHint: "Applies to lights with “Motion”. The lamps get a soft step every 3 seconds.",
    onlySources: "Only for these sources",
    anySource: "Any source",
    onlyWhile: "Only while this entity is on",
    onlyWhilePh: "e.g. input_boolean.party – empty = always",
    turnOn: "Switch on lights that are off when music starts",
    restore: "Restore the lights afterwards",
    defColor: "Default color at the end (instead of restoring)",
    presetsHint: "A preset keeps style, brightness, mood and speed. Recall it here or in automations with the action “Covermood: Apply look”.",
    presetName: "Preset name",
    presetSave: "Save the current look",
    presetApply: "Apply",
    nopresets: "No preset yet.",
    test: "Test on lights",
    testing: "Test running – the lights return shortly.",
    reset: "Reset spots",
    saving: "Saving …",
    saved: "Saved",
    fail: "Error",
  },
};
const esc = (s) => String(s ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[c]);
const clamp = (v, lo, hi) => Math.min(hi, Math.max(lo, v));
const clone = (v) => structuredClone(v);
const lightColor = (l) => `hsl(${HUES[l % HUES.length]} 90% 60%)`;
const mix = (a, b, f) => (!a ? b : !b ? a : `color-mix(in srgb, ${a} ${Math.round((1 - f) * 100)}%, ${b})`);
const rectStyle = ([x, y, w, h]) => `left:${x * 100}%;top:${y * 100}%;width:${w * 100}%;height:${h * 100}%`;
const center = ([x, y, w, h]) => [x + w / 2, y + h / 2];
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
    this._data = null; // { rooms, modes, max_spots, preset_keys }
    this._i = 0;
    this._s = null; // Einstellungen des gewählten Raums (Arbeitskopie)
    this._roomSpots = null; // { regions, paths } des Raums – die Arbeitskopie kann stattdessen die eines Albums sein
    this._albumOn = false; // gelten die Punkte der Arbeitskopie nur für das laufende Album?
    this._album = undefined; // Album, auf das die Arbeitskopie zuletzt abgestimmt wurde
    this._sel = 0; // gewähltes Licht
    this._tab = "spots";
    this._tuneOpen = new Set(); // Lichter, deren Abgleich aufgeklappt ist
    this._image = null;
    this._now = {};
    this._enabled = true; // ist Covermood für den gewählten Raum an?
    this._res = [];
    this._unsub = null;
    this._token = 0;
    this._drift = 0; // wie weit die wandernden Farben in der Vorschau schon gezogen sind (Anteil des Rings)
    this.shadowRoot.addEventListener("input", (e) => this._onInput(e));
    this.shadowRoot.addEventListener("change", (e) => this._onInput(e, true));
    this.shadowRoot.addEventListener("click", (e) => this._onClick(e));
    this.shadowRoot.addEventListener("pointerdown", (e) => this._onDown(e));
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
    this._play();
  }
  disconnectedCallback() {
    this._unsubscribe();
    cancelAnimationFrame(this._frame);
    this._frame = null;
  }

  get t() {
    return T[(this._hass?.language || "en").slice(0, 2)] || T.en;
  }
  get room() {
    return this._data?.rooms[this._i];
  }
  get _own() {
    return this._s.source === "regions";
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
    this._album = undefined;
    this._albumOn = false;
    this._unsubscribe();
    const room = this.room;
    this._s = room ? clone(room.settings) : null;
    this._enabled = room?.enabled ?? true;
    if (this._s) {
      const m = this._data.modes[this._s.mode];
      this._s.fade ??= m.fade; // die Stimmung liefert, was nicht überschrieben ist
      this._s.every ??= m.every;
      this._roomSpots = { regions: clone(this._s.regions), paths: clone(this._s.paths) };
    }
    this._draw();
    if (room) await this._subscribe();
  }

  // --- Live: Cover, Titel, Album ---

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
    if (ev.gone) return void setTimeout(() => this._load(), 3000); // Integration lädt neu: den neuen Raum holen
    this._now = ev;
    if ("enabled" in ev) this._enabled = ev.enabled;
    let redraw = false;
    if ((ev.album ?? null) !== this._album) {
      // Anderes Album: seine eigenen Punkte übernehmen – oder die des Raums, wenn es keine hat
      this._album = ev.album ?? null;
      this._albumOn = !!ev.album_spots;
      const own = ev.album_spots;
      this._s.regions = clone(own ? { ...this._roomSpots.regions, ...own.regions } : this._roomSpots.regions);
      this._s.paths = clone(own ? own.paths || {} : this._roomSpots.paths);
      redraw = true;
    }
    if ("image" in ev && ev.image !== this._image) {
      const hadImage = !!this._image;
      this._image = ev.image;
      if (hadImage && ev.image && !redraw) {
        this.shadowRoot.querySelector("#stage img").src = ev.image;
        this.shadowRoot.querySelector(".ambient").style.backgroundImage = `url(${ev.image})`;
      } else redraw = true;
      this._previewSoon();
    }
    if (redraw) {
      this._draw();
      this._previewSoon();
    }
    this._paintNow();
  }

  _paintNow() {
    const el = this.shadowRoot.querySelector(".now");
    if (!el) return;
    const n = this._now;
    const power = this.shadowRoot.querySelector("#power");
    if (power) power.checked = this._enabled;
    el.innerHTML = !this._enabled
      ? `<span>${this.t.off}</span>`
      : n.playing
      ? `<i class="dot"></i>${esc(n.title || "")}${n.artist ? ` <span>– ${esc(n.artist)}</span>` : ""}`
      : `<span>${this.t.idle}</span>`;
  }

  // --- Zeichnen ---

  _draw() {
    const t = this.t;
    const rooms = this._data?.rooms || [];
    const room = this.room;
    if (!room) {
      this.shadowRoot.innerHTML = `<style>${CSS}</style><div class="wrap"><p class="hint">${t.norooms}</p></div>`;
      return;
    }
    const stage = this._image
      ? `<div class="stage" id="stage"><img src="${this._image}" draggable="false" alt="">${this._own ? this._boxes() : ""}</div>
         <div class="wall" aria-label="${t.wall}">${room.lights
           .map(
             (light, l) => `<div class="lamp" data-lamp="${l}"><i class="cone"></i><i class="bulb"></i>
               <span>${l + 1} · ${esc(light.name)}</span></div>`,
           )
           .join("")}</div>
         <p class="hint">${this._own ? t.hint : t.needpoints}</p>`
      : `<div class="stage"><div class="empty">${t.nocover}</div></div>`;
    this.shadowRoot.innerHTML = `<style>${CSS}</style>
      <div class="ambient"${this._image ? ` style="background-image:url(${this._image})"` : ""}></div>
      <div class="wrap">
        <header>
          <h1>Covermood</h1>
          <select id="room" aria-label="${t.room}">${rooms
            .map((r, i) => `<option value="${i}"${i === this._i ? " selected" : ""}>${esc(r.name)}</option>`)
            .join("")}</select>
          <label class="power"><input type="checkbox" id="power" role="switch"${this._enabled ? " checked" : ""}> ${t.power}</label>
          <div class="now" aria-live="polite"></div>
          <span id="msg" role="status"></span>
        </header>
        <div class="grid">
          <section class="main">${stage}</section>
          <aside class="side">
            <nav class="tabs" role="tablist">${TABS.map(
              (tab) => `<button type="button" role="tab" data-tab="${tab}" aria-selected="${tab === this._tab}">${t.tabs[tab]}</button>`,
            ).join("")}</nav>
            <div class="panel" role="tabpanel">${this[`_tab_${this._tab}`]()}</div>
            <div class="actions">
              <button type="button" id="test"${this._image ? "" : " disabled"}>${t.test}</button>
              ${this._own && this._tab === "spots" ? `<button type="button" id="reset" class="plain">${t.reset}</button>` : ""}
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
    if (k === "path_period") return v >= 60 ? `${Math.round(v / 6) / 10} min` : `${v} s`;
    if (k === "fade") return `${v} s`;
    if (k === "points") return String(v);
    return `${v} %`;
  }

  _tab_spots() {
    const t = this.t, s = this._s, room = this.room;
    const head = `<div class="field"><span>${t.source}</span>${this._seg("source", t.sources, s.source)}</div>`;
    if (!this._own)
      return `${head}${this._slider("points", t.points, 2, 12, 1)}
        <ul class="plainlist">${room.lights
          .map((light, l) => `<li><b class="chip" data-chip="${l}"></b>${l + 1} · ${esc(light.name)}<small data-bri="${l}"></small></li>`)
          .join("")}</ul>`;
    const cards = room.lights
      .map((light, l) => {
        const spots = s.regions[light.entity_id];
        const path = s.paths[light.entity_id];
        const [hue, sat] = s.calibration[light.entity_id] || [0, 100];
        const row = (label, used, del, canDel = true) => `<li class="spot"><span>${label}</span>${used}
          <button type="button" class="x" data-del="${del}" title="${t.del}" aria-label="${t.del}: ${label}"${canDel ? "" : " disabled"}>×</button></li>`;
        return `<div class="card${l === this._sel ? " sel" : ""}" data-l="${l}" style="--c:${lightColor(l)}">
          <div class="head"><b class="chip" data-chip="${l}"></b><span>${l + 1} · ${esc(light.name)}</span><small data-bri="${l}"></small></div>
          <ul class="spots">${spots
            .map((_, k) => row(k ? `${t.alt} ${k}` : t.main, `<em data-used="${l}-${k}">✓</em>`, `${l}-${k}`, spots.length > 1))
            .join("")}${path ? row(t.target, "", `${l}-to`) : ""}</ul>
          <div class="cardbtns">
            <button type="button" class="ghostbtn" data-add="${l}"${spots.length >= this._data.max_spots ? " disabled" : ""}>+ ${t.addalt}</button>
            ${path ? "" : `<button type="button" class="ghostbtn" data-path="${l}">+ ${t.addpath}</button>`}
            <button type="button" class="ghostbtn" data-tune="${l}" aria-expanded="${this._tuneOpen.has(l)}">${t.tune}</button>
          </div>
          ${
            this._tuneOpen.has(l)
              ? `<div class="tune">
                  <label class="sl"><span>${t.tuneHue}<b data-cv="${l}-0">${hue > 0 ? "+" : ""}${hue}°</b></span>
                    <input type="range" data-cal="${l}-0" min="-30" max="30" step="1" value="${hue}"></label>
                  <label class="sl"><span>${t.tuneSat}<b data-cv="${l}-1">${sat} %</b></span>
                    <input type="range" data-cal="${l}-1" min="50" max="150" step="1" value="${sat}"></label>
                  <small>${t.tuneHint}</small></div>`
              : ""
          }
          <p class="note" data-note="${l}"></p>
        </div>`;
      })
      .join("");
    const album = this._now.album
      ? `<label class="ck"><input type="checkbox" id="album"${this._albumOn ? " checked" : ""}> ${t.album}: <b>${esc(this._now.album)}</b></label>
         <small class="note">${t.albumHint}</small>`
      : "";
    return `${head}${album}${cards}<small class="note">${t.altHint} ${t.pathHint}</small>`;
  }

  _tab_color() {
    const t = this.t, s = this._s;
    return `<div class="field"><span>${t.style}</span>${this._seg("style", t.styles, s.style)}<small>${t.styleHints[s.style]}</small></div>
      ${this._slider("min_sat", t.minsat, 0, 100, 1)}
      <div class="field"><span>${t.brimode}</span>${this._seg("bri_mode", t.brimodes, s.bri_mode)}</div>
      ${s.bri_mode === "keep" ? "" : this._slider("brightness", s.bri_mode === "cover" ? t.brimax : t.bri, 1, 100, 1)}
      ${s.bri_mode === "cover" ? this._slider("min_bri", t.brimin, 1, 100, 1) : ""}`;
  }

  _tab_motion() {
    const t = this.t, s = this._s;
    const still = this._own && !s.drift_points; // eigene Punkte stehen fest, solange sie nicht wandern dürfen
    const moving = this._own && Object.keys(s.paths).length > 0;
    return `<div class="field"><span>${t.mode}</span>${this._seg("mode", t.modes, s.mode)}</div>
      ${this._slider("fade", t.fade, 0, 30, 0.5)}
      ${this._own ? `${this._check("drift_points", t.drift)}<small class="note">${t.driftHint}</small>` : ""}
      ${this._slider("every", t.every, 0, 120, 1, still)}
      ${this._slider("path_period", t.period, 10, 300, 5, !moving)}
      <small class="note">${moving ? t.periodHint : t.pathHint}</small>`;
  }

  _tab_rules() {
    const t = this.t, s = this._s, room = this.room;
    const names = [...new Set([...room.sources, ...s.only_sources])];
    const entities = Object.keys(this._hass?.states || {})
      .filter((id) => GATE_DOMAINS.includes(id.split(".")[0]))
      .sort();
    return `<div class="field"><span>${t.onlySources}</span>${
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
      ${s.default_color ? `<input type="color" data-k="default_color" data-t="c" value="${hsToHex(...s.default_color)}">` : ""}`;
  }

  _tab_presets() {
    const t = this.t, names = Object.keys(this._s.presets);
    return `<small class="note">${t.presetsHint}</small>
      ${
        names.length
          ? `<ul class="presets">${names
              .map(
                (n) => `<li><span>${esc(n)}</span>
                  <button type="button" class="ghostbtn" data-preset="${esc(n)}">${t.presetApply}</button>
                  <button type="button" class="x" data-unpreset="${esc(n)}" title="${t.del}" aria-label="${t.del}: ${esc(n)}">×</button></li>`,
              )
              .join("")}</ul>`
          : `<p class="note">${t.nopresets}</p>`
      }
      <div class="newpreset">
        <input type="text" id="presetname" maxlength="40" placeholder="${t.presetName}" aria-label="${t.presetName}">
        <button type="button" id="presetsave">${t.presetSave}</button>
      </div>`;
  }

  _boxes() {
    const lights = this.room.lights, s = this._s;
    const box = (l, k, r, cls, label) => `<div class="box ${cls}${l === this._sel ? " sel" : ""}" data-l="${l}" data-k="${k}" style="--c:${lightColor(l)};${rectStyle(r)}">
      <span>${label}</span><i class="grip"></i></div>`;
    const boxes = lights.flatMap((light, l) => [
      ...s.regions[light.entity_id].map((r, k) => box(l, k, r, k ? "alt" : "", `${l + 1}${k ? "abcdefgh"[k - 1] : ""}`)),
      ...(s.paths[light.entity_id] ? [box(l, "to", s.paths[light.entity_id], "to", `${l + 1} →`)] : []),
    ]);
    // Bahn (Linie) und der Punkt, der in der Vorschau darauf pendelt
    const lines = lights
      .map((light, l) => (s.paths[light.entity_id] ? `<line data-line="${l}" style="--c:${lightColor(l)}"/>` : ""))
      .join("");
    const ghosts = lights
      .map((light, l) => (s.paths[light.entity_id] ? `<i class="ghost" data-ghost="${l}" style="--c:${lightColor(l)}"></i>` : ""))
      .join("");
    return `<svg class="paths" viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden="true">${lines}</svg>${boxes.join("")}${ghosts}`;
  }

  // Ergebnis der Vorschau in die schon gezeichneten Elemente eintragen (ohne neu zu zeichnen)
  _paintRes() {
    const $$ = (s) => this.shadowRoot.querySelectorAll(s);
    const t = this.t;
    this._res.forEach((r, l) => {
      $$(`[data-bri="${l}"]`).forEach((el) => (el.textContent = r.bri == null ? "" : `${r.bri} %`));
      $$(`[data-note="${l}"]`).forEach((el) => (el.textContent = r.used === -1 ? (r.color ? t.fallback : t.nocolor) : ""));
      $$(`.box[data-l="${l}"]`).forEach((el) => el.classList.toggle("used", el.dataset.k === "to" || +el.dataset.k === r.used));
      $$(`[data-used^="${l}-"]`).forEach((el) => el.classList.toggle("on", +el.dataset.used.split("-")[1] === r.used));
      $$(`[data-lamp="${l}"]`).forEach((el) => el.style.setProperty("--b", (r.bri ?? 100) / 100));
    });
    this.shadowRoot.querySelector(".wall")?.style.setProperty("--fade", `${Math.min(this._s.fade, 8)}s`);
    this._paintPaths();
    this._paintColors(this._res.map((r) => r.color));
    this._play();
  }

  // Die Farbe je Licht überall dort eintragen, wo sie gezeigt wird: Wand, Chip, Rechtecke
  _paintColors(colors) {
    colors.forEach((c, l) => {
      this.shadowRoot.querySelectorAll(`[data-lamp="${l}"], [data-chip="${l}"], .box[data-l="${l}"]`).forEach((el) => {
        el.style.setProperty("--m", c || "transparent");
      });
    });
  }

  _paintPaths() {
    const s = this._s;
    this.room.lights.forEach((light, l) => {
      const line = this.shadowRoot.querySelector(`[data-line="${l}"]`);
      if (!line) return;
      const [x1, y1] = center(s.regions[light.entity_id][0]), [x2, y2] = center(s.paths[light.entity_id]);
      Object.entries({ x1, y1, x2, y2 }).forEach(([k, v]) => line.setAttribute(k, v * 100));
    });
  }

  // --- Vorschau abspielen: pendelnde Punkte und wandernde Farben ---

  _animated() {
    if (!this._s || !this._res.length || matchMedia("(prefers-reduced-motion: reduce)").matches) return false;
    const s = this._s;
    const drifting = s.every > 0 && (!this._own || s.drift_points);
    return this._res.some((r) => r.track) || drifting;
  }

  _play() {
    const on = this._animated();
    this.shadowRoot.querySelector(".wall")?.classList.toggle("anim", on);
    if (!on) {
      cancelAnimationFrame(this._frame);
      this._frame = null;
    } else if (!this._frame) this._frame = requestAnimationFrame((ts) => this._step(ts));
  }

  _step(ts) {
    this._frame = null;
    if (!this.isConnected || !this._animated()) return;
    this._frame = requestAnimationFrame((next) => this._step(next));
    if (ts - (this._last || 0) < 100) return; // zehn Bilder je Sekunde genügen
    const dt = Math.min((ts - (this._last || ts)) / 1000, 1);
    this._last = ts;
    const s = this._s, lights = this.room.lights;
    // Wie im Raum: Phase 0 = Start, 0,5 = Ziel; sanft an- und auslaufend
    const phase = ((ts / 1000) % s.path_period) / s.path_period;
    const eased = (1 - Math.cos(2 * Math.PI * phase)) / 2;
    const along = phase < 0.5 ? phase * 2 : 2 - phase * 2; // Stelle in der Liste der Farben entlang der Bahn
    let colors = this._res.map((r, l) => {
      if (!r.track) return r.color;
      const pos = along * (r.track.length - 1), lo = Math.floor(pos);
      const ghost = this.shadowRoot.querySelector(`[data-ghost="${l}"]`);
      const path = s.paths[lights[l].entity_id];
      if (ghost && path) {
        const [ax, ay] = center(s.regions[lights[l].entity_id][0]), [bx, by] = center(path);
        ghost.style.left = `${(ax + (bx - ax) * eased) * 100}%`;
        ghost.style.top = `${(ay + (by - ay) * eased) * 100}%`;
      }
      return mix(r.track[lo], r.track[Math.min(lo + 1, r.track.length - 1)], pos - lo);
    });
    if (s.every > 0 && (!this._own || s.drift_points)) {
      this._drift = (this._drift + ((this._data.modes[s.mode].shift || 0.06) * dt) / s.every) % 1;
      const ring = colors.filter(Boolean);
      if (ring.length > 1)
        colors = colors.map((_, l) => {
          const pos = ((l / colors.length + this._drift) % 1) * ring.length, lo = Math.floor(pos) % ring.length;
          return mix(ring[lo], ring[(lo + 1) % ring.length], pos - Math.floor(pos));
        });
    }
    this._paintColors(colors);
  }

  // --- Bedienung ---

  _onClick(e) {
    const b = e.target.closest("button, .card");
    if (!b) return;
    const { k, v, add, del, l, tab, path, tune, preset, unpreset } = b.dataset;
    if (b.id === "test") return this._test();
    if (b.id === "reset") return this._resetStripes();
    if (b.id === "presetsave") return this._savePreset();
    if (tab) return ((this._tab = tab), this._draw());
    if (k && v !== undefined) return this._set(k, v);
    if (add !== undefined) return this._addSpot(+add);
    if (path !== undefined) return this._addPath(+path);
    if (del !== undefined) return this._delSpot(...del.split("-"));
    if (tune !== undefined) {
      this._tuneOpen.has(+tune) ? this._tuneOpen.delete(+tune) : this._tuneOpen.add(+tune);
      return this._draw();
    }
    if (preset !== undefined) return this._applyPreset(preset);
    if (unpreset !== undefined) {
      delete this._s.presets[unpreset];
      this._draw();
      return this._changed();
    }
    if (b.classList.contains("card") && l !== undefined) this._choose(+l);
  }

  _onInput(e, committed = false) {
    const el = e.target;
    if (el.id === "room") return committed && this._select(+el.value);
    if (el.id === "power") return committed && this._enable(el.checked);
    if (el.id === "album") return committed && this._setAlbum(el.checked);
    if (el.dataset.cal !== undefined) return !committed && this._calibrate(el);
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
    if (k === "mode") {
      const m = this._data.modes[value];
      Object.assign(this._s, { fade: m.fade, every: m.every });
    }
    if (live) this.shadowRoot.querySelector(`[data-v="${k}"]`).textContent = this._fmt(k, value);
    else if (!keep && STRUCTURAL.includes(k)) this._draw();
    this._changed();
  }

  _calibrate(el) {
    const [l, i] = el.dataset.cal.split("-").map(Number);
    const id = this._id(l);
    const value = [...(this._s.calibration[id] || [0, 100])];
    value[i] = +el.value;
    if (value[0] === 0 && value[1] === 100) delete this._s.calibration[id];
    else this._s.calibration[id] = value;
    this.shadowRoot.querySelector(`[data-cv="${l}-${i}"]`).textContent = i ? `${value[1]} %` : `${value[0] > 0 ? "+" : ""}${value[0]}°`;
    this._changed();
  }

  _setAlbum(on) {
    this._albumOn = on;
    if (!on) {
      // zurück zu den Punkten des Raums
      this._s.regions = clone(this._roomSpots.regions);
      this._s.paths = clone(this._roomSpots.paths);
    }
    this._draw();
    this._changed();
  }

  _savePreset() {
    const input = this.shadowRoot.querySelector("#presetname");
    const name = input.value.trim();
    if (!name) return input.focus();
    this._s.presets[name] = Object.fromEntries(this._data.preset_keys.map((key) => [key, this._s[key]]));
    this._draw();
    this._changed();
  }

  _applyPreset(name) {
    Object.assign(this._s, clone(this._s.presets[name]));
    const m = this._data.modes[this._s.mode];
    this._s.fade ??= m.fade;
    this._s.every ??= m.every;
    this._draw();
    this._changed();
  }

  async _enable(on) {
    this._enabled = on;
    this._paintNow();
    try {
      await this._hass.callWS({ type: "covermood/enable", room_id: this.room.id, enabled: on });
    } catch (err) {
      this._enabled = !on; // hat nicht geklappt: Schalter zurück
      this._paintNow();
      this._say(`${this.t.fail}: ${err.message || err.code || err}`);
    }
  }

  _choose(l) {
    this._sel = l;
    this.shadowRoot.querySelectorAll(".card, .box").forEach((el) => el.classList.toggle("sel", +el.dataset.l === l));
  }

  _id(l) {
    return this.room.lights[l].entity_id;
  }

  _spots(l) {
    return this._s.regions[this._id(l)];
  }

  _addSpot(l) {
    const spots = this._spots(l);
    const n = spots.length;
    spots.push([clamp(0.3 + 0.12 * n, 0, 0.84), clamp(0.3 + 0.1 * n, 0, 0.84), 0.14, 0.14]);
    this._redrawSpots(l);
  }

  _addPath(l) {
    // Ziel so groß wie der Hauptpunkt, auf der anderen Seite des Covers
    const [x, y, w, h] = this._spots(l)[0];
    this._s.paths[this._id(l)] = [clamp(1 - x - w, 0, 1 - w), clamp(y < 0.5 ? y + 0.25 : y - 0.25, 0, 1 - h), w, h];
    this._redrawSpots(l);
  }

  _delSpot(l, k) {
    if (k === "to") delete this._s.paths[this._id(+l)];
    else this._spots(+l).splice(+k, 1);
    this._redrawSpots(+l);
  }

  _redrawSpots(l) {
    this._sel = l;
    this._draw();
    this._changed();
  }

  _resetStripes() {
    const lights = this.room.lights;
    lights.forEach((light, l) => (this._s.regions[light.entity_id] = [[l / lights.length, 0, 1 / lights.length, 1]]));
    this._s.paths = {};
    this._draw();
    this._changed();
  }

  _onDown(e) {
    const box = e.target.closest(".box");
    if (!box) return;
    e.preventDefault();
    const l = +box.dataset.l, k = box.dataset.k;
    this._choose(l);
    const stage = this.shadowRoot.querySelector("#stage").getBoundingClientRect();
    const put = (r) => (k === "to" ? (this._s.paths[this._id(l)] = r) : (this._spots(l)[+k] = r));
    const [x0, y0, w0, h0] = k === "to" ? this._s.paths[this._id(l)] : this._spots(l)[+k];
    const size = e.target.classList.contains("grip");
    const move = (ev) => {
      const dx = (ev.clientX - e.clientX) / stage.width, dy = (ev.clientY - e.clientY) / stage.height;
      const r = size
        ? [x0, y0, clamp(w0 + dx, MIN, 1 - x0), clamp(h0 + dy, MIN, 1 - y0)]
        : [clamp(x0 + dx, 0, 1 - w0), clamp(y0 + dy, 0, 1 - h0), w0, h0];
      put(r);
      Object.assign(box.style, { left: `${r[0] * 100}%`, top: `${r[1] * 100}%`, width: `${r[2] * 100}%`, height: `${r[3] * 100}%` });
      this._paintPaths();
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
    const msg = { type: "covermood/update", room_id: this.room.id, settings: this._s };
    if (this._now.album) Object.assign(msg, { album: this._albumOn, album_name: this._now.album }); // Punkte gehören dem Album – oder dem Raum
    if (!this._albumOn) this._roomSpots = { regions: clone(this._s.regions), paths: clone(this._s.paths) };
    try {
      await this._hass.callWS(msg);
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
      setTimeout(() => {
        const again = this.shadowRoot.querySelector("#test");
        if (again) again.disabled = false;
      }, seconds * 1000);
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
  :host { display: block; position: relative; min-height: 100%; background: var(--primary-background-color); color: var(--primary-text-color);
    --line: var(--divider-color); --card: var(--card-background-color); --muted: var(--secondary-text-color); --accent: var(--primary-color); }
  * { box-sizing: border-box; }
  /* Das Cover färbt den Hintergrund – weich und nach unten auslaufend */
  .ambient { position: absolute; inset: 0 0 auto 0; height: 560px; background-size: cover; background-position: center; filter: blur(70px) saturate(1.3);
    opacity: .28; transform: scale(1.15); pointer-events: none; mask-image: linear-gradient(#000 35%, transparent); -webkit-mask-image: linear-gradient(#000 35%, transparent); }
  .wrap { position: relative; max-width: 1240px; margin: 0 auto; padding: 16px 16px 32px; }
  header { display: flex; flex-wrap: wrap; align-items: center; gap: 8px 16px; margin-bottom: 16px; }
  h1 { font-size: 22px; font-weight: 600; letter-spacing: -.01em; margin: 0; }
  select, input[type=text] { font: inherit; padding: 8px 12px; border-radius: 8px; border: 1px solid var(--line); background: var(--card); color: inherit; }
  input[type=text] { width: 100%; }
  .now { flex: 1 1 240px; min-width: 0; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .now span, small, .note { color: var(--muted); }
  .dot { display: inline-block; width: 8px; height: 8px; margin-right: 8px; border-radius: 50%; background: #3fa34d; }
  .power { display: flex; align-items: center; gap: 8px; cursor: pointer; }
  .power input { appearance: none; -webkit-appearance: none; position: relative; width: 38px; height: 22px; margin: 0; border-radius: 11px; cursor: pointer;
    background: var(--line); transition: background .2s; }
  .power input::after { content: ""; position: absolute; top: 3px; left: 3px; width: 16px; height: 16px; border-radius: 50%; background: #fff; transition: transform .2s; }
  .power input:checked { background: var(--accent); }
  .power input:checked::after { transform: translateX(16px); }
  #msg { color: var(--muted); min-height: 1.2em; font-size: 14px; }
  .grid { display: grid; grid-template-columns: minmax(0, 1.2fr) minmax(320px, 1fr); gap: 24px; align-items: start; }
  .main { position: sticky; top: 8px; }
  @media (max-width: 900px) { .grid { grid-template-columns: 1fr; } .main { position: static; } }
  .hint { color: var(--muted); line-height: 1.45; margin: 12px 0 0; font-size: 14px; }

  .stage { position: relative; line-height: 0; border-radius: 12px; overflow: hidden; background: var(--card); user-select: none; -webkit-user-select: none;
    box-shadow: 0 8px 28px rgba(0,0,0,.28); }
  .stage img { width: 100%; display: block; pointer-events: none; }
  .empty { line-height: 1.5; padding: 64px 24px; text-align: center; color: var(--muted); }
  /* --c: Kennfarbe des Lichts, --m: die Farbe, die an dieser Stelle gemessen wurde */
  .box { position: absolute; border: 2px solid var(--c); border-radius: 4px; cursor: move; touch-action: none;
    background: color-mix(in srgb, var(--m, transparent) 30%, transparent); box-shadow: 0 0 0 1px rgba(0,0,0,.65), inset 0 0 0 1px rgba(0,0,0,.45); }
  .box.alt, .box.to { border-style: dashed; }
  .box.sel { z-index: 2; box-shadow: 0 0 0 1px rgba(0,0,0,.65), 0 0 0 4px color-mix(in srgb, var(--c) 35%, transparent); }
  .box:not(.used) { opacity: .6; background: transparent; }
  .box span { position: absolute; left: 3px; top: 3px; font: 600 11px/1.4 system-ui; color: #000; background: var(--c); padding: 0 6px; border-radius: 9px; white-space: nowrap; }
  .grip { position: absolute; right: -2px; bottom: -2px; width: 14px; height: 14px; background: var(--c); border: 1px solid rgba(0,0,0,.65); border-radius: 4px 0 2px 0; cursor: nwse-resize; }
  .paths { position: absolute; inset: 0; width: 100%; height: 100%; pointer-events: none; }
  .paths line { stroke: var(--c); stroke-width: 2; stroke-dasharray: 5 5; vector-effect: non-scaling-stroke; }
  .ghost { position: absolute; z-index: 3; width: 12px; height: 12px; margin: -6px 0 0 -6px; border-radius: 50%; background: var(--c); border: 2px solid #fff;
    box-shadow: 0 0 0 1px rgba(0,0,0,.6); pointer-events: none; }

  /* Die Wand: jedes Licht wirft einen Kegel, benachbarte mischen sich */
  .wall { --fade: 2s; display: flex; margin-top: 12px; padding: 0 8px; border-radius: 12px; overflow: hidden; background: #0c0c0f; }
  .lamp { --b: 1; position: relative; flex: 1; min-width: 0; height: 128px; display: flex; align-items: flex-end; justify-content: center; }
  .cone { position: absolute; inset: 0 -45% 22px; mix-blend-mode: screen; opacity: calc(.3 + .7 * var(--b));
    background: radial-gradient(58% 100% at 50% 100%, var(--m, #222) 0%, color-mix(in srgb, var(--m, #222) 35%, transparent) 45%, transparent 78%);
    transition: opacity var(--fade); }
  .bulb { position: absolute; bottom: 26px; width: 10px; height: 10px; border-radius: 50%; background: color-mix(in srgb, var(--m, #333) 55%, #fff); }
  .lamp span { position: relative; padding: 0 4px 6px; max-width: 100%; font-size: 12px; color: #a9a9b2; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }

  .side { background: var(--card); border-radius: 12px; padding: 0 16px 16px; }
  .tabs { display: flex; gap: 4px; margin: 0 -16px 8px; padding: 0 12px; border-bottom: 1px solid var(--line); overflow-x: auto; }
  .tabs button { flex: none; padding: 14px 10px 12px; border-radius: 0; background: transparent; color: var(--muted); font-size: 14px; border-bottom: 2px solid transparent; }
  .tabs button[aria-selected=true] { color: var(--primary-text-color); border-bottom-color: var(--accent); }
  .field { display: flex; flex-direction: column; gap: 6px; padding: 8px 0; }
  .field > span, .sl > span { font-size: 13px; color: var(--muted); display: flex; justify-content: space-between; gap: 12px; }
  .sl { display: block; padding: 8px 0; }
  .sl.off { opacity: .4; }
  .sl b { color: var(--primary-text-color); font-weight: 500; font-variant-numeric: tabular-nums; }
  input[type=range] { width: 100%; accent-color: var(--accent); }
  .ck { display: flex; align-items: center; gap: 8px; padding: 6px 0; flex-wrap: wrap; }
  .seg { display: flex; flex-wrap: wrap; border: 1px solid var(--line); border-radius: 8px; overflow: hidden; width: fit-content; max-width: 100%; }
  .seg button { border-radius: 0; padding: 7px 14px; background: transparent; color: var(--primary-text-color); font-size: 14px; }
  .seg button[aria-pressed=true] { background: var(--accent); color: var(--text-primary-color, #fff); }
  .card { border: 1px solid var(--line); border-left: 4px solid var(--c); border-radius: 8px; padding: 10px 12px; margin: 8px 0; cursor: pointer; }
  .card.sel { background: color-mix(in srgb, var(--c) 9%, transparent); }
  .head { display: flex; align-items: center; gap: 10px; }
  .head span { flex: 1; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .head small, .plainlist small { font-variant-numeric: tabular-nums; }
  .chip { width: 24px; height: 24px; border-radius: 50%; border: 1px solid var(--line); flex: none; background: var(--m, transparent); }
  .spots, .presets, .plainlist { list-style: none; margin: 6px 0 0; padding: 0; }
  .spot, .presets li { display: flex; align-items: center; gap: 8px; padding: 2px 0; font-size: 14px; }
  .spot span, .presets span { flex: 1; min-width: 0; }
  .presets li { padding: 6px 0; border-bottom: 1px solid var(--line); }
  .spot em { font-style: normal; visibility: hidden; color: #3fa34d; }
  .spot em.on { visibility: visible; }
  .x { padding: 0 8px; font-size: 18px; line-height: 1.2; background: transparent; color: var(--muted); }
  .cardbtns { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 6px; }
  .ghostbtn { padding: 4px 10px; font-size: 13px; background: transparent; color: var(--accent); border: 1px solid var(--line); border-radius: 8px; }
  .tune { margin-top: 8px; padding-top: 4px; border-top: 1px solid var(--line); cursor: default; }
  .note { display: block; font-size: 13px; line-height: 1.45; margin: 4px 0 0; }
  .note:empty { display: none; }
  .plainlist li { display: flex; align-items: center; gap: 10px; padding: 6px 0; }
  .plainlist small { margin-left: auto; }
  .newpreset { display: flex; gap: 8px; margin-top: 12px; flex-wrap: wrap; }
  .newpreset input { flex: 1 1 160px; width: auto; }
  .actions { display: flex; align-items: center; gap: 12px; margin-top: 16px; flex-wrap: wrap; }
  button { font: inherit; padding: 9px 18px; border-radius: 8px; border: 0; background: var(--accent); color: var(--text-primary-color, #fff); cursor: pointer; }
  button.plain { background: transparent; color: var(--accent); }
  button:disabled { opacity: .4; cursor: default; }
  button:focus-visible, input:focus-visible, select:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }
  @media (prefers-reduced-motion: reduce) { .power input, .power input::after, .cone { transition: none; } }
`;

// Nach einem Neustart lädt ein offener Tab das Modul ein zweites Mal – dann nicht noch einmal definieren
if (!customElements.get("covermood-panel")) customElements.define("covermood-panel", CovermoodPanel);
