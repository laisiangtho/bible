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
 * @typedef {Object} TypeOfVerse - ?
 * @property {string} text - Context eg.[In the beginning...]
 * @property {string} [title] - Title eg.[The Creation of the World...]
 * @property {string} [heading] - Heading eg.[The Creation of the World...]
 * @property {string} [ref] - Reference eg.[Gen.9.1,Gen.1.28..]
 * @property {string} [merge] - is Merge eg.[2]
 *
 * @typedef {Object<number,TypeOfVerse>} _BookChapterVerseBlock - ?
 *
 * @typedef {Object<number,{info:InfoOfBook, topic: _BookTopic, chapter:Object<number,{verse:_BookChapterVerseBlock}>}>} TypeOfBibleBook - Bible book
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
 * @property {number} b - bookId
 * @property {number} s - sectionId
 * @property {number} c - total chapter
 * @property {number[]} v - list of each total verses
 *
 * @typedef {Object} TypeOfCategory
 * @property {Object} name - a set of name eg.[section, testament, book, digit]
 * @property {Object<number,string>} name.section - eg[Law,History ..]
 * @property {TypeOfTestament} name.testament
 * @property {Object<number,{info:InfoOfBook}>} name.book
 * @property {TypeOfDigit} name.digit
 * @property {Object<number,Object<number,number[]>>} section
 * @property {Object<string,BookOfCategory>} book
 */

/**
 * @typedef {Object} TypeOfBook
 * @property {string} name - app name
 * @property {Date} updated - last modified
 * @property {number} version
 * @property {TypeOfInfo[]} book - book info
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
 * Merge core.config & local
 */
export const config = core.config.merge({
  fileOfBook: fileOfBook,
  fileOfCategory: fileOfCategory,
  fileOfStructure: fileOfStructure,
});

/**
 * to get latest merge, config must be used
 */
export default config;
