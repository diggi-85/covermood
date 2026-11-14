// Der Editor ohne Browser: prüft die heikelste Logik – wem die Punkte gehören (Raum oder Album).
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import vm from "node:vm";

// Gerade so viel Browser, wie das Panel zum Rechnen braucht; gezeichnet wird ins Leere
const fakeRoot = { innerHTML: "", addEventListener() {}, querySelector: () => null, querySelectorAll: () => [] };
let Panel;
const context = vm.createContext({
  HTMLElement: class {
    attachShadow() {
      return (this.shadowRoot = { ...fakeRoot });
    }
  },
  customElements: { get: () => undefined, define: (_, cls) => (Panel = cls) },
  matchMedia: () => ({ matches: true }),
  requestAnimationFrame: () => 0,
  cancelAnimationFrame() {},
  structuredClone,
  setTimeout,
  clearTimeout,
});
vm.runInContext(readFileSync(new URL("../custom_components/covermood/frontend/covermood-panel.js", import.meta.url), "utf8"), context);

const ROOM = { "light.a": [[0, 0, 0.5, 1]], "light.b": [[0.5, 0, 0.5, 1]] };
const ALBUM = { regions: { "light.a": [[0.1, 0.1, 0.2, 0.2]] }, paths: { "light.a": [0.6, 0.6, 0.2, 0.2] } };

async function open() {
  const calls = [];
  const settings = { mode: "calm", source: "regions", fade: null, every: null, regions: structuredClone(ROOM), paths: {}, calibration: {}, presets: {} };
  const panel = new Panel();
  panel._hass = {
    language: "de",
    states: {},
    connection: { subscribeMessage: async () => () => {} },
    callWS: async (msg) => (calls.push(structuredClone(msg)), null),
  };
  panel._data = {
    rooms: [{ id: "r", name: "Büro", enabled: true, sources: [], lights: [{ entity_id: "light.a", name: "A" }, { entity_id: "light.b", name: "B" }], settings }],
    modes: { calm: { fade: 6, every: 30, shift: 0.06 } },
    max_spots: 5,
    preset_keys: ["style"],
  };
  await panel._select(0);
  return { panel, calls };
}

test("an album with its own spots shows them, and the room keeps its own", async () => {
  const { panel, calls } = await open();
  panel._onEvent({ playing: true, enabled: true, album: "Bad", album_spots: ALBUM });
  assert.equal(panel._albumOn, true);
  assert.deepEqual(panel._s.regions["light.a"], ALBUM.regions["light.a"]);
  assert.deepEqual(panel._s.regions["light.b"], ROOM["light.b"]); // was das Album nicht nennt, kommt vom Raum
  assert.deepEqual(panel._s.paths, ALBUM.paths);

  panel._s.regions["light.a"][0] = [0.3, 0.3, 0.2, 0.2]; // im Album bearbeiten …
  await panel._save();
  assert.equal(calls.at(-1).album, true);
  assert.equal(calls.at(-1).album_name, "Bad");
  assert.deepEqual(panel._roomSpots.regions, ROOM); // … lässt die Punkte des Raums unberührt

  panel._setAlbum(false); // zurück zum Raum
  assert.deepEqual(panel._s.regions, ROOM);
  assert.deepEqual(panel._s.paths, {});
  await panel._save();
  assert.equal(calls.at(-1).album, false);
});

test("the next album without own spots gets the room's spots back", async () => {
  const { panel } = await open();
  panel._onEvent({ playing: true, enabled: true, album: "Bad", album_spots: ALBUM });
  panel._onEvent({ playing: true, enabled: true, album: "Thriller", album_spots: null });
  assert.equal(panel._albumOn, false);
  assert.deepEqual(panel._s.regions, ROOM);
});

test("changing the mood writes only what the server accepts", async () => {
  const { panel } = await open();
  panel._set("mode", "calm");
  assert.equal("shift" in panel._s, false);
  assert.deepEqual([panel._s.fade, panel._s.every], [6, 30]);
});
