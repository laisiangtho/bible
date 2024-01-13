import { JSDOM } from "jsdom";
import * as fs from "fs";
import { seek, ask } from "lethil";
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
 * @property {string} [uco] - api configuration
 * @property {string} [ula] - api language
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
 * //~.com/~/iN/bN.cN.iE
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
 * //~.com/api/~/version/iN
 * @param {string} id
 */
function uaVersion(id) {
  if (!settings.uav || !id) {
    return "";
  }
  return settings.uav.replace(/~/g, idName).replace(/iN/, id);
}

/**
 * fileName: !/bible/?/scanId/bN.cN.html
 * @param {string} bN - bookNameId
 * @param {string|number} cN - chapterId
 */
function fileCache(bN, cN) {
  let root = settings.html.replace("!", config.storage);
  return root
    .replace("?", taskId)
    .replace("scanId", settings.scan)
    .replace(/bN/, bN)
    .replace(/cN/, cN.toString());
}

/**
 * fileName: !/bible/?/scanId.json
 */
function fileFruit() {
  let root = settings.fruit.replace("!", config.storage);
  return root.replace("?", taskId).replace("scanId", settings.scan);
}

/**
 * fileName: !/bible/?/scanId/info.json
 */
function fileVersion() {
  let root = settings.html.replace("!", config.storage);
  return root
    .replace("?", taskId)
    .replace("scanId", settings.scan)
    .replace("bN.cN", "version")
    .replace(".html", ".json");
}

/**
 * fileName: !/bible/?/scanId/lang.json
 */
function fileLang() {
  let root = settings.html.replace("!", config.storage);
  return root
    .replace("?", taskId)
    .replace("scanId", settings.scan)
    .replace("bN.cN", "lang")
    .replace(".html", ".json");
}

/**
 * fileName: ./json/~.json
 * fileDoc
 * @param {string} identify
 */
function fileDoc(identify) {
  return settings.doc.replace("~", identify);
}

/**
 * Testing
 * @param {any} req
 */
export async function doDefault(req) {
  // let _langListFile = fileDoc("listOfLang").replace("/json", "/tmp/wbc");

  // let _incompleteFile = _langListFile.replace("listOfLang", "incomplete");
  // console.log(_langListFile);
  // console.log(_incompleteFile);
  for (let index = 0; index < 12; index++) {
    const progress = index;

    process.stdout.clearLine(0);
    process.stdout.cursorTo(0);
    process.stdout.write(progress + "%");
  }
  console.log("\nhello\n");
  for (let index = 0; index < 100; index++) {
    const progress = index;
    process.stdout.clearLine(0);
    process.stdout.cursorTo(0);
    process.stdout.write(progress + "%");
  }

  return "Oops";
}

/**
 * Check
 * @example
 * node run task wbc check
 * @param {any} req
 */
export async function doCheck(req) {
  const nonBook = [];
  const allBook = [];
  const duplicateBook = [];
  for (let index = 0; index < listOfBible.book.length; index++) {
    let obj = listOfBible.book[index];
    const identify = obj.identify;
    let file = fileDoc(identify);
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
      let docFilePath = fileDoc(identify);
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
 * Requests from live
 * @example
 * node run task wbc request
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
    let file = fileCache(bN, cN);
    await seek.write(file, wbcBody);
  }

  return new JSDOM(wbcBody);
}

/**
 * Add new version/language of Bible
 * request version, expected JSON
 * *.books
 * @param {any} req
 * @example
 * node run task wbc new
 * doNew({ query: { id: identify } });
 * doNew({ query: { id: identify, dir:"lang" } });
 */
export async function doNew(req) {
  if (!settings.scan) {
    return "no scanId";
  }

  const identify = req.query.id || taskCurrent?.identify || settings.scan;

  let docFilePath = fileDoc(identify);
  if (req.query.dir) {
    const abc = "/tmp/?".replace("?", req.query.dir);
    docFilePath = docFilePath.replace("/json", abc);
    // listOfBible.book.find(e=>e.);
    const setId = settings.list.find((e) => e.id == identify);
    if (setId && setId.identify) {
      if (seek.exists(docFilePath)) {
        fs.unlinkSync(docFilePath);
      }
      // await fs.unlink(docFilePath);
      docFilePath = docFilePath.replace(identify, setId.identify);
    }
  }

  if (seek.exists(docFilePath)) {
    return "record file already exists at:" + docFilePath;
  }

  const url = uaVersion(identify);

  if (!url) {
    return "no url";
  }
  if (!structure) {
    return "no structure";
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
  res.info.identify = identify;

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
  if (!req.query.dir) {
    await base.writeJSON(docFilePath.replace(".json", ".v0.json"), res, 2);
  }
  console.log("> write JSON at", docFilePath);
  console.log("> see its matching", url);
  return "done: info(name, year, etc), digit, testament and language(book, chapter, verse, etc) needed manually input";
}

/**
 * Read from local, development only for `examine`
 * @example
 * node run task wbc read
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
  let file = fileCache(bN, cN);

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
 * node run task wbc scan
 * node run task wbc scan --id=368
 * node run task wbc scan --id=1812 nonDoc=none
 * @param {any} req
 */
export async function doScan(req) {
  if (req.query.id) {
    settings.scan = req.query.id;
    taskCurrent = settings.list.find((e) => e.id == settings.scan);
  }

  // const identify = taskCurrent.identify;
  const identify = settings.scan;

  const versionData = await doScanVersion(identify);
  if (!taskCurrent && settings.scan) {
    if (versionData) {
      taskCurrent = {
        id: identify,
        ext: versionData.abbreviation,
        identify: identify,
        note: {},
      };
    } else {
      return "no taskCurrent";
    }
  }
  if (!versionData) {
    return "no versionData";
  }

  /**
   * @type {base.env.TypeOfBible}
   */
  let bible = {};

  if (identify) {
    let docFilePath = fileDoc(identify);

    bible = await base.readJSON(docFilePath, bible);
  } else {
    return "no identify";
  }

  // let infoData = await doScanInfo(identify);

  if (!bible.book) {
    bible.book = {};
  }

  // doScanCore doScanBook;
  await doScanBook(identify, bible, versionData).catch(async (error) => {
    // console.log("> ", identify, error);
    if (error.statusCode) {
      console.log("> error ", identify, error.statusCode);
    } else if (error.message) {
      console.log("> ", identify, error.message);
    }

    console.log("> waiting to continue in", settings.delay, "milliseconds");

    await new Promise((resolve) => setTimeout(resolve, settings.delay));
    await doScan({ query: { id: identify } });
  });

  if (taskCurrent && req.query.nonDoc == undefined) {
    if (taskCurrent.note) {
      if (taskCurrent.note.v) {
        if (identify) {
          if (listOfBible.version < settings.version) {
            listOfBible.version = settings.version;
          }

          let bookIndex = listOfBible.book.findIndex(
            (e) => e.identify == identify
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

            const iso = bookInfo.language.name;
            const file = config.fileOfLang.replace("~", iso);

            const lang = await base.readJSON(file, {
              digit: [],
              language: {},
              section: {},
              testament: {},
              book: {},
              locale: {},
            });

            if (lang.digit.length) {
              // const name = category.name;
              let digit = Object.assign({}, bible.digit, lang.digit);
              bible.digit = Object.values(digit);
              bible.language = Object.assign({}, bible.language, lang.language);
              bible.testament = Object.assign(
                {},
                bible.testament,
                lang.testament
              );

              let o = Object.keys(bible.book);

              for (let index = 0; index < o.length; index++) {
                const bookId = o[index];
                if (!bible.book) {
                  bible.book = {};
                }
                if (!bible.book[bookId]) {
                  bible.book[bookId] = {};
                }
                const description = bible.book[bookId].info.desc;
                // res.book[bookId].info = bible.book[bookId].info;
                bible.book[bookId].info = Object.assign(
                  {},
                  bible.book[bookId].info,
                  lang.book[bookId].info
                );

                bible.book[bookId].info.desc = description;
              }
            }
          } else {
            console.log(
              "> book record is",
              identify,
              "missing in",
              config.fileOfBook
            );
          }

          bible.info.version = taskCurrent.note.v;
          bible.info.identify = identify;

          let docFilePath = fileDoc(identify);
          await base.writeJSON(docFilePath, bible);
          console.log("> replaced JSON at", docFilePath);
        }
      }
    }
  }

  let fruitFileName = fileFruit();
  // NOTE: write on each book
  await base.writeJSON(fruitFileName, bible, 2);
  console.log("> write JSON at", fruitFileName);
  let msg = "scanned: " + identify;

  return msg;
}

/**
 * internal: read or request of version
 * @param {string} identify
 */
async function doScanVersion(identify) {
  try {
    let data;
    let file = fileVersion();
    let local = seek.exists(file);
    if (local) {
      data = await base.readJSON(file);
    } else {
      const url = uaVersion(identify);
      data = await (await fetch(url)).json();
      await base.writeJSON(file, data, 2);
    }
    return data;
  } catch (error) {
    return null;
  }
}

/**
 * internal: book of (version, chapter, lang)
 * @param {string} identify
 * @param {base.env.TypeOfBible} bible
 * @param {any} versionData
 */
async function doScanBook(identify, bible, versionData) {
  // const versionData = await doScanVersion(identify);
  const langData = await doScanLang();

  if (versionData && versionData.books) {
    const books = versionData.books;
    for (let bIndex = 0; bIndex < books.length; bIndex++) {
      const bookOfResponse = books[bIndex];
      const bookOfCategory = category.book.find(
        (e) =>
          e.info.shortname.toLowerCase() == bookOfResponse.usfm.toLowerCase()
      );
      // const bookOfCategory = category.book.find(
      //   (e) =>
      //     e.info.shortname.toLowerCase() ==
      //     bookOfResponse.abbreviation.toLowerCase()
      // );
      if (bookOfCategory) {
        const bookId = bookOfCategory.id;
        // const bookNameId = bookOfResponse.usfm;
        const chapters = bookOfResponse.chapters;
        if (!bible.book[bookId]) {
          bible.book[bookId] = {};
        }
        if (!langData.book[bookId]) {
          langData.book[bookId] = {
            info: {},
          };
        }
        const langBookInfo = {
          name: bookOfResponse.human,
          shortname: bookOfResponse.abbreviation,
          abbr: [],
          desc: bookOfResponse.human_long,
        };
        langData.book[bookId].info = langBookInfo;

        for (let cIndex = 0; cIndex < chapters.length; cIndex++) {
          const chapter = chapters[cIndex];
          // const chapterId = chapter.human;
          const [bookNameId, chapterId] = chapter.usfm.split(".");

          if (chapter.canonical == true) {
            const dom = await doScanChapter(bookNameId, chapterId);
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
              // console.log(bookNameId, chapterId);
              process.stdout.clearLine(0);
              process.stdout.cursorTo(0);
              process.stdout.write(
                identify + " > " + bookNameId + "." + chapterId
              );
            }
          }
        }
      }
    }
    // Update lang
    const langFile = fileLang();
    await base.writeJSON(langFile, langData, 2);
  }
}

/**
 * internal: read or request of chapter
 * @param {string} bookNameId
 * @param {string} chapterId
 */
async function doScanChapter(bookNameId, chapterId) {
  let chapterFile = fileCache(bookNameId, chapterId);
  let alreadyCache = seek.exists(chapterFile);
  if (alreadyCache) {
    return await JSDOM.fromFile(chapterFile);
  } else {
    return await doRequestCore(bookNameId, chapterId, true);
  }
}

/**
 * internal: read of lang
 */
async function doScanLang() {
  const langFile = fileLang();
  const res = await base.readJSON(langFile, {
    digit: [],
    language: {},
    section: {},
    testament: {},
    book: {},
  });

  let digit = Object.assign({}, category.digit, res.digit);
  res.digit = Object.values(digit);

  res.language = Object.assign({}, category.language, res.language);
  res.section = Object.assign({}, category.section, res.section);
  res.testament = Object.assign({}, category.testament, res.testament);
  // res.locale = Object.assign({}, category.locale, res.locale);

  return res;
}

/**
 * internal: book of (dump)
 * @param {string} identify
 * @param {base.env.TypeOfBible} bible
 */
async function doScanCore(identify, bible) {
  await doScanVersion(identify);
  const books = category.book;

  for (let index = 0; index < books.length; index++) {
    const book = books[index];
    const bookId = book.id;
    // const book = books[bookId];
    // console.log("bookId", bookId);
    const bookNameId = book.info.abbr[0].toUpperCase();
    // console.log("bookNameId", bookId, bookNameId);
    let bookDetail = book.clue;
    // let chapterCount = bookDetail.c;
    let chapterCount = bookDetail.v;
    if (!bible.book[bookId]) {
      bible.book[bookId] = {};
    }
    for (let index = 0; index < chapterCount.length; index++) {
      // const verseCount = chapterCount[index];
      const chapterId = index + 1;
      let file = fileCache(bookNameId, chapterId);

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
 * Scan all
 * @example
 * node run task wbc scanAll
 * node run task wbc scanAll --nonDoc=none
 * node run task wbc scanAll --o=empty
 * node run task wbc scanAll --o=equalTo v=3
 * node run task wbc scanAll --o=lessThan v=6
 * node run task wbc scanAll --o=lessOrEqual v=7
 * node run task wbc scanAll --o=greaterThan v=1
 * node run task wbc scanAll --o=greaterOrEqual v=0
 * node run task wbc scanAll --o=greaterOrEqual v=0 nonDoc=none
 * @param {any} req
 */
export async function doScanAll(req) {
  let scanedList = [];
  let ope = req.query.o;
  let ver = req.query.v;
  let nonDoc = req.query.nonDoc;
  for (let index = 0; index < settings.list.length; index++) {
    let data = settings.list[index];
    let tmp = doScanAllFilter(data, ope, ver);
    if (tmp) {
      let id = data.id;
      let query = { id: id };
      if (nonDoc) {
        query.nonDoc = nonDoc;
      }
      // await doScan({ query: { id: id, nonDoc: "none" } });
      await doScan({ query: query });
      scanedList.push(id);
    }
  }
  console.log("scanned", scanedList);
  console.log("total", scanedList.length);
  return "done";
}

/**
 * @param {TypeOfListData} data
 * @param {any} ope - note version operator
 * @param {any} ver - note version value
 */
function doScanAllFilter(data, ope, ver) {
  let version = data.note.v;
  if (!ope && !ver) {
    return true;
  } else if (version == undefined) {
    if (ope == "empty") {
      return true;
    }
  } else {
    if (ope == "equalTo" && version == ver) {
      return true;
    } else if (ope == "lessThan" && version < ver) {
      return true;
    } else if (ope == "lessOrEqual" && version <= ver) {
      return true;
    } else if (ope == "greaterThan" && version > ver) {
      return true;
    } else if (ope == "greaterOrEqual" && version >= ver) {
      return true;
    }
  }
  return false;
}

/**
 * Map and scan contents starting from configuration
 * Expected: 3085
 * @example
 * node run task wbc content
 * @param {any} req
 */
export async function doMapContent(req) {
  return await doMapCore(async (info) => {
    const identify = info.id;
    const listIndex = settings.list.findIndex((e) => e.id == identify);

    if (listIndex == -1) {
      settings.list.push({
        id: identify,
        ext: info.abbreviation,
        identify: identify,
        note: {},
      });
      const msg = await doScan({ query: { id: identify } });
      console.log(msg);
      if (msg.startsWith("scanned")) {
        await base.writeJSON(settings_file, settings, 2);
        console.log("updated settings");
      }
    } else {
      console.log("already scanned", identify);
    }
  });
}

/**
 * Map and scan info then write
 * @example
 * node run task wbc context
 * @param {any} req
 */
export async function doMapContext(req) {
  // await doMapCore(async (info) => {});
  return await doMapCore(async (info) => {
    const identify = info.id;
    const iso = info.language.iso_639_3;
    // const file = config.fileOfLang.replace("~", iso);
    // console.log("lang file", file);
    // const abc = await doNew({ query: { id: identify } });
    // const msg = await doNew({ query: { id: identify, dir: iso } });
    const msg = await doNew({ query: { id: identify, dir: "tpl-json" } });
    console.log(iso, msg);
  });
}

/**
 * Map and scan each iso-639-3 as language
 * Expected: 2045
 * @example
 * node run task wbc language
 * @param {any} req
 */
export async function doMapLanguage(req) {
  // await doMapCore(async (info) => {});
  let _langFile = fileDoc("listOfLang").replace("/json", "/tmp/wbc");

  /** @type {base.env.ContextOfLanguage[]} */
  const _langList = await seek.readJSON(_langFile, []);
  /**
   * @type {{incomplete:Array<number>, fail:Array<{id:number, e:any}>}}
   */
  const _todo = {
    incomplete: [],
    fail: [],
  };
  // const _incomplete = [];

  const message = await doMapCore(async (info) => {
    const identify = info.id;
    const infoLang = info.language;
    const iso = infoLang.iso_639_3;
    if (!_langList.find((e) => e.name == iso)) {
      /**
       * @type {base.env.ContextOfLanguage}
       */
      let langObj = {
        text: "",
        textdirection: "",
        name: "",
      };
      if (infoLang.name) {
        langObj.text = infoLang.name;
      }
      if (infoLang.text_direction) {
        langObj.textdirection = infoLang.text_direction;
      }
      if (infoLang.iso_639_3) {
        langObj.name = infoLang.iso_639_3;
      }
      if (infoLang.local_name) {
        langObj.local = infoLang.local_name;
      }

      _langList.push(langObj);
    }
    try {
      let msg = await env.createLanguage(iso, identify);
      if (msg.startsWith("incomplete")) {
        _todo.incomplete.push(identify);
      }
      console.log(msg);
    } catch (error) {
      _todo.fail.push({ id: identify, e: error });
      console.log(iso, identify, error);
    }
  });
  await seek.writeJSON(_langFile, _langList, 2);
  let _todoFile = _langFile.replace("listOfLang", "todo");
  await seek.writeJSON(_todoFile, _todo, 2);

  console.log(
    "> incomplete",
    _todo.incomplete.length,
    "fail",
    _todo.fail.length
  );
  return message;
}

/**
 * Map all [uco, ula]
 * @param {function(object):Promise<void>} callback
 */
async function doMapCore(callback) {
  try {
    const urlConfiguration = settings.uco?.replace(/~/g, idName);
    let dataConfiguration = await ask.request(urlConfiguration);
    const configJSON = JSON.parse(dataConfiguration);
    const languages = configJSON.response.data.default_versions;
    // console.log(languages[0]);
    // const language = languages[1];

    for (let lIndex = 0; lIndex < languages.length; lIndex++) {
      const language = languages[lIndex];
      const langTag = language.language_tag;

      const urlLanguage = settings.ula
        ?.replace(/~/g, idName)
        .replace(/lT/, langTag);

      let dataLanguage = await ask.request(urlLanguage);

      const langJSON = JSON.parse(dataLanguage);
      const versions = langJSON.response.data.versions;

      for (let index = 0; index < versions.length; index++) {
        await callback(versions[index]);
      }
    }
  } catch (error) {
    console.log(error);
  }
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
