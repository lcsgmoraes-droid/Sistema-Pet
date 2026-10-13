import assert from "node:assert/strict";
import test from "node:test";
import { fileURLToPath } from "node:url";
import { createControllerHarness } from "./reactControllerHarness.mjs";

test("controller harness rejects code outside frontend source before reading it", () => {
  const outside = fileURLToPath(new URL("../../../outside-controller.js", import.meta.url));
  assert.throws(
    () => createControllerHarness(outside, { mocks: new Map(), props: {} }),
    /only load local frontend source/,
  );
});

test("controller harness never compiles configuration or other non-code files", () => {
  const configuration = fileURLToPath(new URL("../../src/config.json", import.meta.url));
  assert.throws(
    () => createControllerHarness(configuration, { mocks: new Map(), props: {} }),
    /only load local frontend source/,
  );
});
