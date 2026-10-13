import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { dirname, isAbsolute, relative, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { compileFunction } from "node:vm";
import ts from "typescript";

const sourceRoot = fileURLToPath(new URL("../../src/", import.meta.url));

function validateSourcePath(path) {
  const localPath = relative(sourceRoot, path);
  if (isAbsolute(localPath) || localPath.startsWith("..") || !/\.[cm]?[jt]sx?$/.test(path)) {
    throw new Error("Controller tests can only load local frontend source modules");
  }
}

// Execute actual component handlers with isolated hooks and mocked imports, without a DOM.
export function createControllerHarness(componentPath, { mocks, props, globals = {} }) {
  const slots = [];
  const cache = new Map();
  let index = 0;
  let dirty = false;
  let effects = [];
  let tree;
  let currentProps = props;
  const sameDependencies = (previous, next) =>
    previous &&
    next &&
    previous.length === next.length &&
    previous.every((value, i) => Object.is(value, next[i]));
  const hooks = {
    useState(initial) {
      const slot = index++;
      if (!slots[slot])
        slots[slot] = { value: typeof initial === "function" ? initial() : initial };
      return [
        slots[slot].value,
        (update) => {
          const value = typeof update === "function" ? update(slots[slot].value) : update;
          if (!Object.is(value, slots[slot].value)) {
            slots[slot].value = value;
            dirty = true;
          }
        },
      ];
    },
    useRef(initial) {
      const slot = index++;
      if (!slots[slot]) slots[slot] = { current: initial };
      return slots[slot];
    },
    useEffect(effect, dependencies) {
      const slot = index++;
      if (!sameDependencies(slots[slot]?.dependencies, dependencies)) {
        slots[slot]?.cleanup?.();
        slots[slot] = { dependencies };
        effects.push(() => {
          slots[slot].cleanup = effect();
        });
      }
    },
  };
  const jsx = (type, elementProps, key) => ({ type, props: elementProps, key });
  const imports = new Map([
    ...mocks,
    ["react", hooks],
    ["react/jsx-runtime", { jsx, jsxs: jsx, Fragment: "fragment" }],
  ]);
  function loadModule(path) {
    validateSourcePath(path);
    if (cache.has(path)) return cache.get(path);
    const { outputText, diagnostics } = ts.transpileModule(readFileSync(path, "utf8"), {
      fileName: path,
      reportDiagnostics: true,
      compilerOptions: {
        target: ts.ScriptTarget.ES2022,
        module: ts.ModuleKind.CommonJS,
        jsx: ts.JsxEmit.ReactJSX,
        esModuleInterop: true,
      },
    });
    assert.equal(
      diagnostics?.filter((item) => item.category === ts.DiagnosticCategory.Error).length,
      0,
    );
    const module = { exports: {} };
    cache.set(path, module.exports);
    const requireMock = (specifier) => {
      if (imports.has(specifier)) return imports.get(specifier);
      if (specifier.startsWith(".")) {
        const target = resolve(dirname(path), specifier);
        return loadModule(/\.[cm]?[jt]sx?$/.test(target) ? target : `${target}.js`);
      }
      throw new Error(`Unexpected module ${specifier}`);
    };
    // Compile only repository source validated above, with the explicit test mocks.
    compileFunction(outputText, ["require", "module", "exports", ...Object.keys(globals)], {
      filename: path,
    })(requireMock, module, module.exports, ...Object.values(globals));
    return module.exports;
  }
  const Controller = loadModule(componentPath).default;
  function render() {
    index = 0;
    dirty = false;
    effects = [];
    tree = Controller(currentProps);
    effects.forEach((effect) => effect());
  }
  async function settle() {
    for (let pass = 0; pass < 20; pass += 1) {
      await Promise.resolve();
      if (dirty) render();
    }
  }
  render();
  return {
    get tree() {
      return tree;
    },
    settle,
    async act(callback) {
      const result = callback();
      await settle();
      await result;
      await settle();
    },
    async update(update) {
      currentProps = { ...currentProps, ...update };
      render();
      await settle();
    },
  };
}

export function elements(node) {
  if (!node || typeof node !== "object") return [];
  if (Array.isArray(node)) return node.flatMap(elements);
  return [node, ...elements(node.props?.children)];
}

export function elementText(node) {
  if (typeof node === "string") return node;
  if (!node || typeof node !== "object") return "";
  if (Array.isArray(node)) return node.map(elementText).join(" ");
  return elementText(node.props?.children);
}
