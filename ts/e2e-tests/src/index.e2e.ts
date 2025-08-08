import { ok } from "node:assert";
import { test } from "node:test";

import { LlamaCloudIndex } from "llama-cloud-services";
import { LlamaParseReader } from "llama-cloud-services";

test("LlamaIndex module resolution test", async (t) => {
  await t.test("works with ES module", () => {
    const index = new LlamaCloudIndex({
      name: "test-index",
      projectName: "Default",
    });
    const reader = new LlamaParseReader({
      resultType: "markdown",
      verbose: false,
    });
    ok(index !== undefined);
    ok(reader !== undefined);
  });

  await t.test("works with dynamic imports", async () => {
    const mod = await import("llama-cloud-services"); // simulates commonjs
    ok(mod !== undefined);
    const index = new mod.LlamaCloudIndex({
      name: "test-index",
      projectName: "Default",
    });
    ok(index !== undefined);
  });

  await t.test("all imports work", () => {
    const allImports = [
      LlamaCloudIndex,
    ];

    ok(allImports.filter(Boolean).length === allImports.length);
  });
});
