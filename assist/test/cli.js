/**
 * Test
 * @param {any} req
 * @example
 * node run test
 * node run test config
 * node run test config io

 */
export default async function main(req) {
  switch (req.params.task) {
    case "config":
      return await doConfig(req.params.name).then((e) => e(req));
    case "wbc":
      return await doWBC(req.params.name).then((e) => e(req));
    case "request":
      return await doRequest(req.params.name).then((e) => e(req));
    case "export":
      return await doExport(req.params.name).then((e) => e(req));
    default:
      return noTask(req);
  }
}

/**
 * @param {string} [name]
 */
async function doRequest(name) {
  switch (name) {
    case "definitions":
      return (await import("./scan.js")).doRequest;
    default:
      return noName;
  }
}

/**
 * @param {string} [name]
 */
async function doWBC(name) {
  switch (name) {
    case "check":
      return (await import("./wbc.js")).doCheck;
    case "io":
      return (await import("./wbc.js")).doIO;
    case "request":
      return (await import("./wbc.js")).doRequest;
    case "read":
      return (await import("./wbc.js")).doRead;
    case "scan":
      return (await import("./wbc.js")).doScan;
    case "scanall":
      return (await import("./wbc.js")).doScanAll;
    case "new":
      return (await import("./wbc.js")).doNew;
    default:
      return (await import("./wbc.js")).doDefault;
  }
}

/**
 * @param {string} [name]
 */
async function doConfig(name) {
  switch (name) {
    case "io":
      return (await import("./test.js")).doTestIO;
    case "bookname":
      return (await import("./test.js")).doTestBookname;
    default:
      return (await import("./test.js")).doTestDefault;
  }
}

/**
 * @param {string} [name]
 */
async function doExport(name) {
  switch (name) {
    case "words":
      return (await import("./scan.js")).doExport;
    default:
      return noName;
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