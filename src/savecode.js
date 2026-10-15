/* =====================================================================
   RED SKIES — savecode.js   RS.savecode : copy-paste save codes (back up progress, restore it on another phone or browser).
   No DOM and no network: it only reads and writes the save keys through RS.load / RS.save / RS.remove (main.js).
   Code format:  'RS1:' + base64url(LZW(UTF-8(JSON))) + 6-char checksum of 'RS1:' + body
     JSON = { v: 1, ver: game version, at: ms when made, d: { campaign?, settings?, free?, survival?, tutorial? } }
     A key missing from `d` means "nothing saved yet" for it; restoring removes that key, so the device ends up the same.
   The format matches the Garage to Glory save codes (GG1:), with its own prefix so the games never mix codes up.
   API:
     make(skipped?)  -> 'RS1:…'   the code for everything saved on this device right now (keys whose stored value
                                  looks broken are left out and pushed onto the optional `skipped` array, so the UI can say so)
     read(text)      -> { v, ver, at, d }   checked and cleaned; throws Error(friendly message) and never writes anything
     apply(data)     -> { ok:true, stored:boolean }   writes every key (stored false = storage blocked, this visit only);
                        throws Error(friendly message) and puts the old progress back if some writes fail
     summary(data)   -> ['Campaign: shift 3 of 6', …]   short lines for the confirm box
     collect(skipped?) -> the `d` object make() packs (exported for tests)
     encode(obj) / decode(text): the raw packing, without the shape check (tests)
   ===================================================================== */
(function () {
  const RS = window.RS;
  const PREFIX = 'RS1:';
  const KEYS = ['campaign', 'settings', 'free', 'survival', 'tutorial'];   // every RS.save key the game writes (meta.js, tutorial.js)
  const MSG = {
    empty: 'Paste a save code first.',
    damaged: 'That save code is damaged or incomplete. Copy the whole code and try again.',
    other: 'That code is for a different game. Red Skies save codes start with RS1:',
    newer: 'That code comes from a newer version of Red Skies. Update the game, then try again.',
    full: "Couldn't save the code on this device, so nothing was changed. Free up some browser storage and try again."
  };

  /* ---------- packing: UTF-8 -> LZW (9..16-bit codes) -> base64url (same scheme as the Garage to Glory codes) ---------- */
  const B64 = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_';
  const B64_INDEX = {};
  for (let i = 0; i < B64.length; i++) B64_INDEX[B64.charAt(i)] = i;
  const MAX_CODES = 65536;

  function utf8Encode(str) {
    const out = [];
    for (let i = 0; i < str.length; i++) {
      let c = str.charCodeAt(i);
      if (c >= 0xD800 && c <= 0xDBFF && i + 1 < str.length) {          // surrogate pair -> one code point
        const lo = str.charCodeAt(i + 1);
        if (lo >= 0xDC00 && lo <= 0xDFFF) { c = 0x10000 + ((c - 0xD800) << 10) + (lo - 0xDC00); i++; }
      }
      if (c < 0x80) out.push(c);
      else if (c < 0x800) out.push(0xC0 | c >> 6, 0x80 | c & 63);
      else if (c < 0x10000) out.push(0xE0 | c >> 12, 0x80 | c >> 6 & 63, 0x80 | c & 63);
      else out.push(0xF0 | c >> 18, 0x80 | c >> 12 & 63, 0x80 | c >> 6 & 63, 0x80 | c & 63);
    }
    return out;
  }
  function utf8Decode(bytes) {
    let s = '', i = 0;
    while (i < bytes.length) {
      const b = bytes[i++];
      let c;
      if (b < 0x80) c = b;
      else if (b < 0xE0) c = (b & 31) << 6 | bytes[i++] & 63;
      else if (b < 0xF0) c = (b & 15) << 12 | (bytes[i++] & 63) << 6 | bytes[i++] & 63;
      else c = (b & 7) << 18 | (bytes[i++] & 63) << 12 | (bytes[i++] & 63) << 6 | bytes[i++] & 63;
      if (c > 0xFFFF) { c -= 0x10000; s += String.fromCharCode(0xD800 + (c >> 10), 0xDC00 + (c & 1023)); }
      else s += String.fromCharCode(c);
    }
    return s;
  }
  function bitLength(n) { let b = 1; while (n >= 2) { n = n >>> 1; b++; } return b; }

  // bits are packed most significant first into 6-bit base64url characters; the tail is zero-padded
  function bitWriter() {
    const out = [];
    let acc = 0, nacc = 0;
    return {
      write(value, width) {
        for (let i = width - 1; i >= 0; i--) {
          acc = acc << 1 | (value >>> i & 1);
          if (++nacc === 6) { out.push(B64.charAt(acc)); acc = 0; nacc = 0; }
        }
      },
      finish() { if (nacc) out.push(B64.charAt(acc << (6 - nacc))); return out.join(''); }
    };
  }
  function bitReader(str) {
    let pos = 0;
    const total = str.length * 6;
    return {
      left: () => total - pos,
      read(width) {
        let v = 0;
        for (let i = 0; i < width; i++, pos++) {
          const d = B64_INDEX[str.charAt(pos / 6 | 0)];
          if (d === undefined) throw new Error('bad char');
          v = v * 2 + (d >> (5 - pos % 6) & 1);
        }
        return v;
      }
    };
  }
  // LZW over bytes. The code width is the bit length of the largest code the decoder could see next.
  function compress(bytes) {
    const w = bitWriter();
    if (!bytes.length) return w.finish();
    const dict = new Map();
    let next = 256, cur = bytes[0];
    for (let i = 1; i < bytes.length; i++) {
      const key = cur * 256 + bytes[i], hit = dict.get(key);
      if (hit !== undefined) { cur = hit; continue; }
      w.write(cur, bitLength(next - 1));
      if (next < MAX_CODES) dict.set(key, next++);
      cur = bytes[i];
    }
    w.write(cur, bitLength(next - 1));
    return w.finish();
  }
  function decompress(str) {
    const r = bitReader(str), out = [];
    if (r.left() < 8) return out;
    const prefix = [], suffix = [], first = [];
    let size = 256;
    for (let i = 0; i < 256; i++) { prefix.push(-1); suffix.push(i); first.push(i); }
    const emit = code => {                    // appends the bytes of `code` to out
      const start = out.length;
      while (code >= 0) { out.push(suffix[code]); code = prefix[code]; }
      for (let a = start, b = out.length - 1; a < b; a++, b--) { const t = out[a]; out[a] = out[b]; out[b] = t; }
    };
    let prev = r.read(8);
    if (prev > 255) throw new Error('bad code');
    emit(prev);
    for (;;) {
      const width = bitLength(Math.min(size, MAX_CODES - 1));
      if (r.left() < width) break;           // what's left is padding
      const code = r.read(width);
      let firstByte;
      if (code < size) firstByte = first[code];
      else if (code === size) firstByte = first[prev];   // the "KwKwK" case: the code being defined right now
      else throw new Error('bad code');
      if (size < MAX_CODES) { prefix.push(prev); suffix.push(firstByte); first.push(first[prev]); size++; }
      emit(code);
      prev = code;
    }
    return out;
  }
  // FNV-1a hash of the prefix + body, as 6 base64url characters: a typo, a lost chunk or a cut-off end changes it
  function checksum(body) {
    const str = PREFIX + body;
    let h = 2166136261 >>> 0;
    for (let i = 0; i < str.length; i++) { h ^= str.charCodeAt(i); h = Math.imul(h, 16777619) >>> 0; }
    let s = '';
    for (let i = 0; i < 6; i++) { s += B64.charAt(h & 63); h = Math.floor(h / 64); }
    return s;
  }
  function encode(obj) { const body = compress(utf8Encode(JSON.stringify(obj))); return PREFIX + body + checksum(body); }
  /** Code text -> parsed JSON. Tolerates spaces, line breaks, zero-width characters and text around the code. */
  function decode(text) {
    let s = String(text == null ? '' : text).replace(/[\s​-‍⁠﻿]+/g, '');
    if (!s) throw new Error(MSG.empty);
    const at = s.indexOf(PREFIX);
    if (at < 0) {
      const m = /RS(\d+):/.exec(s);
      if (m && +m[1] > 1) throw new Error(MSG.newer);
      if (/[A-Za-z]{2,4}\d+:/.test(s)) throw new Error(MSG.other);   // e.g. a Garage to Glory GG1: code
      throw new Error(MSG.damaged);
    }
    s = s.slice(at + PREFIX.length).replace(/[^A-Za-z0-9_-].*$/, '');   // drop trailing quotes or punctuation
    if (s.length < 7) throw new Error(MSG.damaged);
    const body = s.slice(0, -6);
    if (checksum(body) !== s.slice(-6)) throw new Error(MSG.damaged);
    try { return JSON.parse(utf8Decode(decompress(body))); } catch (e) { throw new Error(MSG.damaged); }
  }

  /* ---------- shape check: every saved value must look like what meta.js / tutorial.js write ----------
     Fields may be missing (meta fills in defaults), but a field that is there must have the right type. */
  const isObj = v => !!v && typeof v === 'object' && !Array.isArray(v);
  const num = (v, lo, hi) => typeof v === 'number' && isFinite(v) && v >= lo && v <= hi;
  const int = (v, lo, hi) => num(v, lo, hi) && Math.floor(v) === v;
  const str = (v, max) => typeof v === 'string' && v.length <= max;
  const bool = v => typeof v === 'boolean';
  const grade = v => typeof v === 'string' && /^[A-F]$/.test(v);
  const opt = (v, test) => v === undefined || test(v);
  const BAD_KEYS = ['__proto__', 'constructor', 'prototype'];
  const mapOf = (o, test) => isObj(o) && Object.keys(o).length <= 60 && Object.keys(o).every(k => k.length <= 24 && !BAD_KEYS.includes(k) && test(o[k]));
  const listOf = (a, max, test) => Array.isArray(a) && a.length <= max && a.every(test);
  const W3 = ['lance', 'dart', 'harrow'];
  const CHECK = {
    // 'campaign' {next, unlocked, best:{id:grade}, results[], reserve, pending, bank, medals:{id:[medalId]}, vpick, vlast}
    campaign: c => isObj(c) && opt(c.next, v => int(v, 0, 99)) && opt(c.unlocked, v => int(v, 0, 99)) &&
      opt(c.best, o => mapOf(o, grade)) &&
      opt(c.results, a => listOf(a, 200, r => isObj(r) && opt(r.id, v => str(v, 24)) && opt(r.grade, grade) && opt(r.score, v => num(v, -1e6, 1e6)) && opt(r.at, v => num(v, 0, 1e14)))) &&
      opt(c.reserve, r => isObj(r) && W3.every(w => num(r[w], 0, 1e6))) &&
      opt(c.pending, p => p === null || (isObj(p) && int(p.idx, 0, 99) && num(p.credits, -1e7, 1e7))) &&
      opt(c.bank, v => num(v, 0, 1e7)) &&
      opt(c.medals, o => mapOf(o, a => listOf(a, 20, m => str(m, 24)))) &&
      opt(c.vpick, o => mapOf(o, v => str(v, 8))) && opt(c.vlast, o => mapOf(o, v => str(v, 8))),
    // 'settings' {sound, haptics, voice}
    settings: s => isObj(s) && ['sound', 'haptics', 'voice'].every(k => opt(s[k], bool)),
    // 'free' {seed, diff, dur, ev:{}, time, sky}
    free: f => isObj(f) && opt(f.seed, v => num(v, 0, 1e9)) && opt(f.diff, v => num(v, 0, 1)) && opt(f.dur, v => num(v, 0, 1e5)) &&
      opt(f.ev, o => mapOf(o, bool)) && opt(f.time, v => str(v, 16)) && opt(f.sky, v => str(v, 16)),
    // 'survival' {seed, best:[{score, waves, kills, seed, at}]}
    survival: s => isObj(s) && opt(s.seed, v => num(v, 0, 1e9)) &&
      opt(s.best, a => listOf(a, 50, b => isObj(b) && num(b.score, -1e9, 1e9) && ['waves', 'kills', 'seed', 'at'].every(k => opt(b[k], v => num(v, 0, 1e14))))),
    // 'tutorial' {done}
    tutorial: t => isObj(t) && opt(t.done, bool)
  };

  /** Everything saved on this device, keyed like `d` in the code. Values that fail the shape check are left out
      (and their key pushed onto `skipped` when it is given). */
  function collect(skipped) {
    const d = {};
    for (const k of KEYS) {
      let v = null;
      try { v = RS.load ? RS.load(k, null) : null; } catch (e) { v = null; }
      if (v == null) continue;
      if (CHECK[k](v)) d[k] = v; else if (Array.isArray(skipped)) skipped.push(k);
    }
    return d;
  }
  function make(skipped) { return encode({ v: 1, ver: RS.VERSION || '', at: Date.now(), d: collect(skipped) }); }

  /** Read and check a pasted code. Returns { v, ver, at, d } with only known keys; throws Error(friendly message). */
  function read(text) {
    const obj = decode(text);
    if (!isObj(obj) || typeof obj.v !== 'number') throw new Error(MSG.damaged);
    if (obj.v > 1) throw new Error(MSG.newer);
    if (obj.v !== 1 || !isObj(obj.d)) throw new Error(MSG.damaged);
    const d = {};
    for (const k of KEYS) {
      const v = obj.d[k];
      if (v == null) continue;
      if (!CHECK[k](v)) throw new Error(MSG.damaged);
      d[k] = v;
    }
    return { v: 1, ver: str(obj.ver, 32) ? obj.ver : '', at: num(obj.at, 0, 1e14) ? obj.at : 0, d };
  }

  // one key -> storage: a value is saved, a missing one removed. true = it reached localStorage.
  const put = (k, v) => (v == null ? (RS.remove ? RS.remove(k) : RS.save(k, null)) : RS.save(k, v));
  /** Replace this device's progress with a code's data (from read()). All or nothing. */
  function apply(data) {
    if (!data || !isObj(data.d) || !RS.save) throw new Error(MSG.damaged);
    const before = collect(), done = [];
    let stored = 0;
    for (const k of KEYS) { const ok = put(k, data.d[k]); done.push(k); if (ok) stored++; }
    if (stored > 0 && stored < KEYS.length) {              // some writes failed (storage full): put the old progress back
      for (const k of done) put(k, before[k]);
      throw new Error(MSG.full);
    }
    return { ok: true, stored: stored === KEYS.length };
  }

  /** Short plain lines describing a code's data, for the confirm box before restoring. */
  function summary(data) {
    const d = (data && data.d) || {}, out = [], c = d.campaign, n = (RS.campaign && RS.campaign.shifts.length) || 6;
    if (c) {
      const next = typeof c.next === 'number' ? c.next : Math.max(0, (c.unlocked || 1) - 1);
      out.push(next >= n ? `Campaign: complete (${n} of ${n} shifts)` : `Campaign: shift ${next + 1} of ${n}`);
    } else out.push('Campaign: not started');
    const runs = (d.survival && d.survival.best) || [];
    if (runs.length) out.push(`Survival: ${runs.length} best run${runs.length === 1 ? '' : 's'}, top wave ${Math.max(...runs.map(b => b.waves || 0))}`);
    if (d.tutorial && d.tutorial.done) out.push('Training: done');
    if (data && data.at) {
      try { out.push('Made on ' + new Date(data.at).toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric' })); } catch (e) { /* no Intl */ }
    }
    return out;
  }

  RS.savecode = { PREFIX, KEYS, MSG, make, read, apply, summary, collect, encode, decode };
})();
