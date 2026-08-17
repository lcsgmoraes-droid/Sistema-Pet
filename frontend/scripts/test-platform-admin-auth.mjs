import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

const root = resolve(import.meta.dirname, "..");
const read = (path) => readFileSync(resolve(root, path), "utf8");

const routes = read("src/app/AppRoutes.jsx");
const platformApi = read("src/platformApi.js");
const storage = read("src/auth/platformTokenStorage.js");
const opsLayout = read("src/components/OpsLayout.jsx");
const tenantsController = read("src/pages/ops-tenants/useOpsTenantsController.js");

assert.match(routes, /path="\/ops\/login"/);
assert.match(routes, /path="\/ops\/recuperar-senha"/);
assert.match(routes, /<PlatformProtectedRoute>/);
assert.doesNotMatch(routes, /<ProtectedRoute permission="usuarios\.manage">\s*<OpsLayout/);

assert.match(storage, /platform_access_token/);
assert.match(storage, /platform_refresh_token/);
assert.doesNotMatch(storage, /const ACCESS_TOKEN_KEY = "access_token"/);

assert.match(platformApi, /\/platform-auth\/refresh/);
assert.match(platformApi, /getPlatformAccessToken/);
assert.match(opsLayout, /usePlatformAuth/);
assert.match(tenantsController, /from "\.\.\/\.\.\/platformApi"/);

console.log("platform admin auth contract: ok");
