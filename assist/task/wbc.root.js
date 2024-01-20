import { JSDOM } from "jsdom";
// import * as fs from "fs";
import { seek } from "lethil";
import * as base from "./base.js";
export * as base from "./base.js";

const env = base.env;
const config = env.config;
// const listOfBible = env.listOfBible;
const category = env.category;
// const structure = env.structure;

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
 * @property {string} url - bible.book.chapter
 * @property {string} uav - api version - url api version
 * @property {string} uco - api configuration
 * @property {string} ula - api language
 * @property {number} version - version number
 * @property {number} delay - in seconds
 * @property {TypeOfListData[]} list
 * property {any[]} skip - skipped chapter in book
 * property {TypeOfSkip[]} skip - skipped chapter in book
 * @property {TypeOfSkip[]} skip - skipped chapter in book
 *
 * @typedef {Object} TypeOfSkip - {id:12, books:[]}
 * @property {string} identify - bibleId (scanId)
 * @property {TypeOfSkipBook[]} books
 *
 * @typedef {Object} TypeOfSkipBook - {id:12, chapter:["1"]}
 * @property {string} book - bookId (GEN, etc)
 * @property {any[]} chapters
 */

const taskId = "wbc";
const idName = "bible";

const _settingsFile = "./assets/?/settings.json".replace("?", taskId);

/**
 * @type {TypeOfSetting}
 */
// @ts-ignore
export const settings = await base.readJSON(_settingsFile, {});

/**
 * update setting
 */
export async function settingWrite() {
  return base.writeJSON(_settingsFile, settings, 2);
}

export const task = {
  scanId: settings.scan,
  list: settings.list,
  current: settings.list.find((e) => e.id == settings.scan),
};

/**
 * if `id` provided `task.scanId` is updated
 * @param {string} id
 */
export function findTask(id) {
  if (id) {
    task.scanId = id;
  }
  task.current = settings.list.find((e) => e.id == task.scanId);
  return task.current;
}

/**
 *
 * get scanId
 * @param {string} [identify]
 * @returns {string} - identify || task.current?.id || task.scanId;
 */
export function scanIdentify(identify) {
  return identify || task.current?.id || task.scanId;
}

/**
 * //~.com/~/iN/bN.cN.iE
 * @param {string} bN - bookNameId
 * @param {string|number} cN - chapterId
 * param {any} [id] - identity
 * param {string|number} [ext] - extension
 * param {string} cN - chapterId
 */
export function urlChapter(bN, cN) {
  if (!settings.url || !task.current) {
    return "";
  }
  return settings.url
    .replace(/~/g, idName)
    .replace(/iN/, task.current.id)
    .replace(/bN/, bN)
    .replace(/cN/, cN.toString())
    .replace(/iE/, task.current.ext);
}

/**
 * //~.com/api/~/version/iN
 * @param {string} id
 */
export function uaVersion(id) {
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
export function fileCache(bN, cN) {
  let root = settings.html.replace("!", config.storage);
  const scanId = scanIdentify();
  return root
    .replace("?", taskId)
    .replace("scanId", scanId)
    .replace(/bN/, bN)
    .replace(/cN/, cN.toString());
}

/**
 * fileName: !/bible/?/scanId.json
 */
export function fileFruit() {
  let root = settings.fruit.replace("!", config.storage);
  const scanId = scanIdentify();
  return root.replace("?", taskId).replace("scanId", scanId);
}

/**
 * fileName: !/bible/?/scanId/info.json
 * @param {string} identify
 */
export function fileVersion(identify) {
  let root = settings.html.replace("!", config.storage);
  const scanId = scanIdentify(identify);
  return root
    .replace("?", taskId)
    .replace("scanId", scanId)
    .replace("bN.cN", "version")
    .replace(".html", ".json");
}

/**
 * fileName: !/bible/?/scanId/lang.json
 */
export function fileLang() {
  let root = settings.html.replace("!", config.storage);
  const scanId = scanIdentify();
  return root
    .replace("?", taskId)
    .replace("scanId", scanId)
    .replace("bN.cN", "lang")
    .replace(".html", ".json");
}

/**
 * fileName: ./json/~.json
 * fileDoc
 * @param {string} identify
 */
export function fileDoc(identify) {
  return settings.doc.replace("~", identify);
}

// /**
//  * @example
//  * await new Promise((resolve) => resolveInterval(30, resolve));
//  * @param {number} seconds - seconds of time (seconds * 1000) / 60;

//  * @param {(value: any) => void} resolve
//  * @param {string} [progress] - ...continue in # seconds
//  * @param {string} [success] - ...continuing after # seconds
//  */
// export function resolveInterval(seconds, resolve, progress, success) {
//   let milliseconds = (seconds * 1000) / 60;
//   // let countDown = seconds;
//   let _progress = "...continue in # seconds";
//   let _success = "...continuing at # seconds";
//   if (progress) {
//     _progress = progress;
//   }
//   // setTimeout(resolve, milliseconds);

//   setInterval(() => {
//     process.stdout.clearLine(1);
//     process.stdout.cursorTo(0);
//     if (seconds == 0) {
//       if (success) {
//         _success = success;
//       }
//       let _msg = _success.replace("#", seconds.toString());

//       process.stdout.write(_msg);
//       return resolve(1);
//     }
//     seconds--;

//     let _msg = _progress.replace("#", seconds.toString());

//     process.stdout.write(_msg);
//     // process.stdout.end();
//   }, milliseconds);
// }

/**
 * Request chapter
 * @param {string} bN
 * @param {string|number} cN
 * @param {boolean} [save] - if true write tmp HTML file
 */
export async function requestChapter(bN, cN, save) {
  // try {
  // } catch (error) {
  //   // throw new Error("Parameter is not a number!");
  //   // error.statusCode = 404;
  //   throw error;
  // }
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
 * org: doScanAllFilter
 * @param {TypeOfListData} data
 * @param {any} ope - note version operator
 * @param {any} ver - note version value
 */
export function scanFilter(data, ope, ver) {
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
 * org: doScanCore
 * internal: book of (dump)
 * @param {string} identify
 * @param {base.env.TypeOfBible} bible
 */
export async function scanCore(identify, bible) {
  await scanVersion(identify);
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
      // let file = fileCache(bookNameId, chapterId);

      // const dom = await doRequestCore(bookNameId, chapterId, true);
      // const res = await examine(dom);
      // bible[bookId][chapterId] = res;
      // console.log(file);

      // let dom;
      // let alreadyCache = seek.exists(file);
      // if (alreadyCache) {
      //   dom = await JSDOM.fromFile(file);
      // } else {
      //   dom = await requestChapter(bookNameId, chapterId, true);
      // }
      const dom = await loadChapter(bookNameId, chapterId);

      if (dom) {
        const res = await examineChapter(dom);
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
 * org: doScanLang
 * internal: read of lang
 */
export async function scanLang() {
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
 * org: doScanVersion
 * internal: read or request of version
 * @param {string} identify
 */
export async function scanVersion(identify) {
  try {
    let data;
    let file = fileVersion(identify);
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
 * org: doScanBook
 * internal: book of (version, chapter, lang)
 * @param {string} identify
 * @param {base.env.TypeOfBible} bible
 * @param {any} versionData
 */
export async function scanBook(identify, bible, versionData) {
  // const versionData = await doScanVersion(identify);
  const langData = await scanLang();

  const tmp = {
    bookNameId: "",
  };

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
          if (chapter.canonical == true) {
            // const chapterId = chapter.human;
            const [bookNameId, chapterId] = chapter.usfm.split(".");
            if (!tmp.bookNameId) {
              tmp.bookNameId = bookNameId;
            }
            if (!bible.book[bookId].chapter) {
              bible.book[bookId].chapter = {};
            }
            if (!bible.book[bookId].chapter[chapterId]) {
              bible.book[bookId].chapter[chapterId] = {};
            }
            await loadChapter(bookNameId, chapterId)
              .then(async (dom) => {
                if (dom) {
                  const res = await examineChapter(dom);
                  if (res && res.status > 0) {
                    bible.book[bookId].chapter[chapterId].verse = res.verse;
                  } else {
                    // throw new Error("EXAM is empty");
                    skipHelper(identify, bookNameId, chapterId);
                  }

                  process.stdout.clearLine(0);
                  process.stdout.cursorTo(0);
                  let _lPBId = bookNameId;
                  if (bookNameId != tmp.bookNameId) {
                    _lPBId = tmp.bookNameId + " - " + bookNameId;
                  }

                  // let _lPId = " > " + identify + " > " + _lPBId;
                  let _lPId = "... " + identify + " > " + _lPBId;
                  process.stdout.write(_lPId + "." + chapterId);
                } else {
                  // throw new Error("JSDOM is empty");
                  skipHelper(identify, bookNameId, chapterId);
                }
              })
              .catch((err) => {
                let msg = "Unknown";
                if (err) {
                  msg = err;
                  if (err.message) {
                    msg = err.message;
                  } else if (err.statusCode) {
                    msg = err.statusCode;
                  }
                }
                // NOTE: Resource was not loaded. Status; 503
                if (msg.startsWith("Resource was not loaded")) {
                  console.info("... error RWNL", msg);
                } else {
                  skipHelper(identify, bookNameId, chapterId);
                }
                throw new Error(msg);
              });
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
 * Push to skip
 * @param {string} identify
 * @param {string} bookNameId
 * @param {any} chapterId
 */
function skipHelper(identify, bookNameId, chapterId) {
  if (!settings.skip) {
    settings.skip = [];
  }
  let _indexIdentify = settings.skip.findIndex((e) => e.identify == identify);
  if (_indexIdentify < 0) {
    _indexIdentify =
      settings.skip.push({
        identify: identify,
        books: [],
      }) - 1;
  }
  const _skipBooks = settings.skip[_indexIdentify].books;
  let _indexBook = _skipBooks.findIndex((e) => e.book == bookNameId);
  if (_indexBook < 0) {
    _indexBook =
      _skipBooks.push({
        book: bookNameId,
        chapters: [],
      }) - 1;
  }
  const _skipChapters = _skipBooks[_indexBook].chapters;
  let _indexChapter = _skipChapters.findIndex((e) => e == chapterId);
  if (_indexChapter < 0) {
    _skipChapters.push(chapterId);
  }
}

/**
 * internal: read/request the chapter
 * @param {string} bookNameId
 * @param {string | number} chapterId
 * @param {boolean} [readOnly]
 */
export async function loadChapter(bookNameId, chapterId, readOnly) {
  let chapterFile = fileCache(bookNameId, chapterId);
  let alreadyCache = seek.exists(chapterFile);
  if (alreadyCache) {
    return await JSDOM.fromFile(chapterFile);
  } else {
    if (readOnly) {
      throw new Error("readOnly");
    }
    return await requestChapter(bookNameId, chapterId, true);
  }
}

/**
 * org: doMapCore, mapConfiguration mapAll
 * Map all [uco, ula]
 * @param {function(object):Promise<void>} callback - each of version data
 */
export async function mapAll(callback) {
  try {
    const urlConfiguration = settings.uco.replace(/~/g, idName);
    // let _configuration = await ask.request(urlConfiguration);
    // const configJSON = JSON.parse(_configuration);
    let configJSON = await (await fetch(urlConfiguration)).json();
    const languages = configJSON.response.data.default_versions;
    // console.log(languages[0]);
    // const language = languages[1];

    for (let lIndex = 0; lIndex < languages.length; lIndex++) {
      const language = languages[lIndex];
      const langTag = language.language_tag;

      const urlLanguage = settings.ula
        ?.replace(/~/g, idName)
        .replace(/lT/, langTag);

      // let _language = await ask.request(urlLanguage);
      // const langJSON = JSON.parse(_language);
      let langJSON = await (await fetch(urlLanguage)).json();

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
export async function examineChapter(dom) {
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
