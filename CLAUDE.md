# Red Skies: notes for Claude Code

Red Skies is a portrait-only browser game by Longlight Interactive. You are the
fire-control officer of SAM battery *Kessel*, Republic of Varenna: watch the
radar, sort friendly jets from hostiles, and hold your fire until you are sure.

Read this file first. Then `DESIGN.md` (the game as built) and `plan/status.md`
(version history, decisions, back-burner list). `README.md` is the longer guide.

## Stack

- Plain HTML, CSS and JavaScript. No framework, no bundler, no runtime npm
  packages. Every module is a plain script sharing one global, `window.RS`.
- three.js r128, vendored at `vendor/three.min.js` (MIT, see
  `vendor/three.LICENSE`). No CDN, so the game also plays offline.
- The only outside resource is two Google Fonts for the title (Russo One, Big
  Shoulders Display). They load without blocking and have fallbacks.
- Dev only: Playwright 1.56.1 (`package.json`), for the browser checks. CI uses
  Node 22.

## Commands that work

```sh
node build.js             # or npm run build: writes index.html and dist/
npm test                  # node tests (test/*.test.js); no install needed
npm ci                    # once, installs Playwright for the browser checks
npx playwright install chromium   # once, a Chromium for Playwright
npm run check:browser     # builds, then runs test/*.check.js headless (slow)
npm run balance           # tools/balance.js: a bot plays the campaign shifts
```

## Build, version, deploy

- `build.js` inlines `vendor/three.min.js` and the `src/*.js` modules, in its
  `ORDER` list, into `src/00_shell.html`, one `<script>` per module. It writes
  `index.html` (committed, the playable page), `dist/weapons_hold.html` (the
  browser checks load this) and `dist/weapons_hold.artifact.html` (the claude.ai
  artifact flavour with no doctype/html/head/body).
- The build fails if a file in `src/` is missing from `ORDER`, or the other way
  round. A new module goes into `ORDER` in load order.
- `VERSION` holds `Major.Minor.Patch.Build` (now 1.4.5.0). The build stamps it
  into the `<title>` and `window.RS.VERSION`. Major = overhaul, Minor = feature
  batch, Patch = tweak or fix, Build = republish. Bump it before a release.
- After any `src/` change: run `node build.js` and commit `index.html` with it.
  CI fails when `index.html` is out of date with `src/`.
- CI (`.github/workflows/ci.yml`): on every push to `main` and every pull
  request it builds, checks that `index.html` is current, and runs the node
  tests. The browser checks run only when the workflow is started by hand with
  **browser** ticked.
- Deploy: GitHub Pages serves the repo root of `main`, so merging to `main`
  publishes `index.html`. There is no deploy workflow. Live:
  https://jxstrr0.github.io/RedSkies/ Repo: https://github.com/Jxstrr0/RedSkies

## Code conventions (what the code actually does)

- `src/contracts.js` is the contract: every event name and payload, the sim
  state shape, the command and query API. Update it with any API change. New
  things are added in new sections at the end; older sections are not rewritten.
- `src/sim.js` never touches the DOM or three.js. It runs in node, so the node
  tests and the balance bot drive it headless with a stubbed `window`.
- Fixed sim step at 20 Hz (`RS.SIM_HZ`). Rendering is separate, capped near
  60 fps, and skipped under opaque menus and the rotate cover.
- Tuning lives next to its system, not in one file: weapons, threats and the
  default magazine in `src/content.js`; campaign shifts, budget, prices and
  grading in `src/campaign.js`; sim constants at the top of `src/sim.js`.
- Content is JavaScript data, not JSON: `ShiftDef` objects in `content.js` and
  `campaign.js`, tutorial steps in `tutorial.js`, medals in `meta.js`.
- The sim is seeded (`RS.sim.init({seed})`, `mulberry32`). The same seed replays
  the same shift. The Training Watch's `sureHit` flag is checked before any
  random draw, so normal shifts are byte-for-byte unchanged by it.
- Saves: `localStorage` keys `redskies.v1.` + key, only through `RS.save`,
  `RS.load` and `RS.remove` in `main.js` (try/catch, memory fallback when storage
  is blocked). Keys: `campaign`, `settings`, `free`, `survival`, `tutorial`.
- Save codes (`src/savecode.js`): `RS1:` + base64url(LZW(UTF-8 JSON)) + a
  6-character checksum. Restore checks the whole code before writing, then
  replaces all keys at once. Nothing is ever sent anywhere.
- Fictional names only: Varenna, Kessel, Lance, Dart, Harrow. No real units.
- Portrait only. Landscape under 560 px tall shows the ROTATE TO PORTRAIT cover
  and pauses the shift. Test at 390×844 and 360×740.

## Where things live

| Path | What it is |
| --- | --- |
| `src/00_shell.html` | Page markup and CSS; markers `<!-- RS_THREE -->` and `<!-- RS_SCRIPTS -->` |
| `src/contracts.js` | The contract: units, enums, `RS.bus`, events, state shape, commands |
| `src/content.js` | Weapons, threats, Shift 0 range check, Free watch and Survival generators |
| `src/campaign.js` | The six campaign shifts and their B/C variants, story, budget, prices, `grade()` |
| `src/sim.js` | The air picture: radar, tracks, IFF, weapons, ARMs, jamming, ROE, comms, evasion |
| `src/models*.js`, `src/jet_friend.js` | Procedural three.js models (launchers, ground kit, jets, weapons) |
| `src/scene.js` | The 3-D world: terrain, sky and weather, aircraft, missiles, effects, EO picture |
| `src/cabin.js` | The operator cabin; projects the DOM radar console and `#eo` onto its monitors |
| `src/eo.js` | EO tracker symbology (TV/IR camera overlay) |
| `src/ui.js` | Radar scope, TRACK/IFF, BATTERY and COMMS tabs, launcher strip, thumb zone |
| `src/audio.js`, `src/audio_weapons.js` | Procedural WebAudio and haptics; weapon sounds |
| `src/meta.js` | Menus, campaign map, briefing, debrief, resupply, free watch, survival, settings, pause, save code screens |
| `src/savecode.js` | Save codes: make, read, apply, summary |
| `src/title.js` | The animated cover page over the live scene |
| `src/tutorial.js` | The guided Training Watch (25 steps) |
| `src/main.js` | Boot, fixed-step loop, resize and rotate handling, `RS.save/load/remove` |
| `test/*.test.js` | Node tests: sim, content, campaign, fixes, save codes, training |
| `test/*.check.js`, `test/_browser.js` | Playwright checks: browser, ui, meta, scene, audio; shared setup |
| `test/run.js` | Runs every test file and exits 1 if any failed |
| `tools/balance.js` | The bot operator; run before and after gameplay changes |
| `plan/status.md` | Version history, decisions, back-burner list |
| `VERSION`, `build.js`, `index.html`, `dist/` | Version, build script, built page, build outputs (`dist/` is ignored by git) |

## How Kelbo works

- Beginner-plus coder who tests on his phone from the live URL. End every task
  with a plain-language summary of what changed and how to test it on the live
  site.
- Work on a branch and open a pull request into `main`. Never push straight to
  `main`.
- Once `npm test` and `node build.js` pass and the PR check (CI) is green, merge
  the PR yourself. Kelbo has given standing permission to merge.
- Keep pull requests small enough to review on a phone.
- Real design decisions: ask Kelbo, then record the answer under Decisions in
  `plan/status.md`. Small calls: decide and note them there.
- Use the name Kelbo only. Never his real name or initials, anywhere.

## Current status

- V1.4.5.0 is on `main` and live. Built and playable: the Training Watch, a
  six-shift campaign with three variants per shift, Free watch, Survival,
  medals, the resupply shop, save codes, the 3-D operator cabin with the EO
  camera, procedural audio and haptics.
- Save codes (PR #8, 2026-10-15) were merged after the 1.4.5.0 bump and are
  live under that number. Pick the next version number before the next release.
- Known gaps: the back-burner list in `plan/status.md` (contrast and touch
  target sizes, keyboard access, a few perf ideas that need an on-device test,
  small sim and content items). The browser checks do not run in CI by default.
