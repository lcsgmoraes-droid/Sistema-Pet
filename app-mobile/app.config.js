const fs = require("fs");
const path = require("path");
const appJson = require("./app.json");

function resolveProjectPath(filePath) {
  if (!filePath) return "";
  return path.isAbsolute(filePath) ? filePath : path.resolve(__dirname, filePath);
}

function googleServicesFileFromEnv() {
  const value = process.env.GOOGLE_SERVICES_JSON;
  if (!value || value.trim().startsWith("{")) return undefined;
  return value;
}

function shouldExposeGoogleServicesFile(filePath) {
  if (!filePath) return false;
  if (process.env.EAS_BUILD_PLATFORM === "android") return true;
  if (process.env.GOOGLE_SERVICES_JSON || process.env.GOOGLE_SERVICES_JSON_BASE64) {
    return true;
  }
  return fs.existsSync(resolveProjectPath(filePath));
}

module.exports = ({ config }) => {
  const expo = appJson.expo;
  const googleServicesFile =
    googleServicesFileFromEnv() ?? expo.android.googleServicesFile;
  const android = {
    ...expo.android,
    googleServicesFile,
  };

  if (!shouldExposeGoogleServicesFile(googleServicesFile)) {
    delete android.googleServicesFile;
  }

  return {
    ...config,
    ...expo,
    android,
  };
};
