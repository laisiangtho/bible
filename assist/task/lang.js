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
      const file = config.fileOfLang.replace("~", iso);

      const res = await base.readJSON(file, {
        digit: [],
        language: {},
        section: {},
        testament: {},
        book: {},
        locale: {},
      });

      const identify = book.identify;

      const currentBible = await env.loadBible(identify);
      if (currentBible) {
        const bible = currentBible.bible;
        const name = category.name;
        let digit = Object.assign({}, name.digit, res.digit);
        res.digit = Object.values(digit);
        res.language = Object.assign({}, category.language, res.language);
        res.locale = Object.assign({}, category.locale, res.locale);
        res.section = Object.assign({}, name.section, res.section);
        res.testament = Object.assign({}, name.testament, res.testament);

        if (!res.book) {
          res.book = {};
        }
        let o = Object.keys(bible.book);

        for (let index = 0; index < o.length; index++) {
          const bookId = o[index];
          // console.log(bible.book[bookId].info.name, bookId);
          if (!res.book[bookId]) {
            res.book[bookId] = {};
          }
          // res.book[bookId].info = bible.book[bookId].info;
          res.book[bookId].info = Object.assign(
            {},
            bible.book[bookId].info,
            res.book[bookId].info
          );
          res.book[bookId].info.desc = "";
          const shortname = res.book[bookId].info.shortname;
          res.book[bookId].info.shortname = shortname.replace(/\.$/, "");
        }

        await base.writeJSON(file, res, 2);
        console.log(" >", file, "using", identify);
      }
    }
  }

  let _totalLanguage = logs.length.toString();
  let _totalBook = listOfBible.book.length.toString();
  let msg = "done ? languages from # books"
    .replace("?", _totalLanguage)
    .replace("#", _totalBook);
  return msg;
}
