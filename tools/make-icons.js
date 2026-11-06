#!/usr/bin/env node
/* RED SKIES: render icons/icon.svg into the home-screen PNGs (run by hand after editing the SVG; output is committed).
   Needs Playwright with Chromium (npm ci + npx playwright install chromium). node tools/make-icons.js */
const fs = require('fs'), path = require('path');
const { chromium } = require('playwright');
const ROOT = path.join(__dirname, '..'), DIR = path.join(ROOT, 'icons');
const svg = fs.readFileSync(path.join(DIR, 'icon.svg'), 'utf8');
// [file, size, art scale]: the maskable one shrinks the art into the middle 80 %, so Android's mask never clips it
const OUT = [['apple-touch-icon.png', 180, 1], ['icon-192.png', 192, 1], ['icon-512.png', 512, 1], ['icon-512-maskable.png', 512, 0.8]];
(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage();
  for (const [file, size, scale] of OUT) {
    await page.setViewportSize({ width: size, height: size });
    // the background stays full-bleed; only <g id="art"> shrinks about the centre
    const off = 256 * (1 - scale), src = svg.replace('<g id="art">', `<g id="art" transform="translate(${off} ${off}) scale(${scale})">`);
    const img = `<img src="data:image/svg+xml;base64,${Buffer.from(src).toString('base64')}" width="${size}" height="${size}" style="display:block">`;
    await page.setContent(`<html><body style="margin:0;background:#050707">${img}</body></html>`);
    await page.waitForFunction(() => document.images[0].complete);
    await page.screenshot({ path: path.join(DIR, file), omitBackground: false });
    // the PNGs were then squeezed to 256 colours with Pillow (quantize + optimize) to keep them small
    console.log(file, size, fs.statSync(path.join(DIR, file)).size + ' bytes');
  }
  await browser.close();
})();
