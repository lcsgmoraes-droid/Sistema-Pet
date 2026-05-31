const fs = require("fs");
const path = require("path");
const { PNG } = require("pngjs");

const BRAND = {
  teal: [15, 95, 102, 255],
  white: [255, 255, 255, 255],
};

const SOURCE_ICON = path.resolve(__dirname, "../frontend/public/brand/corepet/corepet-icon-1024.png");
const ASSET_DIR = path.resolve(__dirname, "assets");

function readPng(file) {
  return PNG.sync.read(fs.readFileSync(file));
}

function writePng(file, image) {
  fs.writeFileSync(file, PNG.sync.write(image));
}

function setPixel(image, x, y, rgba) {
  const index = (y * image.width + x) * 4;
  image.data[index] = rgba[0];
  image.data[index + 1] = rgba[1];
  image.data[index + 2] = rgba[2];
  image.data[index + 3] = rgba[3];
}

function getPixel(image, x, y) {
  const index = (y * image.width + x) * 4;
  return [
    image.data[index],
    image.data[index + 1],
    image.data[index + 2],
    image.data[index + 3],
  ];
}

function makeCanvas(width, height, fill) {
  const image = new PNG({ width, height });
  for (let y = 0; y < height; y += 1) {
    for (let x = 0; x < width; x += 1) {
      setPixel(image, x, y, fill);
    }
  }
  return image;
}

function cropToMark(image) {
  let minX = image.width;
  let minY = image.height;
  let maxX = 0;
  let maxY = 0;

  for (let y = 0; y < image.height; y += 1) {
    for (let x = 0; x < image.width; x += 1) {
      const [r, g, b] = getPixel(image, x, y);
      const isBackground = r > 245 && g > 245 && b > 245;
      if (!isBackground) {
        minX = Math.min(minX, x);
        minY = Math.min(minY, y);
        maxX = Math.max(maxX, x);
        maxY = Math.max(maxY, y);
      }
    }
  }

  const padding = 18;
  minX = Math.max(0, minX - padding);
  minY = Math.max(0, minY - padding);
  maxX = Math.min(image.width - 1, maxX + padding);
  maxY = Math.min(image.height - 1, maxY + padding);

  const width = maxX - minX + 1;
  const height = maxY - minY + 1;
  const cropped = new PNG({ width, height });

  for (let y = 0; y < height; y += 1) {
    for (let x = 0; x < width; x += 1) {
      setPixel(cropped, x, y, getPixel(image, x + minX, y + minY));
    }
  }

  return cropped;
}

function resizeContain(image, maxWidth, maxHeight) {
  const scale = Math.min(maxWidth / image.width, maxHeight / image.height);
  const width = Math.round(image.width * scale);
  const height = Math.round(image.height * scale);
  const resized = new PNG({ width, height });

  for (let y = 0; y < height; y += 1) {
    for (let x = 0; x < width; x += 1) {
      const srcX = Math.min(image.width - 1, Math.floor(x / scale));
      const srcY = Math.min(image.height - 1, Math.floor(y / scale));
      setPixel(resized, x, y, getPixel(image, srcX, srcY));
    }
  }

  return resized;
}

function drawRoundedRect(image, left, top, width, height, radius, fill) {
  const right = left + width - 1;
  const bottom = top + height - 1;

  for (let y = top; y <= bottom; y += 1) {
    for (let x = left; x <= right; x += 1) {
      const nearLeft = x < left + radius;
      const nearRight = x > right - radius;
      const nearTop = y < top + radius;
      const nearBottom = y > bottom - radius;

      if ((nearLeft || nearRight) && (nearTop || nearBottom)) {
        const cx = nearLeft ? left + radius : right - radius;
        const cy = nearTop ? top + radius : bottom - radius;
        const dx = x - cx;
        const dy = y - cy;
        if (dx * dx + dy * dy > radius * radius) {
          continue;
        }
      }

      setPixel(image, x, y, fill);
    }
  }
}

function composite(base, overlay, left, top) {
  for (let y = 0; y < overlay.height; y += 1) {
    for (let x = 0; x < overlay.width; x += 1) {
      setPixel(base, left + x, top + y, getPixel(overlay, x, y));
    }
  }
}

function makeLauncherIcon({ adaptive }) {
  const canvas = makeCanvas(1024, 1024, adaptive ? [0, 0, 0, 0] : BRAND.teal);
  const cardSize = adaptive ? 720 : 800;
  const cardLeft = Math.round((1024 - cardSize) / 2);
  const cardTop = cardLeft;
  drawRoundedRect(canvas, cardLeft, cardTop, cardSize, cardSize, 120, BRAND.white);

  const mark = resizeContain(cropToMark(readPng(SOURCE_ICON)), adaptive ? 575 : 640, adaptive ? 575 : 640);
  composite(canvas, mark, Math.round((1024 - mark.width) / 2), Math.round((1024 - mark.height) / 2));

  return canvas;
}

function makeFavicon() {
  const canvas = makeCanvas(48, 48, BRAND.teal);
  drawRoundedRect(canvas, 6, 6, 36, 36, 8, BRAND.white);
  const mark = resizeContain(cropToMark(readPng(SOURCE_ICON)), 30, 30);
  composite(canvas, mark, Math.round((48 - mark.width) / 2), Math.round((48 - mark.height) / 2));
  return canvas;
}

writePng(path.join(ASSET_DIR, "icon.png"), makeLauncherIcon({ adaptive: false }));
writePng(path.join(ASSET_DIR, "adaptive-icon.png"), makeLauncherIcon({ adaptive: true }));
writePng(path.join(ASSET_DIR, "favicon.png"), makeFavicon());

console.log("CorePet app assets generated.");
