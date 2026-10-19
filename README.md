# steamdemo

A collection of small, self-contained dashboard demos built for DTSC coursework. Each demo is a single Python script that builds or serves an interactive page you open in your browser. The data in every demo is illustrative sample data, not live data.

## What's in this repo

| File | What it is |
|---|---|
| [`build_steam_dash.py`](#steam-taste-forge-dashboard) | Builds the "Taste Forge" Steam category tracker |
| [`build_solar_nav.py`](#solar-system-navigation-map) | Builds a No Man's Sky-style 3D map of the solar system |
| [`internship_atlas_server.py`](#dtsc-internship-atlas) | Serves the Internship Atlas map from the CSV |
| [`atlas.html`](#dtsc-internship-atlas) | The Atlas page the server fills with data |
| [`internship_backend.py`](#dtsc-internship-atlas) | Generates and aggregates the internship data |
| [`internship_records.csv`](#dtsc-internship-atlas) | Sample internship records the Atlas reads |

## Requirements

- Python 3 (developed on 3.13)
- The Steam and solar system demos use only the standard library.
- The Internship Atlas needs `pip install flask pandas`.
- Every page loads some assets from the internet (fonts, d3, three.js), so you need to be online the first time you open it.

## Steam "Taste Forge" dashboard

`build_steam_dash.py` writes a single-page dashboard that shows which Steam game categories you lean toward, based on the games you tick and the hours you enter. The game list and figures are a small illustrative sample. A full version would pull real data from the Steam Web API.

```
python build_steam_dash.py            # build, then open in your browser
python build_steam_dash.py --serve    # build, then serve at http://localhost:8000
python build_steam_dash.py --no-open  # build only
```

Output: `steam-dashboard/index.html` (created next to the script).
The script's own header comment calls it `build_dashboard.py`; the file in this repo is `build_steam_dash.py`.

## Solar system navigation map

`build_solar_nav.py` builds a navigation map of the real solar system in the style of the No Man's Sky galaxy map. It covers the Sun, Mercury, Venus, Earth, Luna, Mars, Jupiter and Saturn. All the 3D models are generated in the browser, with no image files. Every body has a habitability score, a planet class and its most valuable resources.

```
python build_solar_nav.py            # build, then open in your browser
python build_solar_nav.py --serve    # build, then serve at http://localhost:8001
python build_solar_nav.py --no-open  # build only
```

Output: `solar-nav/index.html`. The first build downloads three.js into `solar-nav/three.min.js` (it falls back to a CDN if you're offline). The first load takes about 10-15 seconds while the planet textures are generated.

Controls:

- **Locked view** (default): drag to rotate around the system, scroll to zoom. Hover a planet for a summary, click it for the full details.
- **Free look** (`Space`): `W A S D` to fly, `Q` / `E` for down and up, `Shift` to boost, drag to look around, `F` to warp to the selected body.
- `Enter` opens a close-up of the selected body, and `R` toggles the details panel.
- `Esc` or right-click goes back. `P` pauses the orbits, which also stop whenever a body is selected.

Habitability is scored 0-100% from six factors: temperature, atmosphere and water count double, and radiation, gravity and surface count once. The weights are in the `WEIGHTS` object near the top of the page's script. Colors run from red (0%) to green (100%).

## DTSC Internship Atlas

A US map showing the most common internship field and employer in each state, with a field legend and a click-through breakdown per state. It started as a Claude artifact; the backend here fills it with the CSV data.

The pieces:

- **`internship_records.csv`** is the data: one row per internship, 15,000 rows across all 50 states. The columns are `state`, `field`, `role`, `company`, `company_hq` and `degree_level`. It is synthetic sample data.
- **`internship_backend.py`** generates a sample CSV (`--generate-sample`) and aggregates a CSV into `state_data.json` (`--input FILE`). The Atlas server reuses its `aggregate()` function and field catalog.
- **`internship_atlas_server.py`** is a small Flask server. It reads the CSV, aggregates it per state and serves the map page. It re-reads the CSV whenever the file changes, so you can edit it and refresh.
- **`atlas.html`** is the page itself, with the map, badges, tooltip and state dossier.

```
python internship_atlas_server.py                    # serve http://localhost:8002 and open it
python internship_atlas_server.py --csv other.csv    # use a different CSV
python internship_atlas_server.py --export atlas_live.html   # write a standalone page and exit
```

The aggregated data is also available as JSON at `/api/state_data`.
