// Reproducible raster exports from the original FERRAVIS vector, using Next's sharp dependency.
const fs = require('node:fs/promises');
const path = require('node:path');
const sharp = require('sharp');
const root = path.join(__dirname, '../public');
(async () => {
  const svg = await fs.readFile(path.join(root, 'ferravis-mark.svg'), 'utf8');
  for (const size of [192, 512]) {
    await fs.writeFile(path.join(root, `icon-${size}.svg`), svg.replace('viewBox=', `width="${size}" height="${size}" viewBox=`));
    await sharp(Buffer.from(svg)).resize(size, size).png().toFile(path.join(root, `icon-${size}.png`));
  }
  // iOS and maskable launchers supply the outside shape; keep the mark in the safe central 80% circle.
  const tile = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512"><rect width="512" height="512" fill="#171719"/><svg x="64" y="64" width="384" height="384" viewBox="0 0 64 64">${svg.replace(/^<svg[^>]*>/, '').replace(/<\/svg>\s*$/, '')}</svg></svg>`;
  await sharp(Buffer.from(tile)).resize(512, 512).png().toFile(path.join(root, 'icon-maskable-512.png'));
  await sharp(Buffer.from(tile)).resize(180, 180).png().toFile(path.join(root, 'apple-touch-icon.png'));
  await sharp(Buffer.from(svg)).resize(32, 32).png().toFile(path.join(root, 'favicon-32.png'));
})().catch(error => { console.error(error); process.exitCode = 1; });
