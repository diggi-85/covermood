<p align="center"><img src="https://raw.githubusercontent.com/diggi-85/covermood/main/docs/banner.png" alt="Covermood – Home Assistant integration" width="800"></p>

<p align="center"><b>English</b> · <a href="README.de.md">Deutsch</a></p>

<p align="center">
  <a href="https://my.home-assistant.io/redirect/hacs_repository/?owner=diggi-85&repository=covermood&category=integration"><img src="https://my.home-assistant.io/badges/hacs_repository.svg" alt="Open in HACS"></a>
  <a href="https://github.com/diggi-85/covermood/actions/workflows/ci.yml"><img src="https://github.com/diggi-85/covermood/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <img src="https://img.shields.io/badge/version-0.2-blue" alt="Version 0.2">
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-green" alt="MIT"></a>
</p>

# Covermood

**Your lights wear the cover.** Press play, and the lights in the room take on the colors of the album art – each lamp
from the exact spot on the cover you picked for it, blending smoothly from one track to the next. Pause, and they
return to how they were. It works with every music service that shows cover art in Home Assistant: Spotify, Sonos,
Apple Music / AirPlay, Plex, Music Assistant and more.

![The Covermood editor: the cover with one spot per lamp, the wall preview and a spot that swings across the wave](https://raw.githubusercontent.com/diggi-85/covermood/main/docs/screenshots/en/wave.jpg)

<table>
  <tr>
    <td width="50%"><img src="https://raw.githubusercontent.com/diggi-85/covermood/main/docs/screenshots/en/night.jpg" alt="Pastel style on a night-sky cover; the floor lamp falls back to its backup spot because its main spot is dark"></td>
    <td width="50%"><img src="https://raw.githubusercontent.com/diggi-85/covermood/main/docs/screenshots/en/sunrise.jpg" alt="Intense style on a sunrise cover"></td>
  </tr>
  <tr>
    <td align="center"><sub><b>Pastel</b> – the main spot of the floor lamp sits on a dark tree, so its <b>backup spot</b> takes over (✓)</sub></td>
    <td align="center"><sub><b>Intense</b> – the table lamp's spot <b>swings</b> across the morning sky</sub></td>
  </tr>
</table>

<sub>Screenshots with sample data and public-domain artwork (see [Credits](#credits)).</sub>

## Why you'll love it

- 🎯 **You decide where each lamp looks.** Drag a spot onto the cover for every bulb – the lamp gets exactly that color.
  No more “somehow muddy brown”.
- 🛟 **Backup spots.** Is the main spot black right now? The next spot takes over, and if all of them are dark, the lamp
  takes a defining color of the whole cover. Your room never goes dark or grey.
- 🌀 **Spots that move.** Let a lamp's spot swing slowly across the cover – the room keeps changing gently, even
  within one song.
- 🖼️ **A live editor.** The cover changes with every track *inside the editor*, and the room preview shows how your
  bulbs will glow – before you touch a real light.
- 🎨 **Four styles:** *Vibrant*, *Pastel*, *Faithful to the artwork* and *Intense / dramatic* – plus sliders for minimum
  saturation and brightness. Every change reaches the running track instantly.
- 🌊 **Smooth transitions.** Set the fade time between covers and how often the colors drift – or let them stand still.
- 🎛️ **Calm, Static and Party mood**, switchable any time – and a mood is a single entry in a file if you want to add one.
- 💾 **Presets and per-album spots.** Save a look as “Evening” or “Party” and recall it from an automation; give a
  favorite album its own spots.
- 🏠 **Several rooms**, each with its own players, lights, spots and settings. Rooms, players and lights are read from
  Home Assistant (areas are suggested for you).
- 🧯 **Polite to your lights.** The previous state is restored afterwards (or a default color is set) – even across a
  Home Assistant restart in the middle of a song –, pauses don't reset anything, lights that are off stay off unless you want them switched on.
- 🌍 **English and German** – the setup wizard, the editor and all entities.

## Installation

### HACS (recommended)

1. Click the badge above – or in HACS choose **⋮ → Custom repositories**, add `https://github.com/diggi-85/covermood`
   as category **Integration**.
2. Install **Covermood** and restart Home Assistant.
3. **Settings → Devices & services → Add integration → Covermood** and follow the wizard.

### Manual

Copy `custom_components/covermood` into `config/custom_components/` and restart Home Assistant.

Requires Home Assistant 2025.6 or newer.

## Set up

The wizard has three short steps and starts with a room:

1. **Room** – pick a Home Assistant area (or just type a name).
2. **Players and lights** – the media players and color-capable lights of that area are suggested. *The order in which
   you select the lights is the direction of the color gradient.*
3. **Look** – mood, where the colors come from, number of colors, whether lights that are off should be switched on,
   and whether to restore them afterwards.

Everything can be changed later in the editor. Add more rooms under *Devices & services → Covermood → Add room*.

## The editor

Open **Covermood** in the sidebar. The page takes on the colors of the cover, a wall preview shows how the room will
glow, and everything you change is saved a moment later – the lights follow without anything reloading.

| Tab | What you can do |
|---|---|
| **Spots** | Choose where the colors come from: *Automatic* (defining colors), *Zones* (left to right, like an Ambilight) or *Own points*. With own points every light has a card with a **main spot** and **backup spots**; drag the rectangles on the cover and resize them at the corner. Each rectangle shows the color it measures. **Motion** lets the main spot swing slowly to a second spot and back. **Only for this album** keeps a set of spots just for the album that is playing. **Match this bulb** corrects a lamp that shows colors differently from the others. |
| **Color** | Style (*Vibrant, Pastel, Faithful, Intense*), minimum saturation, and the brightness of the lights: *Leave alone*, *Fixed value* or *Follow the cover* (between a minimum and a maximum – never darker than the minimum). |
| **Motion** | Mood (*Calm, Static, Party*), fade time for a new cover, how often the colors drift, whether own points drift around the lamps, and how long a swinging spot takes there and back. The preview plays all of it. |
| **Rules** | Only for certain sources (e.g. only Spotify, not the TV), only while an entity is on, switch on lights that are off, restore afterwards, or set a **default color** at the end instead. |
| **Presets** | Save the current look (style, brightness, mood, speed) under a name and recall it with one click – or from an automation. |

Next to the room picker, the **Active** switch turns Covermood on or off for that room. **Test on lights** puts the
current settings on your real lights for 10 seconds and then restores them.

The cover comes from the room's player – also when it is paused or idle, as long as it provides an image.

## Automations

The action **Covermood: Apply look** (`covermood.apply`) sets a preset, a style or a mood – for one room or, without a
room, for all:

```yaml
action: covermood.apply
data:
  room: Living room
  preset: Evening
```

## Moods and styles

| Mood | Behavior |
|---|---|
| Calm | colors drift gently every 30 s, 6 s fade between covers |
| Static | colors stand still |
| Party | colors drift every 2 s, fast fades |

| Style | Look |
|---|---|
| Vibrant | strong, saturated colors |
| Pastel | soft and light, little saturation |
| Faithful | as the cover shows them |
| Intense | maximum saturation, dramatic |

## Entities per room

| Entity | Purpose |
|---|---|
| `switch` Active | Covermood on/off for the room (remembers its state) |
| `select` Mood | Calm / Static / Party (holds until restart; the editor sets the mood permanently) |
| `sensor` Color palette | the colors currently read from the cover (`colors` attribute) |
| `binary_sensor` Coloring lights | diagnostic: Covermood is controlling the lights right now |

## Good to know

- Lights that are on are only **colored** – their brightness stays, unless you choose *Fixed value* or *Follow the
  cover* in the editor. Lights that are off are switched on only **when the music starts** (optional); if you switch
  them off afterwards, they stay off.
- Near-black parts of a cover are never used as a color.
- A swinging spot sends each lamp a soft step every 3 seconds – many bulbs can't take commands faster than that.
- If Home Assistant restarts while music plays, Covermood remembers how the lights were before the music and restores
  that once the lights are reachable again.
- Only lights with color support (HS/RGB/XY) are offered.
- A cover without any color (greyscale) colors the lights white; if no cover can be read, the lights are left alone.
- A **default color** replaces restoring the state from before the music.
- Adding or changing a room under *Devices & services* reloads the integration; the lights briefly jump back to their
  state before the music. Changes in the editor don't reload anything.
- Tested with Sonos; any Home Assistant media player that provides cover art should work.

## Add a mood or a style

A mood is one entry in [`modes.py`](custom_components/covermood/modes.py) (`MODES`), one line each in
`translations/*.json` under `selector.mode.options` and `entity.select.mode.state`, and its name in `T.modes` of the
editor (`frontend/covermood-panel.js`). A style is one entry in `STYLES` plus `T.styles`.

## Development

Tests need `pytest-homeassistant-custom-component`:

```bash
pip install -r requirements_test.txt
python -m pytest
```

`colors.py` (cover → colors → gradient) is plain Python without Home Assistant and a port of `cover.ts` from
[Ambiframe](https://github.com/diggi-85/ambiframe).

## Credits

The screenshots use public-domain artwork from Wikimedia Commons: *The Great Wave off Kanagawa* (Katsushika Hokusai),
*The Starry Night* (Vincent van Gogh) and *Impression, Sunrise* (Claude Monet). Logo and banner are set in
[Inter](https://github.com/rsms/inter) (SIL Open Font License).

## License

[MIT](LICENSE) © diggi-85
