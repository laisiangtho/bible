// import { config } from "lethil";
import * as base from "./base.js";

const env = base.env;
// const config = env.config;
// const listOfBible = env.listOfBible;
const category = env.category;
// const structure = env.structure;

/**
 * Testing
 * @param {any} req
 */
export async function doTestDefault(req) {
  // return base.settings;
  // console.log(req);
  // return JSON.stringify(base.settings);

  // if (config.hasOwnProperty("uuv")) {
  //   return config["uuv"];
  // }
  // if (base.env.config.hasOwnProperty("uuv")) {
  //   return base.env.config["uuv"];
  // }
  // config.uuv

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
  // await base.writeJSON("./tmp/delete.json", { 1: "Ok" });
  // let category = await base.readJSON("./category.json", {});

  const books = category.name.book;

  for (const [key, value] of Object.entries(books)) {
    // console.log(`${key}: ${value}`);
    console.log(value.info.abbr[0]);
  }

  return "?";
}
