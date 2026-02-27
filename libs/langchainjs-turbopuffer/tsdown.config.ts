import { defineConfig } from "tsdown";

export default defineConfig({
  entry: ["./src/index.ts"],
  format: ["cjs", "esm"],
  target: "es2022",
  platform: "node",
  fixedExtension: false,
  dts: true,
  sourcemap: true,
  unbundle: true,
  inlineOnly: false,
});
