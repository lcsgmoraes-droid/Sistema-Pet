export function shouldShowDevModuleControls(env = {}) {
  const hideFlag = String(env.VITE_HIDE_DEV_CONTROLS || "")
    .trim()
    .toLowerCase();
  return Boolean(env.DEV) && !["1", "true", "yes", "sim"].includes(hideFlag);
}
