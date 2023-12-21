// import * as base from "./base.js";

/**
 * Get definitions, see `cli` for more info
 * @example
 * note run bible search
 * @param {any} req - {query:{identify?:string, timeout?:number}}
 */
export default async function doDefault(req) {
  console.log(req);
  return "search default";
}
