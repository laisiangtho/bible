// import { JSDOM } from "jsdom";
// import * as csv from "csv";
import { seek } from "lethil";

// import { env } from "../anchor/index.js";
export { env } from "../anchor/index.js";

/**
 * Read JSON file
 */
export const readJSON = seek.readJSON;
/**
 * Write JSON file
 */
export const writeJSON = seek.writeJSON;
