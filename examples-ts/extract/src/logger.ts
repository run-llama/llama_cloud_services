import { createConsola } from "consola";
import type { ConsolaInstance } from "consola";

export const logger: ConsolaInstance = createConsola({
  formatOptions: {
    date: false,
  },
});
