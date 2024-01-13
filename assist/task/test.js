import { Prompt } from "lethil";

import * as base from "./base.js";
const env = base.env;
const config = env.config;
// const listOfBible = env.listOfBible;
// const category = env.category;
// const structure = env.structure;

/**
 * Get definitions, see `cli` for more info
 * @param {any} req - {query:{identify?:string, timeout?:number}}
 */
export default async function doDefault(req) {
  const prompt = Prompt();
  let testamentQuestion = "Testament [*,1,2]: ";
  let testament = await prompt.question(testamentQuestion);
  // let bookQuestion = "Book [1-66] msg *: ";
  let bookQuestion = "msg *: ";

  if (testament == "1") {
    //
    bookQuestion = bookQuestion
      .replace(
        "msg",
        "Book in 'Old Testament' between [1-39] seperated by comma"
      )
      .replace("*", "eg. 2,4, or empty for all books");
  } else if (testament == "2") {
    // Book in 'Old Testament' between [40-66] seperated by comma or empty for all books
    bookQuestion = bookQuestion
      .replace(
        "msg",
        "Book in 'New Testament' between [40-66] seperated by comma"
      )
      .replace("*", "eg. 41,44, or empty for all books");
  } else {
    // NOTE: No Testament properly select
    testament = "";
    bookQuestion = bookQuestion
      .replace(
        "msg",
        "Old & New Testament selected, provide book between [1-66] seperated by comma"
      )
      .replace("*", "eg. 2,4 or all");
  }

  const book = await prompt.question(bookQuestion);
  // prompt.close();
  prompt.task.close();

  let msg = `Testament ${testament}, book: ${book}`;
  return msg;
}

/**
 * Test config
 * @param {any} req
 */
export async function doConfig(req) {
  return "config";
}
