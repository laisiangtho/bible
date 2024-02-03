/**
 * Test
 * @param {any} req
 * @example
 * node run task
 * node run task wbc scan
 * node run task lang generate
 * node run task see
 * node run task see khualtawng

 */
export default async function main(req) {
  switch (req.params.task) {
    case "see":
      return await doSee(req.params.name).then((e) => e(req));
    case "wbc":
      return await doWBC(req.params.name).then((e) => e(req));
    case "lang":
      return await doLang(req.params.name).then((e) => e(req));
    case "test":
      return await doTest(req.params.name).then((e) => e(req));
    case "export":
      return await doExport(req.params.name).then((e) => e(req));
    default:
      return noTask(req);
  }
}

/**
 * @param {string} [name]
 */
async function doLang(name) {
  switch (name) {
    case "generate":
      return (await import("./lang.js")).doGenerate;
    default:
      return (await import("./lang.js")).default;
  }
}

/**
 * @param {string} [name]
 */
async function doTest(name) {
  const test = await import("./test.js");
  switch (name) {
    case "config":
      return test.doConfig;
    default:
      return test.default;
  }
}

/**
 * @example
 * node run task wbc
 * node run task wbc check
 * node run task wbc request
 * node run task wbc read
 * node run task wbc scan
 * node run task wbc scanAll
 * node run task wbc new
 * node run task wbc content
 * node run task wbc context
 * @param {string} [name]
 */
async function doWBC(name) {
  switch (name) {
    case "check":
      return (await import("./wbc.js")).doCheck;
    case "request":
      return (await import("./wbc.js")).doRequest;
    case "read":
      return (await import("./wbc.js")).doRead;
    case "scan":
      return (await import("./wbc.js")).doScan;
    case "scanAll":
      return (await import("./wbc.js")).doScanAll;
    case "skip":
      return (await import("./wbc.js")).doSkip;
    case "new":
      return (await import("./wbc.js")).doNew;
    case "content":
      return (await import("./wbc.js")).doMapContent;
    case "context":
      return (await import("./wbc.js")).doMapContext;
    case "language":
      return (await import("./wbc.js")).doMapLanguage;
    default:
      return (await import("./wbc.js")).doDefault;
  }
}

/**
 * @param {string} [name]
 */
async function doSee(name) {
  switch (name) {
    case "io":
      return (await import("./see.js")).doIO;
    case "khualtawng":
      return (await import("./see.js")).doKhualTawng;
    default:
      return (await import("./see.js")).doDefault;
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
