/**
 * Bible
 * @param {any} req
 * @example
 * node run bible
 * node run bible test
 * node run bible search
 * node run bible abbr
 */
export default async function main(req) {
  switch (req.params.task) {
    case "test":
      return (await import("./test.js")).default(req);
    case "search":
      return (await import("./search.js")).default(req);
    case "info":
      return (await import("./info.js")).default(req);
    // case "lang":
    //   return await doLang(req.params.name).then((e) => e(req));
    case "abbr":
      return (await import("./abbr.js")).default(req);
    default:
      return noTask(req);
  }
}

// /**
//  * @param {string} [name]
//  */
// async function doLang(name) {
//   switch (name) {
//     case "generator":
//       return (await import("./lang.js")).doGenerator;
//     default:
//       return (await import("./lang.js")).default;
//   }
// }

/**
 * @param {any} req
 */
function noTask(req) {
  if (req.params.task) {
    return `Wow has no such task '${req.params.task}' name!`;
  }
  return `Provide a task name for Wow!`;
}

/**
 * @param {any} req
 */
function noName(req) {
  return `What to ${req.params.task} from ${req.params.name} of Wow?`;
}
