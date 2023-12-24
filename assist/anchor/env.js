import core, { seek } from "lethil";

/**
 * @typedef {Object} ContextOfLanguage
 * @property {string} text - language name [English]
 * @property {string} textdirection - Text direction eg.[ltr]
 * @property {string} name - name [en]
 *
 * @typedef {Object} TypeOfInfo - ?
 * @property {string} identify - id of the Bible [1,2]
 * @property {string} name - Bible name eg.[King James Version]
 * @property {string} shortname - Shortname eg.[KJV]
 * @property {string} year - Year
 * @property {ContextOfLanguage} language - Language
 * @property {number} version - Version
 * @property {string} [description] - Description
 * @property {string} [publisher] - Publisher
 * @property {string} [contributors] - Contributors
 * @property {string} [copyright] - Copyright
 *
 * @typedef {Object<string, string>} TypeOfNote - ???
 *
 * @typedef {string[]} TypeOfDigit - Number in Language
 *
 * @typedef {Object} TypeOfBibleLocale - Each Bible locale
 * @property {string} chapter - Chapter in language eg.[Chapter, Alian]
 * @property {string} verse - Verse in language eg.[Verse, Aneu]
 *
 * @typedef {{info:{name:string,shortname:string, desc?:string}, other:any}} NameOfTestament - testament
 * @typedef {Object<number,NameOfTestament>} TypeOfTestament - Bible testament
 *
 * @typedef {Object<number,Object<number,Object<number,ContextOfStory>>>} TypeOfStory - Bible story
 *
 * @typedef {Object} ContextOfStory - Each Bible locale
 * @property {string} text
 * @property {string} [title]
 * @property {string} [ref]
 * @property {string} [other]
 *
 * @typedef {Object} InfoOfBook - ?
 * @property {string} name - Name of the book eg.[Genesis, Piancilna]
 * @property {string} shortname - shortname of the book eg.[Gen, Pian]
 * @property {string[]} abbr - Name abbreviation eg.[]
 * @property {string} desc - Book description
 *
 * @typedef {Object<any,any>} _BookTopic - ?
 *
 * @typedef {Object} ContextOfVerse - ?
 * @property {string} text - Context eg.[In the beginning...]
 * @property {string} [title] - Title eg.[The Creation of the World...]
 * @property {string} [heading] - Heading eg.[The Creation of the World...]
 * @property {string} [ref] - Reference eg.[Gen.9.1,Gen.1.28..]
 * @property {string} [merge] - is Merge eg.[2]
 *
 * @typedef {Object<number,ContextOfVerse>} TypeOfVerse -
 *
 * @typedef {Object<number,{info:InfoOfBook, topic: _BookTopic, chapter:Object<number,{verse:TypeOfVerse}>}>} TypeOfBibleBook - Bible book
 *
 * @typedef {Object} TypeOfBible - ?
 * @property {TypeOfInfo} info
 * @property {TypeOfNote} note
 * @property {TypeOfDigit} digit
 * @property {TypeOfBibleLocale} language
 * @property {TypeOfTestament} testament
 * @property {TypeOfStory} story
 * @property {TypeOfBibleBook} book
 */

/**
 * @typedef {Object} BookOfCategory
 * @property {number} t - testamentId
 * property {number} b - bookId
 * @property {number} s - sectionId
 * @property {number} c - total chapter
 * @property {number[]} v - list of each total verses
 *
 * @typedef {Object} TypeOfCategory
 * @property {Object} name - a set of name eg.[section, testament, book, digit]
 * @property {Object<number,string>} name.section - eg[Law,History ..]
 * @property {TypeOfTestament} name.testament
 * property {Object<number,{info:InfoOfBook}>} name.book
 * @property {TypeOfDigit} name.digit
 * @property {Object<number,Object<number,number[]>>} section
 * property {Object<string,BookOfCategory>} book
 * @property {{id:string, info:InfoOfBook, clue:BookOfCategory}[]} book
 * @property {TypeOfBibleLocale} language
 * @property {Object<string,string>} locale
 */

/**
 * @typedef {Object} TypeOfBook
 * @property {string} name - app name
 * @property {Date} updated - last modified
 * @property {number} version
 * @property {TypeOfInfo[]} book - book info
 */

/**
 * @typedef {Object} TypeOfReference
 * @property {string} book - book name
 * @property {string} chapter - chapter
 * @property {string} verse - verse from
 * @property {string} to - verse to
 *
 * @typedef {{bible:TypeOfBible, category:TypeOfCategory}} TypeOfLoadedBible
 */

const fileOfBook = "./book.json";
const fileOfCategory = "./category.json";
const fileOfStructure = "./structure.json";

/**
 * Template `./structure.json`
 * set to {} note, story, book
 * info: required manully update
 * digit: required manully update
 * language: required manully update
 * testament: required manully update
 * @type {TypeOfBible}
 */
export const structure = await seek.readJSON(fileOfStructure);

/**
 * `./category.json`
 * @type {TypeOfCategory}
 */
export const category = await seek.readJSON(fileOfCategory);

/**
 * Index of Book(Bible) from `./book.json`
 * listOfBible
 * @type {TypeOfBook}
 */
export const listOfBible = await seek.readJSON(fileOfBook);

/**
 * Loaded Bible list
 * type {TypeOfBible[]}
 * @type {TypeOfLoadedBible[]}
 */
export const listOfLoadedBible = [];

/**
 * Merge core.config & local
 */
export const config = core.config.merge({
  fileOfBook: fileOfBook,
  fileOfCategory: fileOfCategory,
  fileOfStructure: fileOfStructure,
  fileOfBible: "./json/~.json",
  fileOfLang: "./lang/~.json",
});

/**
 * @example
 * Gen 1:3, 2:2-5; Exo 2:4; Gamlak Vakna 2:4
 * Gen 1:3, 7-9; Exo 2:4
 * Gen.1:3, 2:7-9; Exo.2:4
 * Gen.1.3, 2.7-9, 11; Exo.2.4
 * Gen.1.3
 * Gen.1.3, 9, 11; Exo.2.4
 * Thu Hilhkikna 28:39,59, 32:42
 * Thu Hilhkikna 28:39, 28:59, 32:42
 *
 * remove duplicate
 * Gen.1.3-4, 4; Gen.1.4
 * Gen.1.4, 3-4; Gen.1.4
 * @param {string} param - see example referenceFormat formatReference
 * @returns {TypeOfReference[]}
 */
export function formatReference(param) {
  const res = [];
  const seperator = { book: ";", chapter: ",", verse: "-" };

  let b = param.replace(/  +/g, " ").trim().split(seperator.book);
  for (let bk = 0; bk < b.length; bk++) {
    let book = "";
    let chapter = "";
    const c1 = b[bk].trim().split(seperator.chapter);
    for (let ck = 0; ck < c1.length; ck++) {
      const c = c1[ck].trim();
      let verse = "";
      let to = "";
      if (book) {
        const e =
          /(\s?(\d+?)(\s+)?[:.](\s+)?)?(\s?\d+)?(\s?(\d+?)?([\-–])?(\s?\d+)?)/.exec(
            c
          );

        if (e) {
          chapter = e[2] || chapter;
          verse = e[5];
          to = e[9];
        }
      } else {
        const e =
          /(\d?(\w+?)?(\s?)\w+(\s+?)?(\s?)\w+(\s+?|\.?))?((\d+)((\s+)?[:.]?(\s+)?)?)((\d+)([\-–])?(\d+)?)?/.exec(
            c
          );

        if (e && e[1]) {
          book = e[1].trim().replace(/\.$/, "");
          if (book) {
            chapter = e[8];
            verse = e[13];
            to = e[15];
          }
        }
      }
      if (chapter) {
        let ind = res.findIndex(
          (e) =>
            e.book == book &&
            e.chapter == chapter &&
            (e.verse == verse || e.to == verse || e.verse == to)
        );
        // NOTE: avoid duplicate
        if (ind == -1) {
          res.push({ book: book, chapter: chapter, verse: verse, to: to });
        }
      }
    }
  }
  return res;
}

/**
 * Load Bible
 * @param {string?} identify - tedim1932
 * @returns {Promise<TypeOfLoadedBible?>}
 */
export async function loadBible(identify) {
  if (!identify) {
    // return "no identify: " + identify;
    return null;
  }

  const currentBibleInfo = listOfBible.book.find((e) => e.identify == identify);

  if (!currentBibleInfo) {
    // return "not found identify: " + identify;
    return null;
  }

  let currentBible = listOfLoadedBible.find(
    (e) => e.bible.info.identify == identify
  );
  if (!currentBible) {
    const file = config.fileOfBible.replace("~", identify);
    /**
     * @type {TypeOfBible?}
     */
    // ts-ignore
    let tmp = await seek.readJSON(file);
    let cat = Object.assign({}, category);

    if (tmp && Object.keys(tmp).length) {
      // const abc = tmp.book["1"];
      for (let index = 0; index < cat.book.length; index++) {
        const e = cat.book[index];
        const i = tmp.book[e.id];

        e.info.abbr.push(i.info.name);
        e.info.abbr.push(i.info.shortname);
        e.info.abbr.push(...i.info.abbr);
      }

      currentBible = { bible: tmp, category: cat };
      listOfLoadedBible.push(currentBible);
    }
  }

  if (!currentBible) {
    // return "no book of identify: " + identify;
    return null;
  }

  return currentBible;
}

/**
 * Load Bible
 * @param {string} identify
 * @param {TypeOfReference[]} arg
 * @returns {Promise<TypeOfBibleBook?>}
 */
export async function getBibleByReference(identify, arg) {
  const currentBible = await loadBible(identify);
  /**
   * @type {TypeOfBibleBook}
   */
  const res = {};
  if (!currentBible) {
    return null;
  }

  for (let index = 0; index < arg.length; index++) {
    const q = arg[index];

    let book = category.book.find(
      (e) => e.info.name == q.book || e.info.abbr.includes(q.book)
    );

    if (book) {
      // console.log(book.info.name);
      const bookId = book.id;
      const chapterId = q.chapter;
      // let chapter = currentBible.book[bookId].chapter[q.chapter].verse[q.verse];
      let _itemBook = currentBible.bible.book[bookId];
      if (_itemBook) {
        let _itemChapter = _itemBook.chapter[chapterId];
        if (_itemChapter) {
          if (!res[bookId]) {
            res[bookId] = {};
            res[bookId].info = _itemBook.info;
            res[bookId].chapter = {};
          }
          if (q.verse) {
            if (!res[bookId].chapter[chapterId]) {
              res[bookId].chapter[chapterId] = {};
              // res[bookId].chapter[chapterId].verse = {};
            }

            let abc = getVerse(_itemChapter.verse, q.verse, q.to);
            if (abc) {
              res[bookId].chapter[chapterId].verse = abc;
            }
          } else {
            if (!res[bookId].chapter[chapterId]) {
              res[bookId].chapter[chapterId] = {};
            }
            // res[bookId].chapter[chapterId].verse = _itemChapter;
            let abc = getVerse(_itemChapter.verse);
            if (abc) {
              res[bookId].chapter[chapterId].verse = abc;
            }
          }
        }
      }
      // let chapter = currentBible.book[bookId].chapter[q.chapter];
      // console.log(book.info.name, q.chapter, q.verse, tmp.text);
    }
  }
  if (res) {
    return res;
  }
  return null;
}

/**
 * Support verse merge
 * @example
 * Gamlak Vakna 2:4-5 -> 4.2:3
 * @param {TypeOfVerse} verses - res
 * @param {string} [from] - from
 * @param {string} [to] - to
 * @returns {TypeOfVerse}
 */
export function getVerse(verses, from, to) {
  /**
   * @type {TypeOfVerse}
   */
  const res = {};

  if (!from) {
    return verses;
  } else {
    const _key = Object.keys(verses);

    let startAt = _key.filter((e) => parseInt(e) <= parseInt(from)).pop();

    if (startAt) {
      if (to) {
        let endAt = _key.filter((e) => parseInt(e) <= parseInt(to)).pop();
        console.log("endAt", endAt);
        if (endAt) {
          let from = parseInt(startAt);
          let to = parseInt(endAt);
          for (let vId = from; vId <= to; vId++) {
            res[vId] = verses[vId];
          }
        }
      } else {
        res[startAt] = verses[startAt];
      }
    }
  }
  return res;
}

/**
 * to get latest merge, config must be used
 */
export default config;
