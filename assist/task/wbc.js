import { seek } from "lethil";
import * as root from "./wbc.root.js";

const env = root.base.env;
const config = env.config;
const listOfBible = env.listOfBible;
// const category = env.category;
// const structure = env.structure;

/**
 * Testing
 * @example
 * node run task wbc --book=GEN chapter=1 id=463
 * @param {any} req
 */
export async function doDefault(req) {
  try {
    const res = await root.loadChapter(req.query);
    return res.status;
  } catch (error) {
    return error.message;
  }
}

/**
 * Check
 * @example
 * node run task wbc check
 * @param {any} req
 */
export async function doCheck(req) {
  return "???";
}

/**
 * Requests from live
 * 463/JER.35.NABRE
 * 120, 3663
 * @example
 * node run task wbc request
 * node run task wbc request --book=GEN chapter=1 id=463
 * node run task wbc request --book=GEN chapter=1 id=463 save=false readOnly=false
 * @param {any} req
 */
export async function doRequest(req) {
  return root
    .loadChapter(req.query)
    .then((res) => {
      if (res && res.status > 0) {
        return res.status;
      }
    })
    .catch((err) => {
      return err.message;
    });
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
  return "???";
}

/**
 * Read from local, development only for `examine`
 * @example
 * node run task wbc read --book=GEN chapter=1 id=463 save=false readOnly=true
 * @param {any} req
 */
export async function doRead(req) {
  // const save = req.query.save;
  // const bN = "REV";
  // const cN = "7";

  req.query.save = false;

  return root
    .loadChapter(req.query)
    .then(async (res) => {
      if (res && res.status > 0) {
        let file = "./tmp/test-read-chapter.json";
        await root.base.writeJSON(file, res, 2);
        return "> write " + file;
      }
    })
    .catch((err) => {
      return err.message;
    });
}

/**
 * Scan from live or local
 * @example
 * node run task wbc scan
 * node run task wbc scan --id=368
 * node run task wbc scan --id=1812 nonDoc=none
 * node run task wbc scan --id=463 nonDoc=none
 * 120
 * @param {any} req
 */
export async function doScan(req) {
  if (req.query.id) {
    root.task.current = root.findTask(req.query.id);
  }
  const identify = root.task.scanId;
  const versionDetail = await root.scanVersionDetail(identify);
  if (!root.task.current && identify) {
    if (versionDetail.data) {
      root.task.current = {
        id: identify,
        ext: versionDetail.data.abbreviation,
        identify: identify,
        note: {},
      };
    } else {
      return "no taskCurrent";
    }
  }

  if (!versionDetail) {
    return "no versionData";
  }

  /**
   * @type {root.base.env.TypeOfBible}
   */
  let bible = {};

  if (identify) {
    let docFilePath = root.fileDoc(identify);

    bible = await root.base.readJSON(docFilePath, bible);
  } else {
    return "no identify";
  }

  if (!bible.book) {
    bible.book = {};
  }

  await root.scanBook(identify, bible, versionDetail).catch(async (error) => {
    let _ms = 3000;
    if (error.statusCode) {
      console.info(">", error.statusCode);
    } else if (error.message) {
      // Resource was not loaded. Status; 503
      console.info(">", error.message);
      if (error.message.startsWith("Resource was not loaded")) {
        _ms = root.settings.delay;
      }
    }

    console.info("...continue in %d ms", _ms);
    await new Promise((resolve) => setTimeout(resolve, _ms));

    await doScan({ query: { id: identify } });
  });

  if (root.task.current && req.query.nonDoc == undefined) {
    if (root.task.current.note) {
      if (root.task.current.note.v) {
        if (identify) {
          if (listOfBible.version < root.settings.version) {
            listOfBible.version = root.settings.version;
          }

          let bookIndex = listOfBible.book.findIndex(
            (e) => e.identify == identify
          );
          if (bookIndex >= 0) {
            listOfBible.book[bookIndex].version = root.task.current.note.v;
            listOfBible.updated = new Date();
            await root.base.writeJSON(config.fileOfBook, listOfBible, 2);
            console.info("> updated JSON at", config.fileOfBook);

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
            const file = env.fileLanguage(iso);

            const lang = await root.base.readJSON(file, {
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
            console.info(
              "> book record is",
              identify,
              "missing in",
              config.fileOfBook
            );
          }

          bible.info.version = root.task.current.note.v;
          bible.info.identify = identify;

          let docFilePath = root.fileDoc(identify);
          await root.base.writeJSON(docFilePath, bible);
          console.info("> replaced JSON at", docFilePath);
        }
      }
    }
  }

  let fruitFileName = root.fileFruit();
  // NOTE: write each book
  await root.base.writeJSON(fruitFileName, bible, 2);
  // NOTE: update setting
  await root.settingWrite();
  console.info(" > write:", fruitFileName);
  let msg = "scanned: " + identify;

  return msg;
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
  for (let index = 0; index < root.task.list.length; index++) {
    let data = root.task.list[index];
    let tmp = root.scanFilter(data, ope, ver);
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
  console.info("scanned", scanedList);
  console.info("total", scanedList.length);
  return "done";
}

/**
 * Map and scan contents starting from configuration
 * Expected: 3085
 * @example
 * node run task wbc content
 * @param {any} req
 */
export async function doMapContent(req) {
  return await root.mapAll(async (info) => {
    if (info) {
      let _ms = 300;
      let keyNote = "?";
      const identify = info.id;

      root.findTask(identify);

      if (!root.task.current) {
        root.task.current = {
          id: identify,
          ext: info.abbreviation,
          identify: identify,
          note: {},
        };
        root.task.list.push(root.task.current);
        const msg = await doScan({ query: { id: identify } });
        if (msg.startsWith("scanned")) {
          await root.settingWrite();
          keyNote = "newly";
        } else {
          console.info(msg);
        }
      } else {
        _ms = 60;
        // exists in (setting.list)
        keyNote = "already";
      }
      // let scanCount = root.task.list.length;

      console.info(
        "> scanned %s: %d, continue in %d ms",
        keyNote,
        identify,
        _ms
      );
      await new Promise((resolve) => setTimeout(resolve, _ms));
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
  // await mapAll(async (info) => {});
  return await root.mapAll(async (info) => {
    const identify = info.id;
    const iso = info.language.iso_639_3;
    // const file = env.fileLanguage(iso);
    // console.info("lang file", file);
    // const abc = await doNew({ query: { id: identify } });
    // const msg = await doNew({ query: { id: identify, dir: iso } });
    const msg = await doNew({ query: { id: identify, dir: "tpl-json" } });
    console.info(iso, msg);
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
  // await root.mapAll(async (info) => {});
  let _langFile = root.fileDoc("listOfLang").replace("/json", "/tmp/wbc");

  /** @type {root.base.env.RowOfLanguage[]} */
  const _langList = await seek.readJSON(_langFile, []);
  /**
   * @type {{incomplete:Array<number>, fail:Array<{id:number, e:any}>}}
   */
  const _todo = {
    incomplete: [],
    fail: [],
  };
  // const _incomplete = [];

  const message = await root.mapAll(async (info) => {
    const identify = info.id;
    const infoLang = info.language;
    const iso = infoLang.iso_639_3;
    if (!_langList.find((e) => e.name == iso)) {
      /**
       * @type {root.base.env.RowOfLanguage}
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
      console.info(msg);
    } catch (error) {
      _todo.fail.push({ id: identify, e: error });
      console.info(iso, identify, error);
    }
  });
  await seek.writeJSON(_langFile, _langList, 2);
  let _todoFile = _langFile.replace("listOfLang", "todo");
  await seek.writeJSON(_todoFile, _todo, 2);

  const _tL = _todo.incomplete.length;
  const tF = _todo.fail.length;
  console.info("> incomplete: %d, fail: %d", _tL, tF);
  return message;
}

/**
 * Rescan skipped list
 * @example
 * node run task wbc skip
 * @param {any} req
 */
export async function doSkip(req) {
  let skippedBible = root.settings.skip;

  const successIdentifies = [];
  for (let oIndex = 0; oIndex < skippedBible.length; oIndex++) {
    const elBi = skippedBible[oIndex];
    const id = elBi.identify;
    const successBooks = [];
    for (let bIndex = 0; bIndex < elBi.books.length; bIndex++) {
      const elBo = elBi.books[bIndex];
      const book = elBo.book;
      const successChapters = [];
      for (let cIndex = 0; cIndex < elBo.chapters.length; cIndex++) {
        const chapter = elBo.chapters[cIndex];
        // Testing
        // if (chapter < 10) {
        //   successChapters.push(chapter);
        // }

        await root
          .loadChapter({
            id: id,
            book: book,
            chapter: chapter,
          })
          .then((res) => {
            if (res && res.status > 0) {
              successChapters.push(chapter);
              console.info(` > ${id} ${book}.${chapter} ~ ${res.status}`);
            }
          })
          .catch((err) => {
            console.error(` > ${id} ${book}.${chapter} ...${err.message}`);
          });
      }

      elBo.chapters = elBo.chapters.filter((e) => !successChapters.includes(e));
      if (elBo.chapters.length == 0) {
        successBooks.push(book);
      }
    }
    elBi.books = elBi.books.filter((e) => !successBooks.includes(e.book));
    if (elBi.books.length == 0) {
      successIdentifies.push(id);
    }
  }

  root.settings.skip = skippedBible.filter(
    (e) => !successIdentifies.includes(e.identify)
  );

  await root.settingWrite();

  return "doSkip";
}

/**
 * Testing
 * @example
 * node run task wbc test
 * @param {any} req
 */
export async function doTest(req) {
  // listOfBible;
  return "testing";
}
