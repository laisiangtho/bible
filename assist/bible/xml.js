import xml2js from "xml2js";
import { seek } from "lethil";
import * as base from "./base.js";

const env = base.env;
// const config = env.config;
// const listOfBible = env.listOfBible;
// const category = env.category;
// const structure = env.structure;

/**
 * @example
 * node run bible xml tedim1932
 * node run bible xml niv2011
 * @param {any} req
 */
export default async function doDefault(req) {
  const identify = req.params.name;
  if (!identify) {
    return "No identify provided";
  }
  const currentBible = await env.loadBible(identify);
  if (!currentBible) {
    return "No # found".replace("#", identify);
  }

  // let testing = currentBible.bible.book;

  let infoBible = infoObject(currentBible.bible.info);
  let digitBible = digitObject(currentBible.bible.digit);
  let noteBible = noteObject(currentBible.bible.note);
  let languageBible = languageObject(currentBible.bible.language);
  let testamentBible = testamentObject(currentBible.bible.testament);
  let bookBible = bookObject(currentBible.bible.book);

  const res = {
    bible: {
      info: infoBible,
      digit: digitBible,
      note: noteBible,
      language: languageBible,
      testament: testamentBible,
      book: bookBible,
    },
  };
  const builder = new xml2js.Builder();
  const xml = builder.buildObject(res);

  const resultFile = "./tmp/xml-?.xml".replace("?", identify);

  await seek.write(resultFile, xml);

  return "xml generated at: " + resultFile;
}

/**
 * get XML Object from Info
 * @param {base.env.TypeOfInfo} info
 */
function infoObject(info) {
  const res = [];
  for (const [key, value] of Object.entries(info)) {
    if (typeof value == "object") {
      res.push({
        $: {
          id: key,
          textdirection: value.textdirection,
          name: value.name,
        },
        _: value.text,
      });
    } else {
      if (value) {
        res.push({ $: { id: key }, _: value });
      }
    }
  }
  return res;
}

/**
 * get XML Object from digit
 * @param {base.env.TypeOfDigit} digit
 */
function digitObject(digit) {
  const res = [];
  for (const [key, value] of Object.entries(digit)) {
    res.push({ $: { id: key }, _: value });
  }
  return res;
}

/**
 * get XML Object from note
 * @param {base.env.TypeOfNote} note
 */
function noteObject(note) {
  const res = [];
  for (const [key, value] of Object.entries(note)) {
    res.push({ $: { id: key }, _: value });
  }
  return res;
}

/**
 * get XML Object from language
 * @param {base.env.TypeOfBibleLocale} language
 */
function languageObject(language) {
  const res = [];
  for (const [key, value] of Object.entries(language)) {
    res.push({ $: { id: key }, _: value });
  }
  return res;
}

/**
 * get XML Object from testament
 * @param {base.env.TypeOfTestament} testament
 */
function testamentObject(testament) {
  const res = [];
  for (const [key, value] of Object.entries(testament)) {
    res.push({
      $: { id: key, name: value.info.name, shortname: value.info.shortname },
      _: value.info.desc || "",
    });
  }
  return res;
}
/**
 * get XML Object from book
 * @param {base.env.TypeOfBibleBook} book
 */
function bookObject(book) {
  const res = [];

  for (const [key, value] of Object.entries(book)) {
    res.push({
      $: {
        id: key,
        name: value.info.name,
        shortname: value.info.shortname,
        abbr: value.info.abbr.join(","),
      },
      description: value.info.desc,
      chapter: chapterObject(value.chapter),
    });
  }
  return res;
}

/**
 * @param {Object<number,{verse:base.env.TypeOfVerse}>} chapters
 */
function chapterObject(chapters) {
  const res = [];
  for (const [chapterId, value] of Object.entries(chapters)) {
    res.push({
      $: {
        id: chapterId,
      },
      verse: verseObject(value.verse),
    });
  }
  return res;
}

/**
 * @param {Object<number,{verse:base.env.TypeOfVerse}>} verse
 */
function verseObject(verse) {
  const res = [];
  for (const [verseId, value] of Object.entries(verse)) {
    const attr = {};
    attr.id = verseId;
    if (value.title) {
      attr.title = value.title;
    }
    if (value.ref) {
      attr.ref = value.ref;
    }
    if (value.merge) {
      attr.merge = value.merge;
    }
    res.push({
      $: attr,
      _: value.text,
    });
  }
  return res;
}
