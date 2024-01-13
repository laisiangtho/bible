import { Prompt } from "lethil";
import * as base from "./base.js";

const env = base.env;
const config = env.config;
const listOfBible = env.listOfBible;
const category = env.category;
const structure = env.structure;

/**
 * late 10:40
 * pian 1:20
 * @example
 * node run bible search tedim1932
 * node run bible search tedim1932 --q Topa kiangah
 * node run bible search niv2011 --q abraham
 * @param {any} req - {query:{identify?:string, timeout?:number}}
 */
export default async function doDefault(req) {
  const identify = req.params.name;
  const keyword = req.query.q;
  const que = await doQuestion();
  const res = await env.getBibleByKeyword(identify, keyword, que);
  let resultFile = "./tmp/result-search.json";
  await base.writeJSON(resultFile, res, 2);
  return "search: " + identify + ", result: " + resultFile;

  // console.log(res);
  // return "abc";
}

/**
 * Prompt for question to select book
 * @returns {Promise<base.env.TypeOfSearchParameter>}
 */
async function doQuestion() {
  const prompt = Prompt();
  // Select testament between [1-2], or empty for both testaments:
  let testamentQuestion =
    "> Select testament between [1-2], or empty for both testaments: ";
  let testament = await prompt.question(testamentQuestion);
  // let bookQuestion = "Book [1-66] msg *: ";
  let bookQuestion = "> msg *: ";
  const res = {};

  if (testament == "1") {
    res.testament = 1;
    bookQuestion = bookQuestion
      .replace(
        "msg",
        "Select book in 'Old Testament' between [1-39] seperated by comma"
      )
      .replace("*", "eg. 2,4, or empty for all books in Old Testament");
  } else if (testament == "2") {
    res.testament = 2;
    bookQuestion = bookQuestion
      .replace(
        "msg",
        "Select book in 'New Testament' between [40-66] seperated by comma"
      )
      .replace("*", "eg. 41,44, or empty for all books in New Testament");
  } else {
    // NOTE: No Testament properly select
    bookQuestion = bookQuestion
      .replace("msg", "Select book between [1-66] seperated by comma")
      .replace("*", "eg. 2,4 or empty for all books in Old & New Testament");
  }

  const book = await prompt.question(bookQuestion);
  // prompt.close();
  prompt.task.close();

  const selectedbook = book
    .split(",")
    .map((e) => e.trim())
    // .filter((v) => typeof v === "number")
    .filter((v) => Number.isNaN(v) == false)
    .filter(function (item, pos) {
      return book.indexOf(item) == pos;
    })
    .map((e) => parseInt(e));
  if (testament == "1") {
    res.book = selectedbook.filter((v) => v >= 1 && v <= 39);
    if (!res.book.length) {
      res.book = Array.from({ length: 39 }, (v, k) => k + 1);
    }
  } else if (testament == "2") {
    res.book = selectedbook.filter((v) => v >= 40 && v <= 66);
    if (!res.book.length) {
      res.book = Array.from({ length: 27 }, (v, k) => k + 40);
    }
  } else {
    res.book = selectedbook.filter((v) => v >= 1 && v <= 66);
    if (!res.book.length) {
      res.book = Array.from({ length: 66 }, (v, k) => k + 1);
    }
  }

  // res.book = [...new Set(res.book)];
  return res;
}
