# Red Skies: the game as built

This describes what is in the code today (V1.5.0.0). Numbers come from
`src/content.js`, `src/campaign.js`, `src/sim.js` and `src/meta.js`. Change
them there, then update this file.

## The pitch

You are the fire-control officer of SAM battery *Kessel*, guarding an airbase on
the border of the Republic of Varenna (fictional). Hostile jets, helicopters,
cruise missiles and drones come in from the north and east. Friendly jets fly
home through your sector, some with broken transponders. Shoot one down and the
shift is over. The game is played on a phone held in portrait.

## The loop: one shift

A shift is 6 to 10 minutes of sim time. You sit at the console inside the
battery's cabin and work the radar scope.

1. **Find.** Tracks appear as the radar sweep finds them (range 100 km). Tap one
   or cycle with the arrows. The radar also gives you away: after 90 s of
   continuous transmission the TX timer turns red and hostile ARM carriers
   within 45 km fire anti-radiation missiles at it. Switching RADAR off resets
   the danger. Lance and Dart need the radar on to fire; the gun does not.
2. **Identify.** IFF the selected track (about 1.5 s, radar on). A working
   friendly answers FRIEND 95 % of the time, otherwise NO RESPONSE; a friendly
   with a broken transponder always gives NO RESPONSE; a hostile gives NO
   RESPONSE 85 % of the time, otherwise INVALID. Altitude, speed, heading, the
   two RTB corridors and radio calls from HQ, CAP and TOWER are the other cues.
   Classify the track FRIEND or HOSTILE.
3. **Engage.** ASSIGN a launcher (the sim suggests the best one), open the cover
   and hold FIRE. Rules of engagement come from HQ and change mid-shift: HOLD
   (no fire), TIGHT (only tracks classified HOSTILE), FREE (anything not
   classified FRIEND). A track classified FRIEND can never be fired on.
   Doctrine is SHOOT-LOOK-SHOOT (one round) or SALVO (two rounds; a double
   burst for the gun).
4. **Watch the round.** Missiles fly a real boost-and-coast profile; a coasting
   round that has to turn hard loses speed and hit chance. Hostile jets hear
   the lock or the inbound missile and may break, dive or drop chaff. The EO
   camera follows the engagement.
5. **Hold the line.** A hostile inside 3 km of the battery is a leaker. Strike
   aircraft release on the asset inside 6 km. Launchers reload from the
   battery's reserve magazine (Lance 50 s, Dart 15 s, gun 30 s); an empty
   reserve means no reload.
6. **Debrief.** The shift is graded A to F (see Scoring). Fratricide or losing
   the asset is an automatic F.

## Screens

- **Title**: an animated cover over the live 3-D scene. TAP TO BEGIN unlocks
  audio.
- **Menu**: TRAINING (shown until it is done), CAMPAIGN, SURVIVAL, FREE WATCH,
  SETTINGS.
- **Campaign map**: the six shifts, best grades and medals. Grade D or better
  unlocks the next shift.
- **Briefing**: the shift's story, then CONDITIONS, EXPECTED THREATS,
  FRIENDLY TRAFFIC, HQ NOTES, the RESERVE magazine and RULES OF ENGAGEMENT.
- **Play**: the cabin view. The radar console (scope, TRACK/IFF, BATTERY and
  COMMS tabs, launcher strip, thumb-zone buttons) and the EO camera are DOM
  elements projected onto the cabin's monitors.
- **Pause**: RESUME, RESTART SHIFT (or RESTART RUN), END RUN in survival, QUIT.
  Rotating the phone to landscape pauses the shift under a ROTATE TO PORTRAIT
  cover.
- **Debrief**: grade, the four score parts, stats, medals, and a 20x replay
  mini-scope that plays back what you saw.
- **Resupply**: spend credits on Lance, Dart and gun rounds before the next
  shift.
- **Free watch setup**: seed, difficulty slider (EASY to HARD, 0 to 1),
  duration 6/8/10 minutes, time of day, sky, and six random-event toggles.
- **Survival**: seed, HOLD THE LINE, best five runs table.
- **Settings**: SOUND, HAPTICS, TRAINING, RESET PROGRESS, and SAVE CODE with
  BACK UP and RESTORE screens.

## Systems

All of these live in `src/sim.js` unless noted, and all are driven headless by
the node tests.

- **Radar and tracks.** Fixed 20 Hz sim step. Tracks fade 20 s after they were
  last seen. Track quality, jam strobes (position unreliable), radar health,
  degraded state below 70 % health, and a repair command (radar forced off for
  19 to 30 s).
- **IFF and classification** as above. The track never exposes the true kind;
  the UI only sees cues.
- **Weapons.** Two Lance launchers (L1, L2), one Dart launcher (L3), one Harrow
  gun (G1). Lance seekers go active inside 20 km, after which that round no
  longer needs the radar.
- **Threat behaviour.** Strike runs on the asset, ARM carriers, jammers,
  pop-up helicopters that hide below terrain until about 8 to 10 km, drone
  swarms, friendly transits along the east and north RTB corridors, CAP pairs
  orbiting inside 35 km.
- **Evasion.** Hostile jets react to a lock (about 28 %) or to a closing
  missile (about 66 %): break, dive to low level (hit chance down while low),
  chaff in the terminal phase (two programmes per jet).
- **Random events** (9 kinds): radar fault, launcher jam, comms outage,
  friendly IFF failure, drone swarm, night, storm, late resupply, ROE change.
- **Weather.** Time of day dawn/day/dusk/night and sky clear/overcast/rain.
  Rain cuts radar detection of small targets, adds track noise and lowers the
  gun's hit chance; night halves visibility.
- **Comms.** Messages from HQ, CAP, TOWER and BATTERY, some needing an
  acknowledgement.
- **Survival waves.** An endless shift: wave 1 at 8 s, the next wave 15 s after
  the current one is cleared or 150 s after it began. Waves escalate (swarms
  from wave 3, ARM carriers from 4, jammers from 6). Each cleared wave adds
  2 Lance, 2 Dart and 200 gun rounds to the reserve.
- **Debrief history.** The sim records what the operator saw every 2 s plus
  the key events, for the debrief replay.
- **The view** (`scene.js`, `cabin.js`, `eo.js`, `models*.js`): terrain, sky
  and weather, procedural aircraft and launcher models, missiles with smoke and
  kill effects, a kill cam that follows your rounds, and the EO tracker (TV/IR,
  swap by tapping) with reticle, gate and readouts.
- **Audio** (`audio.js`, `audio_weapons.js`): everything is procedural
  WebAudio, with 3-D positioning from the cabin's listener, plus haptics.

## Content scale

Counted from the data files.

- **Weapons: 3.** Lance, long-range SAM, 3 to 60 km, up to 20 000 m, 4 per
  launcher, base hit chance 0.80. Dart, short-range SAM, 1 to 25 km, up to
  10 000 m, 4 per launcher, base hit chance 0.80. Harrow, gun, 0 to 4 km, up to
  4 000 m, 40-round bursts at 0.60, 600 rounds loaded. Default reserve: 8 Lance,
  8 Dart, 1200 gun rounds.
- **Threat kinds: 9.** Friendly: fighter, strike aircraft, transport, utility
  helicopter. Hostile: strike fighter, attack helicopter, cruise missile,
  loitering munition/drone, anti-radiation missile.
- **Campaign: 6 shifts, each with 3 variants (A, B, C), 18 shift definitions.**
  The game picks one variant at random per playthrough; a retry keeps it.
  Grades and medals are per shift, not per variant.

| Shift | A | B | C | Length |
| --- | --- | --- | --- | --- |
| 1 | First Watch (day, clear) | Border Patrol | Morning Traffic | 6 min |
| 2 | Night Shift (night, clear) | Lights Out | Homecoming | 7 min |
| 3 | Storm Front (dusk, rain) | Fog Bank | Lightning Alley | 7.5 min |
| 4 | Silent Line (dawn, overcast) | Blackout | Decoy Day | 8 min |
| 5 | Swarm Season (day, overcast) | Hornet's Nest | Wild Weasel | 8.3 min |
| 6 | Red Skies (night, overcast) | Dawn Assault | Last Stand | 9 min (Last Stand 10) |

  Each definition has 8 to 23 spawn entries (a swarm entry stands for several
  drones) and 4 to 19 scripted radio calls.
- **Shift 0, Kessel Range Check** (`content.js`): a hand-authored 8-minute test
  shift with 20 spawns. The menu does not list it; the tests and the fallback
  boot path use it.
- **Free watch**: generated from a seed, difficulty and duration. At 8
  minutes: 10 spawn entries on EASY, about 20 on NORMAL, about 30 on HARD.
- **Survival**: generated waves, reserve 12 Lance, 12 Dart, 1800 gun rounds,
  ROE FREE.
- **Training Watch**: 25 scripted steps (welcome, scope, radar, zoom, a
  friendly to identify, a hostile jet to engage, the camera, a drone for the
  Dart, ROE, salvo, finish). Every shot in training hits (`sureHit`).
- **Medals: 7.** CLEAN SKIES (no leakers), MARKSMAN (70 %+ first-shot kills),
  IRON DOME (asset 100 % intact), QUIET RADAR (never emitted over 90 s), FRIEND
  OR FOE (friendly identified, never shot at), MISER (at most 1.3 rounds per
  kill), SURVIVOR (reached wave 10).
- **Events on the bus: 40** names in `RS.EV`.

## Scoring

From `grade()` in `campaign.js`.

- Four parts, each 0 to 100: asset health; leakers (100 minus 25 per leaker);
  ammo (kills per shot, full marks at 0.75 kills per shot, gun bursts count as
  one shot); reaction time (mean seconds from detection to engagement, 100 at
  15 s or faster, 0 at 90 s).
- Score = 40 % asset + 20 % leakers + 20 % ammo + 20 % reaction.
- A 85+, B 70+, C 55+, D 40+, else F. Fratricide or asset destroyed is F with
  score 0.
- **Campaign economy.** Credits before each shift: 0, 260, 300, 340, 400, 460
  (shift 1 has no shop). Grade bonus: A +80, B +40. Prices: Lance 30, Dart 12,
  100 gun rounds 15. Caps: 24 Lance, 24 Dart, 3000 gun rounds.
- **Survival score** = waves × 1000 + kills × 100 + asset % × 5. The best five
  runs are kept.

## Save system

- Everything is in the browser's `localStorage`, keys `redskies.v1.campaign`,
  `.settings`, `.free`, `.survival`, `.tutorial`, written only through
  `RS.save`, `RS.load`, `RS.remove` in `main.js`. If storage is blocked the game
  keeps going from memory for that visit.
- `campaign` holds the next shift, unlocked count, best grades, results,
  reserve, bank, medals and the variant picks. `survival` holds the seed and
  best runs. `free` holds the setup. `settings` holds sound and haptics.
- **Save codes** (`savecode.js`, 1.5.0.0): Settings → SAVE CODE → BACK UP shows
  one line starting `RS1:` (base64url of LZW-compressed JSON plus a 6-character
  checksum) with a COPY CODE button. RESTORE takes a pasted code, CHECK CODE
  shows what it holds, RESTORE replaces this device's progress all at once.
  Empty, damaged, other-game (`GG1:`) and newer-version codes are refused with
  a plain message and change nothing. The code never leaves the device.

## Portrait only, phone first

- The layout is for a phone held upright. In landscape under 560 px tall a
  ROTATE TO PORTRAIT cover appears, the shift pauses and the 3-D view stops
  rendering.
- Checked sizes: 390×844 and 360×740 (the browser checks run both).
- Frame rate is capped near 60 fps; nothing renders under opaque menus; the EO
  pass runs at 30 Hz or less; far jets and distant ground kit use low detail.
- Audio suspends when the page is hidden.

## Not built yet / ideas

Reviewed in `plan/status.md` (Back-burner) and not in the code:

- Accessibility: amber text on the light keyboard shelf is about 3.1:1
  contrast; track-list rows are 36 px tall; the EO TV/IR key is 43×42 px on a
  360 px phone; "OUT RNG" is clipped on the assigned chip at 360 to 412 px; the
  main buttons are pointer-only; `#toast` is not a live region and the tabs
  lack `aria-selected`; `prefers-reduced-motion` does not cover in-game blinks;
  the debrief replay canvas blocks page scrolling.
- Performance ideas that need an on-device test: drop
  `logarithmicDepthBuffer`, send launcher FX sprites through the one-draw
  particle system, bake static meshes of ready launchers, shorten the weapon
  audio delay line and add a voice budget.
- Sim: LEAKER and ASSET_HIT should carry the entity id when the attacker was
  never tracked.
- Content: the Dustoff 3 and Dustoff 4 medevac helicopters should land after
  their shift ends.
- Open decision: in normal play, a salvo's spare round after a first-round kill
  is logged as a MISS and counts in the stats. Training hides it. Changing it
  would alter debrief numbers, so it needs Kelbo's call.
