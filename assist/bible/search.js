import * as base from "./base.js";

const env = base.env;
const config = env.config;
const listOfBible = env.listOfBible;
const category = env.category;
const structure = env.structure;

/**
 * late 10:40
 * pian 1:20
 * @example
 * note run bible search tedim1932
 * @param {any} req - {query:{identify?:string, timeout?:number}}
 */
export default async function doDefault(req) {
  const bibleIdentity = req.query.name;
  console.log(req);
  return "search default";
}
