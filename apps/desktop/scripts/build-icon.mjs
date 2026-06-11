import { execFileSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import zlib from "node:zlib";

const desktopRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const assetsRoot = path.join(desktopRoot, "assets");
const sourceSvg = path.join(assetsRoot, "icon.svg");
const buildRoot = path.join(assetsRoot, ".icon-build");
const iconsetRoot = path.join(buildRoot, "icon.iconset");
const outputIcns = path.join(assetsRoot, "icon.icns");

const iconFiles = [
  ["icp4", "icon_16x16.png", 16],
  ["ic11", "icon_16x16@2x.png", 32],
  ["icp5", "icon_32x32.png", 32],
  ["ic12", "icon_32x32@2x.png", 64],
  ["ic07", "icon_128x128.png", 128],
  ["ic13", "icon_128x128@2x.png", 256],
  ["ic08", "icon_256x256.png", 256],
  ["ic14", "icon_256x256@2x.png", 512],
  ["ic09", "icon_512x512.png", 512],
  ["ic10", "icon_512x512@2x.png", 1024],
];

const palette = {
  background: [243, 241, 235, 255],
  coverTop: [33, 77, 69, 255],
  coverBottom: [240, 184, 90, 255],
  pageTop: [255, 254, 250, 255],
  pageBottom: [232, 238, 232, 255],
  ink: [33, 77, 69, 255],
  muted: [124, 144, 136, 255],
  gold: [240, 184, 90, 255],
  shadow: [16, 33, 31, 54],
};

function ensureTool(name) {
  try {
    execFileSync("which", [name], { stdio: "ignore" });
  } catch {
    throw new Error(`Required macOS tool not found: ${name}`);
  }
}

function clean() {
  fs.rmSync(buildRoot, { recursive: true, force: true });
  fs.mkdirSync(iconsetRoot, { recursive: true });
}

function crc32(buffer) {
  let crc = 0xffffffff;
  for (const byte of buffer) {
    crc ^= byte;
    for (let bit = 0; bit < 8; bit += 1) {
      crc = (crc >>> 1) ^ (0xedb88320 & -(crc & 1));
    }
  }
  return (crc ^ 0xffffffff) >>> 0;
}

function chunk(type, data) {
  const typeBuffer = Buffer.from(type);
  const length = Buffer.alloc(4);
  length.writeUInt32BE(data.length);
  const crc = Buffer.alloc(4);
  crc.writeUInt32BE(crc32(Buffer.concat([typeBuffer, data])));
  return Buffer.concat([length, typeBuffer, data, crc]);
}

function writePng(file, width, height, rgba) {
  const stride = width * 4;
  const raw = Buffer.alloc((stride + 1) * height);
  for (let y = 0; y < height; y += 1) {
    raw[y * (stride + 1)] = 0;
    rgba.copy(raw, y * (stride + 1) + 1, y * stride, y * stride + stride);
  }

  const ihdr = Buffer.alloc(13);
  ihdr.writeUInt32BE(width, 0);
  ihdr.writeUInt32BE(height, 4);
  ihdr[8] = 8;
  ihdr[9] = 6;
  ihdr[10] = 0;
  ihdr[11] = 0;
  ihdr[12] = 0;

  fs.writeFileSync(
    file,
    Buffer.concat([
      Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]),
      chunk("IHDR", ihdr),
      chunk("IDAT", zlib.deflateSync(raw, { level: 9 })),
      chunk("IEND", Buffer.alloc(0)),
    ]),
  );
}

function writeIcns(file, entries) {
  const blocks = entries.map(([type, png]) => {
    const data = fs.readFileSync(png);
    const header = Buffer.alloc(8);
    header.write(type, 0, 4, "ascii");
    header.writeUInt32BE(data.length + 8, 4);
    return Buffer.concat([header, data]);
  });
  const totalLength = blocks.reduce((sum, block) => sum + block.length, 8);
  const header = Buffer.alloc(8);
  header.write("icns", 0, 4, "ascii");
  header.writeUInt32BE(totalLength, 4);
  fs.writeFileSync(file, Buffer.concat([header, ...blocks]));
}

function mix(a, b, t) {
  return a.map((value, index) => Math.round(value + (b[index] - value) * t));
}

function blendPixel(buffer, width, x, y, color) {
  if (x < 0 || y < 0 || x >= width || y >= width) return;
  const offset = (y * width + x) * 4;
  const alpha = color[3] / 255;
  const inverse = 1 - alpha;
  buffer[offset] = Math.round(color[0] * alpha + buffer[offset] * inverse);
  buffer[offset + 1] = Math.round(color[1] * alpha + buffer[offset + 1] * inverse);
  buffer[offset + 2] = Math.round(color[2] * alpha + buffer[offset + 2] * inverse);
  buffer[offset + 3] = 255;
}

function inRoundedRect(x, y, rect) {
  const { left, top, right, bottom, radius } = rect;
  if (x < left || x > right || y < top || y > bottom) return false;
  const cx = x < left + radius ? left + radius : x > right - radius ? right - radius : x;
  const cy = y < top + radius ? top + radius : y > bottom - radius ? bottom - radius : y;
  return (x - cx) ** 2 + (y - cy) ** 2 <= radius ** 2;
}

function fillRoundedRect(buffer, size, rect, colorForPoint) {
  const left = Math.max(0, Math.floor(rect.left * size));
  const top = Math.max(0, Math.floor(rect.top * size));
  const right = Math.min(size - 1, Math.ceil(rect.right * size));
  const bottom = Math.min(size - 1, Math.ceil(rect.bottom * size));
  const scaled = {
    left: rect.left * size,
    top: rect.top * size,
    right: rect.right * size,
    bottom: rect.bottom * size,
    radius: rect.radius * size,
  };

  for (let y = top; y <= bottom; y += 1) {
    for (let x = left; x <= right; x += 1) {
      if (inRoundedRect(x, y, scaled)) {
        blendPixel(buffer, size, x, y, colorForPoint(x / size, y / size));
      }
    }
  }
}

function strokeLine(buffer, size, start, end, width, color) {
  const sx = start[0] * size;
  const sy = start[1] * size;
  const ex = end[0] * size;
  const ey = end[1] * size;
  const radius = (width * size) / 2;
  const left = Math.floor(Math.min(sx, ex) - radius);
  const right = Math.ceil(Math.max(sx, ex) + radius);
  const top = Math.floor(Math.min(sy, ey) - radius);
  const bottom = Math.ceil(Math.max(sy, ey) + radius);
  const dx = ex - sx;
  const dy = ey - sy;
  const lengthSq = dx * dx + dy * dy;

  for (let y = top; y <= bottom; y += 1) {
    for (let x = left; x <= right; x += 1) {
      const t = Math.max(0, Math.min(1, ((x - sx) * dx + (y - sy) * dy) / lengthSq));
      const px = sx + t * dx;
      const py = sy + t * dy;
      if ((x - px) ** 2 + (y - py) ** 2 <= radius ** 2) {
        blendPixel(buffer, size, x, y, color);
      }
    }
  }
}

function drawIcon(size) {
  const buffer = Buffer.alloc(size * size * 4);
  for (let y = 0; y < size; y += 1) {
    for (let x = 0; x < size; x += 1) {
      blendPixel(buffer, size, x, y, palette.background);
    }
  }

  fillRoundedRect(buffer, size, { left: 0.25, top: 0.2, right: 0.81, bottom: 0.86, radius: 0.1 }, () => palette.shadow);
  fillRoundedRect(buffer, size, { left: 0.22, top: 0.17, right: 0.78, bottom: 0.83, radius: 0.1 }, (_x, y) =>
    mix(palette.coverTop, palette.coverBottom, Math.min(1, Math.max(0, (y - 0.17) / 0.66))),
  );
  fillRoundedRect(buffer, size, { left: 0.31, top: 0.23, right: 0.72, bottom: 0.75, radius: 0.07 }, (_x, y) =>
    mix(palette.pageTop, palette.pageBottom, Math.min(1, Math.max(0, (y - 0.23) / 0.52))),
  );

  strokeLine(buffer, size, [0.4, 0.33], [0.63, 0.33], 0.027, palette.ink);
  strokeLine(buffer, size, [0.4, 0.43], [0.62, 0.43], 0.023, palette.muted);
  strokeLine(buffer, size, [0.4, 0.52], [0.64, 0.52], 0.023, palette.muted);
  strokeLine(buffer, size, [0.4, 0.61], [0.55, 0.61], 0.023, palette.muted);
  strokeLine(buffer, size, [0.34, 0.75], [0.49, 0.72], 0.03, palette.gold);
  strokeLine(buffer, size, [0.49, 0.72], [0.65, 0.75], 0.03, palette.gold);

  return buffer;
}

if (!fs.existsSync(sourceSvg)) {
  throw new Error(`Missing SVG source: ${sourceSvg}`);
}

ensureTool("sips");
clean();
const icnsEntries = [];
for (const [type, name, size] of iconFiles) {
  const iconPath = path.join(iconsetRoot, name);
  writePng(iconPath, size, size, drawIcon(size));
  execFileSync("sips", ["-s", "format", "png", iconPath, "--out", iconPath], { stdio: "ignore" });
  icnsEntries.push([type, iconPath]);
}
writeIcns(outputIcns, icnsEntries);
fs.rmSync(buildRoot, { recursive: true, force: true });
console.log(`Wrote ${outputIcns}`);
