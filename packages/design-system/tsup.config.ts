import { defineConfig } from "tsup";

export default defineConfig({
  entry: ["src/index.ts", "src/button.tsx", "src/card.tsx", "src/input.tsx", "src/utils.ts"],
  format: ["esm", "cjs"],
  dts: true,
  external: ["react", "react-dom"],
  clean: true,
  sourcemap: true,
});
