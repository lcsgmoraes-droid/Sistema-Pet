const appJson = require("./app.json");

module.exports = ({ config }) => {
  const expo = appJson.expo;
  const googleServicesFile =
    process.env.GOOGLE_SERVICES_JSON ?? expo.android.googleServicesFile;

  return {
    ...config,
    ...expo,
    android: {
      ...expo.android,
      googleServicesFile,
    },
  };
};
