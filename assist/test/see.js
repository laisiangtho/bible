// import { config } from "lethil";
import * as base from "./base.js";

const env = base.env;
// const config = env.config;
// const listOfBible = env.listOfBible;
const category = env.category;
const structure = env.structure;

/**
 * Testing
 * @param {any} req
 */
export async function doTestDefault(req) {
  // return base.settings;
  // console.log(req);
  // return JSON.stringify(base.settings);
  return JSON.stringify(category.name.book);
}

/**
 * Testing
 * @param {any} req
 */
export async function doTestIO(req) {
  // await base.writeJSON("./tmp/delete.json", { 1: "Ok" });
  // let category = await base.readJSON("./category.json", {});
  return "?";
}

/**
 * Testing
 * @param {any} req
 */
export async function doTestBookname(req) {
  const books = category.name.book;
  for (const [key, value] of Object.entries(books)) {
    console.log(value.info.abbr[0]);
  }
  return "?";
}

/**
 * Issue reported by Khual Tawng
 * @param {any} req
 */
export async function doKhualTawng(req) {
  const taskList = [
    "Gamlak Vakna. 10:14; 23:3",
    "Thu Hilhkikna. 28:39; 28:59; 32:42",
    "Joshua. 11:8; 19:28; 23:5",
    "Samuel Masa. 9:11; 10:11",
    "Samuel Nihna. 1:9; 16:1",
    "Kumpi Masate. 20:6",
    "Kumpi Nihnate. 3:3; 13:20",
    "Khang Tangthu Masa. 11:11; 21:23; 29:5; 29:11",
    "Khang Tangthu Nihna. 21:16; 29:27; 29:34; 34:11; 34:27; 35:22; 36:8",
    "Job. 30:5; 34:32",
    "Late. 31:10;93:5; 96:7; 107:42; 119:131; 119:148",
    "Paunak. 6:12; 23:27",
    "Thuhilhna. 3:5",
    "Solomon La. 5:13",
    "Isaiah. 3:1",
    "Jeremiah. 31:38",
    "Ezekiel. 7:15; 16:11; 24:6; 31:9; 31:18",
    "Daniel. 1:19; 3:29; 8:15; 11:6",
    "Hosea. 14:5",
    "Nahum. 1:1; 2:1",
    "Habakkuk. 2:12",
    "Mark. 5:31; 9:27",
  ];
  /**
   * @type {base.env.TypeOfBible}
   */
  const typeData = Object.assign({}, structure);
  let oldData = await base.readJSON("./tmp/old-json/tedim1932.json", typeData);
  let newData = await base.readJSON("./json/tedim1932.json", typeData);

  for (let a1 = 0; a1 < taskList.length; a1++) {
    const [bookName, _dumpList] = taskList[a1].split(".");
    const bookId = base.getBookIdByName(newData, bookName.trim());
    // console.log(bookName, bookId, _dumpList);
    // console.log(bookName, bookId);
    if (bookName && _dumpList) {
      const _chapters = _dumpList.split(";").map((e) => e.trim());
      // console.log(bookName, _chapters);

      if (_chapters.length) {
        console.log("- [ ]", bookName, _chapters.join("; "));
        for (let a2 = 0; a2 < _chapters.length; a2++) {
          const _dumpChapter = _chapters[a2];
          console.log("   - [ ]", _dumpChapter);
          const [chapterId, verseId] = _dumpChapter
            .split(":")
            .map((e) => e.trim());
          // console.log("    -", _dumpChapter);

          let verseTextOld = "";
          let verseTextNew = "";
          try {
            verseTextOld =
              oldData.book[bookId].chapter[chapterId].verse[verseId].text;
            verseTextNew =
              newData.book[bookId].chapter[chapterId].verse[verseId].text;
          } catch (error) {
            console.log(error);
          }

          console.log("    -", verseTextOld);
          console.log("    -", verseTextNew);
          // console.log(bookName, bookId, chapterId, verseId);
        }
      }
    }
  }

  return "khual tawng working";
}
