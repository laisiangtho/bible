import * as base from "./base.js";

const env = base.env;
const config = env.config;
const listOfBible = env.listOfBible;
const category = env.category;
const structure = env.structure;

/**
 * @example
 * note run bible info
 * @param {any} req - {query:{identify?:string, timeout?:number}}
 */
export default async function doDefault(req) {
  // console.log(req);
  // const taskName = req.params.name;

  listOfBibleMarkDown();

  return "info default";
}

function listOfBibleMarkDown() {
  const totalBible = listOfBible.book.length;

  console.log("|", "Name", "|", "Language", "|", "ISO", "|");
  console.log("|", "---", "|", "---", "|", "---", "|");
  for (let index = 0; index < totalBible; index++) {
    const book = listOfBible.book[index];

    let name = "? (*)".replace("?", book.name).replace("*", book.shortname);
    let lang = book.language.text;
    let iso = book.language.name;
    console.log("|", name, "|", lang, "|", iso, "|");
  }

  const langDump = listOfBible.book.map((e) => e.language.name);
  let langList = [...new Set(langDump)];

  console.log("> Books:", totalBible, "langs:", langList.length);
}
