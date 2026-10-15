/* RED SKIES — save code test (src/savecode.js). node test/savecode.test.js  (exit 1 on failure)
   Runs RS.savecode headless against a fake localStorage that works like main.js's RS.save / RS.load / RS.remove. */
const fs = require('fs'), path = require('path'), vm = require('vm');
const src = f => fs.readFileSync(path.join(__dirname, '..', 'src', f), 'utf8');

let fails = 0, checks = 0;
const ok = (c, m) => { checks++; console.log((c ? '  PASS ' : '  FAIL ') + m); if (!c) fails++; };
const same = (a, b) => JSON.stringify(a) === JSON.stringify(b);
const throwsMsg = (fn, re) => { try { fn(); return false; } catch (e) { return re.test(e.message); } };

/** Fresh game context. store = the fake localStorage (a Map of 'redskies.v1.' + key → JSON text); failOn(key) → that write throws. */
function fresh(failOn) {
  const ctx = { console, Math, JSON, Object, Array, String, Number, isFinite, Date, Map, Error };
  ctx.window = ctx; ctx.globalThis = ctx; ctx.RS = {};
  vm.createContext(ctx);
  for (const f of ['contracts.js', 'content.js', 'campaign.js', 'savecode.js']) vm.runInContext(src(f), ctx, { filename: f });
  const RS = ctx.window.RS, store = new Map(), P = 'redskies.v1.';
  RS.VERSION = '1.4.5.0';
  RS.save = (k, v) => { if (failOn && failOn(k)) return false; store.set(P + k, JSON.stringify(v)); return true; };
  RS.load = (k, fb) => (store.has(P + k) ? JSON.parse(store.get(P + k)) : fb);
  RS.remove = k => { store.delete(P + k); return true; };
  const dump = () => Object.fromEntries([...store].sort());
  return { RS, store, dump };
}

/* a well-played save: shift 4 next, 40 results, medals, variants, survival board, free watch setup, training done */
function seed(RS) {
  const results = [];
  for (let i = 0; i < 40; i++) results.push({ id: 'C' + (1 + i % 3), grade: 'ABCDF'[i % 5], score: 40 + i, at: 1760000000000 + i * 3600e3 });
  RS.save('campaign', { next: 3, unlocked: 4, best: { C1: 'A', C2: 'B', C3: 'C' }, results, reserve: { lance: 9, dart: 6, harrow: 900 },
    pending: { idx: 3, credits: 140 }, bank: 12, medals: { C1: ['clean', 'iron'], C3: ['quiet'] }, vpick: { 3: 'B' }, vlast: { 0: 'A', 1: 'C', 2: 'A' } });
  RS.save('settings', { sound: false, haptics: true, voice: true });
  RS.save('free', { seed: 4242, diff: 0.8, dur: 360, ev: { night: true, storm: false }, time: 'night', sky: 'rain' });
  RS.save('survival', { seed: 777, best: [{ score: 12650, waves: 11, kills: 15, seed: 777, at: 1760001000000 }, { score: 5300, waves: 4, kills: 12, seed: 31, at: 1760002000000 }] });
  RS.save('tutorial', { done: true });
}

console.log('round trip');
{
  const a = fresh();
  seed(a.RS);
  const before = a.dump(), code = a.RS.savecode.make();
  console.log('  INFO code ' + code.length + ' chars (JSON ' + JSON.stringify(before).length + ')');
  ok(/^RS1:[A-Za-z0-9_-]+$/.test(code), 'code is RS1: + base64url only (safe to paste in chat apps)');
  ok(code.length < 1500, 'a 40-result save stays short (' + code.length + ' chars)');
  const b = fresh();                                   // another phone: nothing saved yet
  const data = b.RS.savecode.read(code);
  ok(data.v === 1 && data.ver === '1.4.5.0' && data.at > 0 && Object.keys(data.d).length === 5, 'read: version, time and all 5 keys');
  const r = b.RS.savecode.apply(data);
  ok(r.ok && r.stored, 'apply: stored');
  ok(same(b.dump(), before), 'restored storage is identical to the original, key by key');
  ok(b.RS.savecode.make().length > 0 && same(b.RS.savecode.read(b.RS.savecode.make()).d, data.d), 'a code made after restoring holds the same data');
  const sum = b.RS.savecode.summary(data);
  ok(sum[0] === 'Campaign: shift 4 of 6' && /Survival: 2 best runs, top wave 11/.test(sum[1]) && sum.includes('Training: done'), 'summary: ' + sum.join(' | '));
  // pasted with line breaks, spaces, zero-width characters and chat text around it
  const messy = 'my code: "' + code.slice(0, 30) + '\n  ' + code.slice(30, 61) + '​ ' + code.slice(61) + '" thanks';
  ok(same(b.RS.savecode.read(messy).d, data.d), 'spaces, line breaks and text around the code are ignored');
  // restoring replaces: a key the code has no value for is removed
  const c = fresh();
  c.RS.save('campaign', { next: 1 }); c.RS.save('tutorial', { done: true });
  const partial = c.RS.savecode.make();
  seed(b.RS);
  b.RS.savecode.apply(b.RS.savecode.read(partial));
  ok(same(b.dump(), c.dump()), 'keys missing from the code are removed on restore (' + Object.keys(b.dump()).join(', ') + ')');
}

console.log('empty save');
{
  const a = fresh(), code = a.RS.savecode.make();
  ok(/^RS1:/.test(code) && code.length < 120, 'a fresh device still makes a code (' + code + ')');
  const data = a.RS.savecode.read(code);
  ok(same(data.d, {}), 'empty code holds no keys');
  ok(a.RS.savecode.summary(data)[0] === 'Campaign: not started', 'summary says not started');
  const b = fresh(); seed(b.RS);
  b.RS.savecode.apply(data);
  ok(b.store.size === 0, 'restoring an empty code leaves a fresh device (nothing saved)');
  ok(throwsMsg(() => a.RS.savecode.read(''), /Paste a save code first/) && throwsMsg(() => a.RS.savecode.read('  \n '), /Paste a save code first/), 'empty paste: "Paste a save code first."');
}

console.log('damaged codes are rejected');
{
  const a = fresh(); seed(a.RS);
  const code = a.RS.savecode.make(), D = /damaged or incomplete/;
  const mid = Math.floor(code.length / 2), swap = ch => (ch === 'A' ? 'B' : 'A');
  const cases = {
    'one character changed': code.slice(0, mid) + swap(code[mid]) + code.slice(mid + 1),
    'one character missing': code.slice(0, mid) + code.slice(mid + 1),
    'cut off at the end': code.slice(0, -10),
    'only the first half': code.slice(0, mid),
    'checksum changed': code.slice(0, -1) + swap(code.slice(-1)),
    'prefix only': 'RS1:',
    'random text': 'hello there'
  };
  for (const k in cases) ok(throwsMsg(() => a.RS.savecode.read(cases[k]), D), k + ' → damaged message');
  // every single-character change in the body is caught (checksum), never a crash or a wrong save
  let caught = 0, n = 0;
  for (let i = 4; i < code.length; i += 7) { n++; if (throwsMsg(() => a.RS.savecode.read(code.slice(0, i) + swap(code[i]) + code.slice(i + 1)), D)) caught++; }
  ok(caught === n, `every sampled one-character change rejected (${caught}/${n})`);
  // a code with a good checksum but the wrong shape inside is rejected before anything is written
  const S = a.RS.savecode, b = fresh(); seed(b.RS);
  const keep = b.dump();
  const bad = [
    { v: 1, d: { campaign: { next: 'lots' } } },
    { v: 1, d: { campaign: { best: { C1: 'Z' } } } },
    { v: 1, d: { campaign: { reserve: { lance: -1, dart: 2, harrow: 3 } } } },
    { v: 1, d: { settings: { sound: 'yes' } } },
    { v: 1, d: { survival: { best: [{ waves: 3 }] } } },
    { v: 1, d: { tutorial: [true] } },
    { v: 1, d: [] }, { v: 1 }, { d: {} }, [1, 2], 'text'
  ];
  bad.forEach(o => ok(throwsMsg(() => b.RS.savecode.apply(b.RS.savecode.read(S.encode(o))), D) && same(b.dump(), keep), 'bad shape rejected, nothing written: ' + JSON.stringify(o)));
  ok(same(b.RS.savecode.read(S.encode({ v: 1, d: { campaign: { next: 2 }, extra: { x: 1 } } })).d, { campaign: { next: 2 } }), 'unknown keys inside a v1 code are ignored');
}

console.log('broken stored data');
{
  const a = fresh(); seed(a.RS);
  a.RS.save('campaign', { next: 'three' });            // a broken value in storage is reported, never packed
  const skipped = [], data = a.RS.savecode.read(a.RS.savecode.make(skipped));
  ok(same(skipped, ['campaign']) && !data.d.campaign && Object.keys(data.d).length === 4, 'broken campaign left out and reported: ' + skipped.join(', '));
}

console.log('wrong game / newer version');
{
  const a = fresh(); seed(a.RS);
  const code = a.RS.savecode.make(), body = code.slice(4), O = /different game/;
  ok(throwsMsg(() => a.RS.savecode.read('GG1:' + body), O), 'GG1: (Garage to Glory) code → "different game"');
  ok(throwsMsg(() => a.RS.savecode.read('XYZ7:' + body), O), 'other prefix → "different game"');
  ok(throwsMsg(() => a.RS.savecode.read('RS2:' + body), /newer version/), 'RS2: code → "newer version"');
  ok(throwsMsg(() => a.RS.savecode.read(a.RS.savecode.encode({ v: 2, d: {} })), /newer version/), 'RS1 code holding a v2 save → "newer version"');
}

console.log('all or nothing');
{
  const a = fresh(); seed(a.RS);
  const code = a.RS.savecode.make();
  let n = 0;
  const b = fresh(k => k === 'survival' && ++n === 1);   // the survival write fails once (storage full), the rollback works
  b.RS.save('campaign', { next: 1 }); b.RS.save('settings', { sound: true, haptics: false });
  const keep = b.dump();
  ok(throwsMsg(() => b.RS.savecode.apply(b.RS.savecode.read(code)), /nothing was changed/), 'a failed write reports "nothing was changed"');
  ok(same(b.dump(), keep), 'old progress put back after a failed write');
  const c = fresh(() => true);                          // storage blocked: every write fails
  ok(c.RS.savecode.apply(c.RS.savecode.read(code)).stored === false, 'storage blocked: restore reports stored:false (this visit only)');
}

console.log('packing');
{
  const { RS } = fresh(), S = RS.savecode;
  const odd = { v: 1, d: {}, s: 'Ünïcödé ✓ 🚀 ' + 'abcabcabc'.repeat(300) + '"\\\n' };
  ok(same(S.decode(S.encode(odd)), odd), 'UTF-8 + long repeats round trip');
  const big = { v: 1, d: {}, n: Array.from({ length: 3000 }, (_, i) => (i * 7919) % 10007) };
  ok(same(S.decode(S.encode(big)), big), 'a large payload round trips (LZW codes past 12 bits)');
}

console.log(`\n${checks - fails}/${checks} checks passed`);
process.exit(fails ? 1 : 0);
