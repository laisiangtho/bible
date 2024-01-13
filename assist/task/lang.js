// import { seek } from "lethil";
import * as base from "./base.js";

const env = base.env;
const config = env.config;
const listOfBible = env.listOfBible;
const category = env.category;
// const structure = env.structure;

/**
 * Testing
 * @example
 * node run task lang
 * @param {any} req
 */
export default async function doDefault(req) {
  return "????";
}

/**
 * Generator or regenerate languages
 * @example
 * node run task lang generate
 * @param {any} req
 */
export async function doGenerate(req) {
  const logs = [];
  for (let index = 0; index < listOfBible.book.length; index++) {
    const book = listOfBible.book[index];
    const iso = book.language.name;
    if (!logs.includes(iso)) {
      logs.push(iso);

      const identify = book.identify;
      let msg = await env.createLanguage(iso, identify);
      console.log(msg);
    }
  }

  let _totalLanguage = logs.length.toString();
  let _totalBook = listOfBible.book.length.toString();
  let msg = "done ? languages from # books"
    .replace("?", _totalLanguage)
    .replace("#", _totalBook);
  return msg;
}
