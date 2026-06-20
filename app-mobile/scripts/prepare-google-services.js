const fs = require("fs");
const path = require("path");

const appRoot = path.resolve(__dirname, "..");
const packageName = "br.com.corepet.app";
const localSource = path.join(appRoot, "google-services.json");
const targetRelative = "android/app/google-services.json";
const target = path.join(appRoot, ...targetRelative.split("/"));

function log(message) {
  console.log(`[firebase] ${message}`);
}

function readJsonFile(filePath) {
  return JSON.parse(fs.readFileSync(filePath, "utf8"));
}

function validateGoogleServices(filePath) {
  const config = readJsonFile(filePath);
  const clients = Array.isArray(config.client) ? config.client : [];
  const hasPackage = clients.some(
    (client) =>
      client?.client_info?.android_client_info?.package_name === packageName
  );

  if (!hasPackage) {
    throw new Error(
      `google-services.json nao contem o package_name ${packageName}.`
    );
  }
}

function writeContent(content) {
  fs.mkdirSync(path.dirname(target), { recursive: true });
  fs.writeFileSync(target, content);
  validateGoogleServices(target);
  log("google-services.json preparado para o build Android.");
}

function copyFile(filePath) {
  fs.mkdirSync(path.dirname(target), { recursive: true });
  fs.copyFileSync(filePath, target);
  validateGoogleServices(target);
  log("google-services.json copiado para android/app.");
}

function prepare() {
  if (process.env.EAS_BUILD_PLATFORM && process.env.EAS_BUILD_PLATFORM !== "android") {
    log("build nao Android; preparacao Firebase ignorada.");
    return;
  }

  const envFile = process.env.GOOGLE_SERVICES_JSON;
  if (envFile) {
    const resolvedEnvFile = path.isAbsolute(envFile)
      ? envFile
      : path.resolve(appRoot, envFile);
    if (fs.existsSync(resolvedEnvFile)) {
      copyFile(resolvedEnvFile);
      return;
    }
    if (envFile.trim().startsWith("{")) {
      writeContent(envFile);
      return;
    }
  }

  const envBase64 = process.env.GOOGLE_SERVICES_JSON_BASE64;
  if (envBase64) {
    writeContent(Buffer.from(envBase64, "base64").toString("utf8"));
    return;
  }

  if (fs.existsSync(localSource)) {
    copyFile(localSource);
    return;
  }

  if (fs.existsSync(target)) {
    validateGoogleServices(target);
    log("google-services.json ja existe em android/app.");
    return;
  }

  throw new Error(
    "Firebase/FCM nao configurado. Crie a variavel de arquivo GOOGLE_SERVICES_JSON no EAS ou coloque app-mobile/google-services.json antes do build Android."
  );
}

prepare();
