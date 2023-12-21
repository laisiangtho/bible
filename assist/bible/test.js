// import { seek } from "lethil";
import * as base from "./base.js";

const env = base.env;
// const config = env.config;
const listOfBible = env.listOfBible;
// const category = env.category;
// const structure = env.structure;

/**
 * Testing
 * @example
 * note run bible test
 * @param {any} req
 */
export default async function doDefault(req) {
  return JSON.stringify(listOfBible);
}

export async function khualTawng() {}
