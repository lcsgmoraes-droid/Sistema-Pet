import assert from "node:assert/strict";
import Module, { createRequire } from "node:module";
import path from "node:path";
import { after, test } from "node:test";

const require = createRequire(import.meta.url);
const expoRequire = createRequire(require.resolve("expo/package.json"));
const cliPackagePath = expoRequire.resolve("@expo/cli/package.json");
const cliDirectory = path.dirname(cliPackagePath);
// Permite validar uma instalacao temporaria sem modificar dependencias compartilhadas.
const zodRequire = createRequire(
  process.env.COREPET_ZOD_VALIDATION_ROOT
    ? path.join(
        path.resolve(process.env.COREPET_ZOD_VALIDATION_ROOT),
        "package.json",
      )
    : cliPackagePath,
);
const zod = zodRequire("zod");
const zodVersion = zodRequire("zod/package.json").version;
const originalLoad = Module._load;

Module._load = function (request, parent, isMain) {
  if (
    request === "zod" &&
    parent?.filename.startsWith(`${cliDirectory}${path.sep}`)
  ) {
    return zod;
  }
  return originalLoad.call(this, request, parent, isMain);
};
after(() => {
  Module._load = originalLoad;
});

const serverDirectory = path.join(cliDirectory, "build/src/start/server");
const { PluginSchema, DevToolsPluginOutputSchema } = require(
  path.join(serverDirectory, "DevToolsPlugin.schema.js"),
);
const { createMCPDevToolsExtensionSchema } = require(
  path.join(serverDirectory, "createMCPDevToolsExtensionSchema.js"),
);
const { DevToolsPluginCliExtensionResults } = require(
  path.join(serverDirectory, "DevToolsPluginCliExtensionResults.js"),
);
const plugin = {
  packageName: "fixture-plugin",
  packageRoot: "/fixture",
  cliExtensions: {
    description: "Fixture",
    entryPoint: "fixture.js",
    commands: [
      {
        name: "lookup",
        title: "Lookup",
        environments: ["cli", "mcp"],
        parameters: [
          { name: "query", type: "text" },
          { name: "limit", type: "number" },
          { name: "confirm", type: "confirm" },
        ],
      },
    ],
  },
};

test("schemas reais do Expo CLI usam o Zod corrigido sem perder validacoes", () => {
  assert.equal(zodVersion, "4.6.6");
  assert.equal(PluginSchema.safeParse(plugin).success, true);
  assert.equal(
    PluginSchema.safeParse({ ...plugin, packageName: "" }).success,
    false,
  );
  const invalid = PluginSchema.safeParse({});
  assert.equal(invalid.success, false);
  assert.ok(invalid.error.message.length);
  assert.ok(invalid.error.issues.length);
});

test("schema MCP real preserva comando, tipos e rejeicao de campos extras", () => {
  const schema = createMCPDevToolsExtensionSchema(plugin);
  assert.equal(
    schema.safeParse({
      command: "lookup",
      query: "abc",
      limit: 4,
      confirm: false,
    }).success,
    true,
  );
  assert.equal(schema.safeParse({ command: "lookup" }).success, true);
  for (const input of [
    { command: "unknown" },
    { command: "lookup", limit: "wrong" },
    { command: "lookup", confirm: "wrong" },
    { command: "lookup", unexpected: true },
  ]) {
    assert.equal(schema.safeParse(input).success, false);
  }
});

test("resultados reais do CLI preservam texto, midia e mensagens de erro", () => {
  const lines = [
    { type: "text", text: "ok", level: "info" },
    { type: "image", url: "https://example.com/image.png" },
    { type: "audio", url: "https://example.com/audio.mp3" },
  ];
  assert.equal(DevToolsPluginOutputSchema.safeParse(lines).success, true);
  const results = new DevToolsPluginCliExtensionResults();
  assert.deepEqual(results.parseOutputText(JSON.stringify(lines)), lines);
  assert.equal(results.parseOutputText("Plain text")[0].text, "Plain text");
  for (const line of [
    { type: "image", url: "invalid-url" },
    { type: "text", text: "invalid", level: "other" },
    { type: "unknown" },
  ]) {
    const parsed = results.parseOutputText(JSON.stringify([line]));
    assert.equal(parsed[0].level, "error");
    assert.match(parsed[0].text, /^Invalid JSON: .+/);
  }
});
