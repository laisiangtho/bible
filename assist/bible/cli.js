/**
 * Bible
 * @param {any} req
 * @example
 * note run bible
 * note run bible test
 * note run bible search
 */
export default async function main(req) {
  switch (req.params.task) {
    case "test":
      return (await import("./test.js")).default(req);
    case "search":
      return (await import("./search.js")).default(req);
    case "info":
      return (await import("./info.js")).default(req);
    default:
      return noTask(req);
  }
}

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
