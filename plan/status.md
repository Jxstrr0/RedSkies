# Red Skies — status

In a new session read `CLAUDE.md` first, then this file (history, decisions and the back-burner list). `DESIGN.md` describes the game as built. Update this file after every publish.

- **Version:** see `VERSION` (Major.Minor.Patch.Build; Major = overhaul, Minor = feature batch, Patch = tweak/fix, Build = republish). Bump before every publish.
- **Repo:** https://github.com/Jxstrr0/RedSkies (`main` is the default branch)
- **Live site:** https://redskies.longlight.games/ (since November 2026; the old https://jxstrr0.github.io/RedSkies/ forwards here. GitHub Pages serves the repo root of `main`, so every merge to `main` goes live; no deploy workflow). The Longlight Interactive website links here. From V1.5.0.0 (2026-10-24) the live page's version matches its features again.
- **Live artifact:** https://claude.ai/artifact/2vVrrJw4wg99sdZw6rptYP. Publish `dist/weapons_hold.artifact.html` to this same URL, labelled with the version. (The GitHub Pages site above is the main live copy now; the artifact is the older home.)
  - Last publish: V1.4.5.0 (artifact version 39), 2026-10-14. The source files are published alongside the page.
- **Studio:** Longlight Interactive. The license is all rights reserved (`LICENSE`); three.js is MIT (`vendor/three.LICENSE`).

## Layout (details in README.md)

- `src/*.js` + `src/00_shell.html`: `build.js` inlines them in its ORDER list, plus `vendor/three.min.js` (r128), into one self-contained page:
  - `index.html` (committed; GitHub Pages serves it)
  - `dist/weapons_hold.html`
  - `dist/weapons_hold.artifact.html`
- `build.js` fails when a file in `src/` is missing from ORDER, or the other way round.
- The contract is `src/contracts.js`: every event payload, state field and command. Update it with any API change.
- The sim (`src/sim.js`) never touches the DOM; the node tests drive it headless.
- Save codes (`src/savecode.js`, `RS.savecode`): Settings → Save code → Back up / Restore. `RS1:` + packed JSON of every `redskies.v1.` key + a checksum; restore checks everything before it writes, and replaces all keys at once.
- Save safety (1.6.0.0): the same box has Save file / Load file (`red-skies-backup-YYYY-MM-DD.txt`) and a storage line; `RS.storage` in `main.js` asks the browser to keep storage (`navigator.storage.persist`); `settings.backupAt` drives the menu's backup reminder.
- Tests:
  - `npm test` runs the node tests (`test/*.test.js`).
  - `npm run check:browser` runs the Playwright checks (`test/*.check.js`, shared setup in `test/_browser.js`).
  - `tools/balance.js` is the bot operator. Run it before and after gameplay changes.
- CI (`.github/workflows/ci.yml`):
  - on every push and PR: build, `index.html` drift check, node tests;
  - browser checks only on manual dispatch.

## Decisions (user)

- V1.4.3.0: a single version bump for the three improvement batches, then republish to the same artifact URL.
- Pop-up helicopters hide until about 8–10 km, as the briefings say. They start just outside their pop-up range at the authored time. Shifts with helicopters are a little harder.
- License: all rights reserved.
- V1.4.5.0: the studio is Longlight Interactive (was Prairie Blue Studio).
- V1.6.0.0 save safety (Kelbo asked for it in every Longlight game, 2026-11-06): ask the browser to keep storage, backup files next to the save code, and a quiet reminder. Small calls made here: the reminder sits on the main menu (BACK UP ▸ opens Settings at the save code box, LATER hides it for this visit); "progress" means a finished campaign shift or a survival run; the last-backup time lives in the existing `settings` key as `backupAt` (no new key), and restoring a code sets it to the code's own date, so a freshly restored phone is not nagged.
- V1.8.0.0 Blender pass, small calls made here: Blender is used where the game still had box placeholders (drone, helicopter, transport), not to redo the detailed procedural jets, launchers and radars; the models ship as generated JavaScript data with vertex colours, so the game stays one offline file with no loader; helicopters of both sides share one model, as before.
- V1.7.0.0 UI pass, small calls made here: the hint line is on by default with a Settings switch; it tells the player the next key in the drill but never whether a contact is friend or foe; the help page is one scrolling page, not a second tutorial; the launcher keys keep their short words (ROE TIGHT, OUT RNG) because longer ones do not fit a 360 px phone, and the field card explains them instead.
- V1.5.0.0: save codes get their own number. They are a new feature, so it is a Minor bump (Kelbo, 2026-10-24: pick a sensible number and go).
- The title/cover shot keeps full-quality grass; the performance savings apply in play only.
- V1.4.4.0 Training Watch:
  - Every shot the player fires in training hits: Lance, Dart and gun (`ShiftDef.sureHit`). Real watches are unchanged.
  - The training jet starts at about 40 km (was 48), so the tracker camera (35 km by day) picks it up during a prompt Lance's flight.
  - After launch the coach card follows the camera: it explains OUT OF RANGE, then says when the camera has picked up the jet.

## Changelog

- **1.8.0.0** (2026-11-11): first Blender model pass (Kelbo asked for a Blender visual pass).
  - The last three box placeholders are replaced by Blender-built aircraft: the **drone** (pusher propeller, V tail, sensor ball; 1,112 triangles), the **helicopter** (tandem cockpit, stub wings with rocket pods, chin gun, five-blade rotor; 3,296) and the **transport** (four-engine high-wing airlifter with a T-tail; 2,882). Each has a decimated low-detail copy (about 40%). They show on the tracker camera and in the cabin windows.
  - `tools/blender/build_models.py` (headless, `pip install bpy`, Blender 5.3): lofted fuselages and aerofoils in bmesh, camouflage painted into vertex colours, **ambient occlusion baked with Cycles** into the same colours, Decimate for the low copy. It writes `src/models_blender_data.js` (246 KB of base64); `src/models_blender.js` turns that into three.js meshes and hooks into `Models.create`. Same output on every run.
  - No textures, no model files, no loader library: still one offline page. The page grows from about 1.56 MB to 1.81 MB.
  - The far stand-in (2.5–4.5 km, a few pixels) is still the primitive placeholder. The rotor and the propeller spin as before (a child named `rotor`).
  - `test/scene.check.js` checks the three Blender models (source, rotor, sizes, triangle counts).

- **1.7.0.0** (2026-11-11): easier start (Kelbo asked for a UI pass that makes the game simpler to understand from the start).
  - **HOW TO PLAY** field card (`meta.js` `help()`): the drill in five steps, the three scope symbols, and a plain-words list of the console's short words (ROE, TX, ARM, Pk, OUT RNG, RLD, 1×/2×, TRK, RDR, JAM, Q, EO). It opens from the main menu, Settings and the pause screen (BACK returns to the pause screen, still paused). Weapon ranges are read from `content.js`.
  - **"What next" line** under the selected track (`ui.js` `nextHint()`): "Next: tap IFF…", "No IFF reply. Check COMMS…", "Marked HOSTILE. Next: tap ASSIGN…", "Launcher ready. Press and hold FIRE.", and a warning when a track that answered FRIEND is marked HOSTILE. It never says what a contact is; that stays the player's call. **Settings → HINTS** turns it off (`settings.hints`, in save codes too).
  - The first briefing offers **TRAINING** and HOW TO PLAY while training is not done. The menu's TRAINING button now says "Start here" and "about 3 minutes".
  - Fix: in training, pop-up messages (for example "L2 LANCE assigned") covered the coach card's NEXT button. They now sit just above the card (`tutorial.js` `liftToast()`).
  - Tests: `savecode.test.js` covers `settings.hints`; `test/meta.check.js` has a `help` section (META_ONLY=help).

- **1.6.1.1** (2026-11-08): republish for the new address, https://redskies.longlight.games/ (every Longlight game now has its own subdomain, so its own storage; saves from before the move stay on jxstrr0.github.io). Docs, the save-safety comment in `src/main.js` and the `LONGLIGHT-STUDIO.md` copy updated; no gameplay change.
- **1.6.1.0** (2026-11-06): home-screen icon. A green radar scope with its sweep and a red hostile contact (`icons/icon.svg`), rendered to `icons/apple-touch-icon.png` (180), `icon-192.png`, `icon-512.png` and `icon-512-maskable.png` by `tools/make-icons.js` (run by hand). New `manifest.webmanifest` (standalone, portrait, `#050707`); the shell links the manifest, favicon (SVG + PNG) and apple-touch-icon, and names the home-screen app "Red Skies".
- **1.6.0.0** (2026-11-06): save safety. Settings → Save code now also has **Save file** (the same `RS1:` code as `red-skies-backup-YYYY-MM-DD.txt`: the share sheet where the browser can share files, so iPhone offers Save to Files, else a download) and **Load file** (reads a file into Restore, so the same check and confirm run; a broken file gets the usual "damaged or incomplete" message). A line says whether the browser keeps the game's storage, and the game asks it to (`navigator.storage.persist`) once per visit after progress is saved, training ends, or a backup or restore. Copying the code or saving the file records `settings.backupAt`; with progress and no backup, or one 14+ days old, the main menu shows a small reminder once per visit. Node tests cover `backupAt` and file text; `test/meta.check.js` `code` section covers the reminder, Save file, Load file (broken and good). Not republished to the claude.ai artifact.

- **1.5.0.0** (2026-10-24): version bump only, no game change. Save codes shipped in PR #8 (2026-10-15) without a bump, so the live page read V1.4.5.0 while carrying a new feature. 1.5.0.0 is that feature batch. Not republished to the claude.ai artifact.
- **1.4.5.0, second build (PR #8, merged 2026-10-15, live on GitHub Pages)**: save codes, released as 1.5.0.0 above. Settings → Save code → **Back up** shows all progress as one `RS1:` line with a Copy button; **Restore** takes a pasted code, shows what it holds and asks before replacing this device's progress. It carries the campaign, survival best runs, free watch setup, training and settings. Damaged, cut-off, other-game and newer-version codes get a plain message and change nothing. New `test/savecode.test.js`; `test/meta.check.js` has a `code` section (META_ONLY=code).
- **1.4.5.0**: studio renamed from Prairie Blue Studio to Longlight Interactive (title credit, menu credit, LICENSE, README, file headers).
- **1.4.4.0** (Training Watch)
  - Every training shot hits: no Pk roll, no dodging or chaff, an engaged target cannot leave, and a salvo's spare round vanishes without a MISS. The flag is tested before any `rand()`, and 108 normal-shift fingerprint runs are byte-identical to 1.4.3.0.
  - The training jet starts at ~40 km.
  - The post-launch steps follow the camera (OUT OF RANGE → picked up, ring on the camera). The step moves on by itself at the splash.
  - `RS.scene.eo.state.maxKm` gives the camera's current range.
  - The tutorial remembers what each shot was fired at, so a kill after the track faded (radar off) still counts. Before, the training got stuck.
  - Reworded: the salvo step (training shots always hit; real ones can miss), the miss hint and the out-of-range hint.
  - New `test/training.test.js`.
  - Follow-up after verification:
    - The OUT OF RANGE card is shorter, so it fits a 360 px phone without covering the camera.
    - On camera steps the card keeps clear of the camera. A card that fits nowhere goes where it covers the least (it used to jump to the top).
    - The jet's distance shows to 0.1 km (like the camera's readout) and always reads above the camera's reach.
    - The text drops "(top right)" and the "make it big" tip when the camera fills the view.
    - Watching steps show "watching…" instead of "your move". The out-of-range hint also covers "too high" (gun vs the 5000 m jet).
    - A salvo's spare round vanishes with the kill.
    - The no-fit fallback weighs the ring target and the II button 100× more than the scope or the camera. On a 360×640 phone the radio-call card used to cover II.
- **1.4.3.0**
  - Batch 1 (bug fixes):
    - SALVO second round re-checks ROE, FRIEND, assignment, radar and the fire-control solution.
    - ARM_INBOUND names the ARM's track.
    - Pop-up helicopters work.
    - Corridor friendlies join the route ahead of them.
    - Reloads cannot share reserve rounds, and an empty launcher retries its reload.
    - SHIFT_END.grade equals the debrief grade.
    - C5B keeps its 6-Lance cap; the extra Lance wait in the depot and the screens show it.
    - Rotating the phone pauses the shift.
    - Audio suspends when the page is hidden.
    - One `<script>` per module.
  - Batch 2 (phone performance):
    - Grass far band uses lighter tufts.
    - Far-jet LOD tier.
    - Distant ground kit uses low detail.
    - 60 fps cap; nothing renders under opaque menus.
    - EO pass at 30 Hz or less.
    - Particle uploads cover live particles only.
    - Launch smoke rate is capped.
    - Finished weapon-audio voices are disconnected.
  - Batch 3 (repo):
    - three.js bundled; the game works offline.
    - Fonts no longer block the page.
    - `VERSION` file.
    - ORDER check in `build.js`.
    - Tests updated to V1.4.3, with a test runner and a shared browser helper.
    - CI, LICENSE and this status doc.
- **1.4.2.0**: imported from the claude.ai artifact; `src/` rebuilt from the live page.

## Back-burner (reviewed ideas not done yet)

- **Polish and accessibility:**
  - Amber text on the light keyboard shelf is about 3.1:1 contrast.
  - Track-list rows are 36 px (below the 44/48 px touch-target guideline).
  - The EO TV/IR key is 43×42 px on a 360 px phone.
  - "OUT RNG" is clipped on the assigned chip at 360–412 px.
  - The main buttons are pointer-only (no keyboard).
  - `#toast` is not a live region, and the tabs lack `aria-selected`.
  - `prefers-reduced-motion` does not cover the in-game blinks.
  - The debrief replay canvas blocks page scrolling (`touch-action: none`).
- **Performance** (these need an on-device test):
  - Drop `logarithmicDepthBuffer` (it disables early-Z).
  - Send the launcher FX sprites through the one-draw particle system.
  - Bake the static meshes of ready TELs.
  - Shorten the 26 s weapon-audio delay line and add a voice budget.
- **Sim:** LEAKER and ASSET_HIT carry the entity id when the attacker was never tracked (the log shows "E13").
- **Models (Blender):** a separate utility helicopter for friendly medevac flights (they share the gunship model); Blender-built far stand-ins; a baked-light pass on the cabin interior.
- **Content:** the Dustoff 3 (C2) and Dustoff 4 (C2B) medevac helicopters land after their shift ends.
- **Code comments:** keep or reword the "Kelbo" nickname in `src/models_launchers.js` and `src/scene.js`.
- **Salvo spare-round MISS (normal play):** after the first round of a salvo kills, the second round's self-destruct is logged and flashed as a MISS and counts in stats.misses. Training hides it (1.4.4). Changing it for real watches would alter the debrief numbers, so it needs a decision.
- **Deliberate, not bugs:** Survival counts outlasted waves (`sim.js`, "outlasted the previous wave").
