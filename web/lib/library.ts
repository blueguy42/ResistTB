import type { Library } from "./types";
import generated from "../data/library.json";

// Written by `python -m genohack.cli library` (one design summary per WHO target).
export function loadLibrary(): Library {
  return generated as unknown as Library;
}
