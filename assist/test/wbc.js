import { JSDOM } from "jsdom";
import { seek } from "lethil";
import * as base from "./base.js";

const env = base.env;
const config = env.config;
const listOfBible = env.listOfBible;
const category = env.category;
const structure = env.structure;

const taskId = "wbc";
const idName = "bible";

const settings_file = "./assets/?/settings.json".replace("?", taskId);

/**
 * @typedef {Object} TypeOfListData
 * @property {string} id - bibleId
 * @property {string} ext - extension
 * @property {string} [identify] - id that has JSON data in json
 * @property {object} [note] - Note
 *
 * @typedef {Object} TypeOfSetting
 * @property {string} scan
 * @property {string} fruit - output file `./assets/?/tmp/scanId.json`
 * @property {string} html - cache file `./assets/?/tmp/scanId/bN.cN.html`
 * @property {string} doc - JSON file containing bible `./json/~.json`
 * @property {string} [url] - bible.book.chapter
 * @property {string} [uav] - api version - url api version
 * @property {number} version - version number
 * @property {number} delay - in milliseconds
 * @property {TypeOfListData[]} list
 */

/**
 * @type {TypeOfSetting}
 */
const _settings = {
  scan: "",
  fruit: "",
  html: "",
  doc: "",
  delay: 60000,
  version: 0,
  list: [],
};
const settings = await base.readJSON(settings_file, _settings);

// const taskCurrent = settings.list.find((e) => e.id == settings.scan);
let taskCurrent = settings.list.find((e) => e.id == settings.scan);

/**
 * https://~.com/~/iN/bN.cN.iE
 * @param {string} bN - bookNameId
 * @param {string|number} cN - chapterId
 * param {string} cN - chapterId
 */
function urlChapter(bN, cN) {
  // if (!config[taskId]) {
  //   return "";
  // }
  if (!settings.url || !taskCurrent) {
    return "";
  }
  return settings.url
    .replace(/~/g, idName)
    .replace(/iN/, taskCurrent?.id)
    .replace(/bN/, bN)
    .replace(/cN/, cN.toString())
    .replace(/iE/, taskCurrent?.ext);
}

/**
 * https://www.~.com/api/~/version/iN
 */
function uaVersion() {
  if (!settings.uav || !taskCurrent) {
    return "";
  }
  return settings.uav.replace(/~/g, idName).replace(/iN/, taskCurrent?.id);
}

/**
 * fileName: ./assist/?/tmp/scanId/bN.cN.html
 * @param {string} bN - bookNameId
 * @param {string|number} cN - chapterId
 */
function cacheFile(bN, cN) {
  return settings.html
    .replace("?", taskId)
    .replace("scanId", settings.scan)
    .replace(/bN/, bN)
    .replace(/cN/, cN.toString());
}

/**
 * fileName: ./assist/?/tmp/scanId.json
 */
function fruitFile() {
  return settings.fruit.replace("?", taskId).replace("scanId", settings.scan);
}

/**
 * fileName: ./json/~.json
 * @param {string} identify
 */
function docFile(identify) {
  return settings.doc.replace("~", identify);
}

/**
 * Testing
 * @param {any} req
 */
export async function doDefault(req) {
  // 2020-07-24T11:36:18.429Z
  // if (settings.url) {
  //   let books = category.name.book;

  //   let bookList = Object.entries(books);

  //   for (const [key, book] of bookList) {
  //     let bookName = book.info.abbr[0].toUpperCase();

  //     let bookCategory = category.book[key];
  //     let chapterList = bookCategory.v;
  //     let chapterTotal = chapterList.length;

  //     for (let index = 0; index < chapterTotal; index++) {
  //       let verseTotal = chapterList[index];
  //       let chapterId = index + 1;
  //       let url = urlChapter(bookName, chapterId);
  //       console.log(url, chapterId, verseTotal);
  //     }
  //   }
  // }

  return "Oops";
}

/**
 * Check
 * @example
 * node run test wbc check
 * @param {any} req
 */
export async function doCheck(req) {
  const nonBook = [];
  const allBook = [];
  const duplicateBook = [];
  for (let index = 0; index < listOfBible.book.length; index++) {
    let obj = listOfBible.book[index];
    const identify = obj.identify;
    let file = docFile(identify);
    let alreadyCache = seek.exists(file);
    if (alreadyCache == "") {
      nonBook.push(identify);
    }

    if (allBook.includes(identify)) {
      duplicateBook.push(identify);
    } else {
      allBook.push(identify);
    }
    console.log("book", identify, alreadyCache);
  }

  if (nonBook.length || duplicateBook.length) {
    console.log("none book", nonBook);
    console.log("duplicate book", duplicateBook);
    return "none book";
  }

  const nonDoc = [];
  const nonRegister = [];

  for (let index = 0; index < settings.list.length; index++) {
    const wbc = settings.list[index];
    const identify = wbc.identify;
    let docFileExist = false;
    let docIndex = -1;

    if (identify) {
      let docFilePath = docFile(identify);
      if (seek.exists(docFilePath)) {
        docFileExist = true;
      }
      docIndex = listOfBible.book.findIndex((e) => e.identify == identify);
    }
    if (docIndex == -1) {
      nonRegister.push(identify);
    }

    if (docFileExist == false) {
      nonDoc.push(identify);
    }

    console.log(
      "> wbc:",
      wbc.id,
      "identify:",
      identify,
      "doc:",
      docFileExist,
      "register",
      docIndex >= 0
    );
  }
  console.log(">> non-doc", nonDoc);
  console.log(">> non-register", nonRegister);

  console.log(
    "> its expected false on doc if identify empty, 'non-doc' provided its Id"
  );
  console.log(
    "> if identify is not empty, register is expected to be true, otherwise 'non-register' provided its Id"
  );

  const totalBook = listOfBible.book.length;
  const totalWBC = settings.list.length;

  console.log(">> total of books", totalBook, "wbc", totalWBC);

  // const nonWBC = listOfBible.book.map((a) =>
  //   settings.list.find((b) => a.identify != b.identify)
  // );
  // const nonWBC = settings.list.map(
  //   (a) => listOfBible.book.find((b) => b.identify != a.identify)?.identify
  // );

  const nonWBC = [];

  for (let index = 0; index < listOfBible.book.length; index++) {
    const a = listOfBible.book[index];
    let tmp = settings.list.find((b) => a.identify == b.identify);
    if (!tmp) {
      // console.log("non WBC", a.identify);
      nonWBC.push(a.identify);
    }
  }

  console.log(">> non WBC", nonWBC);

  return "id is wbcId, identify is used in app, doc shown if identify file is exist in doc folder(./json)";
}

/**
 * IO ??
 * @example
 * node run test wbc io
 * @param {any} req
 */
export async function doIO(req) {
  // await base.writeJSON("./tmp/delete.json", { 1: "Ok" });

  return "?";
}

/**
 * Requests from live
 * @example
 * node run test wbc request
 * @param {any} req
 */
export async function doRequest(req) {
  const bN = "GEN";
  const cN = "3";
  await doRequestCore(bN, cN, true);
  return "request";
}

/**
 * @param {string} bN
 * @param {string|number} cN
 * @param {boolean} [save] - if true write tmp HTML file
 */
async function doRequestCore(bN, cN, save) {
  let url = urlChapter(bN, cN);

  let dom = await JSDOM.fromURL(url);
  let doc = dom.window.document;

  const body = doc.getElementsByClassName("ChapterContent_chapter__uvbXo")[0];
  const wbcInnerHTML = body.innerHTML;

  // NOTE: meta is require for utf8
  const tpl = "<html><head><meta charset='utf-8'></head><body>?</body></html>";

  const wbcBody = tpl.replace("?", wbcInnerHTML);

  if (save) {
    let file = cacheFile(bN, cN);
    await seek.write(file, wbcBody);
  }

  return new JSDOM(wbcBody);
}

/**
 * Add new version/language of Bible
 * request version, expected to be JSON
 * *.books
 * @example
 * node run test wbc new
 */
export async function doNew() {
  if (!settings.scan) {
    return "no scanId";
  }
  const url = uaVersion();
  if (!url) {
    return "no url";
  }
  if (!structure) {
    return "no structure";
  }

  const docFilePath = docFile(taskCurrent?.identify || settings.scan);

  if (seek.exists(docFilePath)) {
    return "record file already exists at:" + docFilePath;
  }

  let api = await (await fetch(url)).json();

  if (!api) {
    return "not found:" + url;
  }

  let books = api.books;

  if (!books) {
    return "no book contain:" + url;
  }

  const res = Object.assign({}, structure);
  res.note = {};
  res.story = {};
  res.book = {};
  res.info.identify = settings.scan;

  for (let index = 0; index < books.length; index++) {
    let bookId = (index + 1).toString();
    const obj = books[index];
    // let infoName = "";
    // if (obj.human) {
    //   infoName = obj.human
    //     .toLowerCase()
    //     .split(" ")
    //     .map((w) => {
    //       return w[0].toUpperCase() + w.substr(1);
    //     })
    //     .join(" ");
    // }

    // let infoshortname = "";
    // if (obj.abbreviation) {
    //   infoshortname = obj.abbreviation
    //     .toLowerCase()
    //     .split(" ")
    //     .map((w) => w[0].toUpperCase() + w.substr(1))
    //     .join(" ");
    // }

    // let infodesc = "";
    // if (obj.human_long) {
    //   infodesc =
    //     obj.human_long[0].toUpperCase() +
    //     obj.human_long.substr(1).toLowerCase();
    // }
    let infoName = obj.human;
    let infoshortname = obj.abbreviation;
    let infodesc = obj.human_long;
    if (infoName == infoshortname) {
      infoshortname = "";
    }
    if (infoName == infodesc) {
      infodesc = "";
    }
    res.book[bookId] = {
      info: {
        name: infoName,
        shortname: infoshortname,
        abbr: [],
        desc: infodesc,
        // name: obj.human,
        // shortname: obj.abbreviation,
        // abbr: [],
        // desc: obj.human_long,
      },
      chapter: {},
    };
  }

  await base.writeJSON(docFilePath, res, 2);
  await base.writeJSON(docFilePath.replace(".json", ".v0.json"), res, 2);
  console.log("> write JSON at", docFilePath);
  console.log("> see its matching", url);
  return "done: info(name, year, etc), digit, testament and language(book, chapter, verse, etc) needed manually input";
}

/**
 * Read from local, development only for `examine`
 * @example
 * node run test wbc read
 * @param {any} req
 */
export async function doRead(req) {
  const bN = "REV";
  const cN = "7";
  await doReadCore(bN, cN, true);
  return "read";
}

/**
 * @param {string} bN
 * @param {string|number} cN
 * @param {boolean} [save] - if true write tmp JSON file
 */
async function doReadCore(bN, cN, save) {
  let file = cacheFile(bN, cN);

  let dom = await JSDOM.fromFile(file);
  let res = await examine(dom);

  if (save) {
    await base.writeJSON(file.replace(".html", ".json"), res, 2);
  }

  return res.status;
}

/**
 * Scan from live or local
 * @example
 * node run test wbc scan
 * @param {any} req
 */
export async function doScan(req) {
  if (req.query.scan) {
    settings.scan = req.query.scan;
    taskCurrent = settings.list.find((e) => e.id == settings.scan);
  }

  if (!taskCurrent) {
    return "no taskCurrent";
  }

  /**
   * @type {base.env.TypeOfBible}
   */
  let bible = {};

  const currentIdentify = taskCurrent.identify;

  if (currentIdentify) {
    let docFilePath = docFile(currentIdentify);

    bible = await base.readJSON(docFilePath, bible);
  }

  if (!bible.book) {
    bible.book = {};
  }

  await doScanCore(bible).catch(async (error) => {
    console.log("> ", error);

    console.log("> waiting to continue in", settings.delay, "milliseconds");

    await new Promise((resolve) => setTimeout(resolve, settings.delay));
    await doScan({});
  });

  if (taskCurrent.note) {
    if (taskCurrent.note.v) {
      if (currentIdentify) {
        if (listOfBible.version < settings.version) {
          listOfBible.version = settings.version;
        }

        let bookIndex = listOfBible.book.findIndex(
          (e) => e.identify == currentIdentify
        );
        if (bookIndex >= 0) {
          listOfBible.book[bookIndex].version = taskCurrent.note.v;
          listOfBible.updated = new Date();
          await base.writeJSON(config.fileOfBook, listOfBible, 2);
          console.log("> updated JSON at", config.fileOfBook);

          const bookInfo = listOfBible.book[bookIndex];
          bible.info.name = bookInfo.name;
          bible.info.shortname = bookInfo.shortname;
          bible.info.year = bookInfo.year;
          bible.info.language = bookInfo.language;
          bible.info.description = bookInfo.description;
          bible.info.publisher = bookInfo.publisher;
          bible.info.contributors = bookInfo.contributors;
          bible.info.copyright = bookInfo.copyright;
        } else {
          console.log(
            "> book record is",
            currentIdentify,
            "missing in",
            config.fileOfBook
          );
        }

        bible.info.version = taskCurrent.note.v;
        bible.info.identify = currentIdentify;

        let docFilePath = docFile(currentIdentify);
        await base.writeJSON(docFilePath, bible);
        console.log("> replaced JSON at", docFilePath);
      }
    }
  }

  let fruitFileName = fruitFile();
  // NOTE: write on each book
  await base.writeJSON(fruitFileName, bible, 2);
  console.log("> write JSON at", fruitFileName);
  let msg = "Scanned: " + taskCurrent.id;

  return msg;
}

/**
 * @param {base.env.TypeOfBible} bible
 */
async function doScanCore(bible) {
  const books = category.name.book;

  let bookList = Object.keys(books);
  for (let index = 0; index < bookList.length; index++) {
    const bookId = bookList[index];
    const book = books[bookId];
    // console.log("bookId", bookId);
    const bookNameId = book.info.abbr[0].toUpperCase();
    // console.log("bookNameId", bookId, bookNameId);
    let bookDetail = category.book[bookId];
    // let chapterCount = bookDetail.c;
    let chapterCount = bookDetail.v;
    if (!bible.book[bookId]) {
      bible.book[bookId] = {};
    }
    for (let index = 0; index < chapterCount.length; index++) {
      // const verseCount = chapterCount[index];
      const chapterId = index + 1;
      let file = cacheFile(bookNameId, chapterId);

      // const dom = await doRequestCore(bookNameId, chapterId, true);
      // const res = await examine(dom);
      // bible[bookId][chapterId] = res;
      // console.log(file);

      let dom;
      let alreadyCache = seek.exists(file);
      if (alreadyCache) {
        dom = await JSDOM.fromFile(file);
      } else {
        dom = await doRequestCore(bookNameId, chapterId, true);
      }

      if (dom) {
        const res = await examine(dom);
        if (res && res.status > 0) {
          // bible[bookId][chapterId] = res.verse;

          if (!bible.book[bookId].chapter) {
            bible.book[bookId].chapter = {};
          }
          if (!bible.book[bookId].chapter[chapterId]) {
            bible.book[bookId].chapter[chapterId] = {};
          }
          bible.book[bookId].chapter[chapterId].verse = res.verse;
        }
      }
      console.log(bookNameId, chapterId);
    }
  }
}

/**
 * @param {any} req
 */
export async function doScanAll(req) {
  const tmp = settings.list;

  const scanedList = [];

  for (let index = 0; index < tmp.length; index++) {
    const data = tmp[index];
    const scanId = data.id;
    // req.query.identify;
    await doScan({ query: { scan: scanId } });
    scanedList.push(scanId);
  }
  console.log("scanned", scanedList);
  console.log("total", scanedList.length);
  return "done";
}

/**
 * Html to json of Chapter
 * Extract html>body and format to json
 * @param {JSDOM} dom
 */
async function examine(dom) {
  let doc = dom.window.document;
  let body = doc.getElementsByTagName("body")[0];
  const res = {
    chapter: "",
    status: 0,
    verse: {},
  };

  let chapterSpan = body.querySelectorAll("div>span");
  let verseTitle = "";
  let verseTitleInsertIndex = 0;

  for (let k0 = 0; k0 < chapterSpan.length; k0++) {
    const el0 = chapterSpan[k0];
    let className = el0.className;

    let usfmAttr = el0.getAttribute("data-usfm");
    let usfmSplit = usfmAttr?.split("+");
    /**
     * @type {any}
     */
    let usfm = {};
    if (usfmSplit?.length) {
      // GEN.1.17+GEN.1.18
      usfm = usfmFormat(usfmSplit[0]);
    }
    // let usfm = usfmFormat(usfmAttr);
    if (usfm) {
      if (!res.chapter) {
        res.chapter = usfm.chapter;
      }
    }

    let verseId = usfm?.verse;

    if (className == "ChapterContent_heading__xBDcs") {
      // NOTE: title
      // let verseTitleText = titleFormat(el0.innerHTML);
      let verseTitleText = el0.innerHTML.trim();
      if (verseTitle) {
        verseTitle += " " + verseTitleText;
      } else {
        verseTitle = verseTitleText;
      }
      if (Object.keys(res.verse).length === 0) {
        // NOTE: first title ahead of verse
        verseTitleInsertIndex++;
      }
    } else if (usfmAttr) {
      let verseHTML = el0.querySelectorAll(
        "span.ChapterContent_content__RrUqA"
      );
      let verseText = "";
      for (let vk = 0; vk < verseHTML.length; vk++) {
        const verseElm = verseHTML[vk];
        verseText += " " + verseElm.innerHTML;
      }
      verseText = verseFormat(verseText);

      if (verseText) {
        if (res.verse[verseId]) {
          if (res.verse[verseId].text) {
            res.verse[verseId].text += " " + verseText;
          } else {
            res.verse[verseId].text = verseText;
          }
        } else {
          res.verse[verseId] = {};
          res.verse[verseId].text = verseText;
        }
      }

      if (verseTitle) {
        if (res.verse[verseId]) {
          verseTitleInsertIndex++;

          if (verseTitleInsertIndex >= 2) {
            // res.verse[verseId].title = verseTitle;
            res.verse[verseId].title = titleFormat(verseTitle);
            verseTitle = "";
            verseTitleInsertIndex = 0;
          }
        }
      }

      let refHTML = el0.querySelectorAll(
        "span.ChapterContent_note__YlDW0.ChapterContent_x__tsTlk > span.ChapterContent_body__O3qjr"
      );

      if (refHTML) {
        let refText = "";
        for (let rk = 0; rk < refHTML.length; rk++) {
          const refElm = refHTML[rk];
          // verseText += " " + refElm.innerHTML;¨
          // NOTE: remove the last dot
          refText +=
            "; " + refElm.innerHTML.replace(/။/g, ";").replace(/\.$/, "");
          // console.log("ref", refElm.innerHTML);
        }
        if (refText) {
          // NOTE: remove the first and last semicolon
          refText = refText.trim().replace(/^\;/, "").replace(/\;$/, "").trim();
          // refText = refText.replace(/^\;/, "").trim();

          if (res.verse[verseId]) {
            // console.log("verse", usfm);
            if (res.verse[verseId].ref) {
              res.verse[verseId].ref += "; " + refText;
            } else {
              res.verse[verseId].ref = refText;
            }
          } else {
            res.verse[verseId] = {};
            res.verse[verseId].ref = refText;
          }
        }
      }

      // NOTE: merge
      if (usfmSplit && usfmSplit.length > 1) {
        // let verseMerge = usfmSplit[1].split(".").pop();
        let verseMergeLast = usfmSplit.pop();
        if (verseMergeLast) {
          let verseMerge = verseMergeLast.split(".").pop();
          if (verseMerge) {
            if (res.verse[verseId]) {
              res.verse[verseId].merge = verseMerge;
            }
          }
        }
      }
    }
  }

  res.status = Object.keys(res.verse).length;
  return res;
}

/**
 * GEN.2.1
 * @param {string|null} e
 * @returns
 */
function usfmFormat(e) {
  if (e) {
    let x = e.split(".");
    if (x.length == 3) {
      let bookId = base.getBookIdByAbbreviation(x[0]);
      return { book: x[0], bookId: bookId, chapter: x[1], verse: x[2] };
    }
  }
}

/**
 * <span class="ChapterContent_nd__ECPAf">Lord</span>
 * @param {string} str
 * @returns
 */
function titleFormat(str) {
  let e = commonFormat(str);
  return base.textFormat(e);
}

/**
 * <span class="ChapterContent_nd__ECPAf">Lord</span>
 * @param {string} str
 * @returns
 */
function verseFormat(str) {
  let e = commonFormat(str).replace(/<span[^>]*>([\s\S]*?)<\/span>/g, "$1");
  return base.textFormat(e);
}

/**
 * Replace known non-alph
 * ZWJ(hi), etc
 * @param {string} e
 * @returns
 */
function commonFormat(e) {
  return e
    .replace(/‍/g, "")
    .replace(/​/g, "")
    .replace(/ /g, "")
    .replace(/ /g, "")
    .replace(/\( /g, "(")
    .replace(/ \)/g, ")");
}
