import { command } from "lethil";

const app = command();
const routes = app.routes();

routes.register("", () => "?");
routes.register("apple", () => "Did you know apple is fruit?");
routes.register("orange", () => "Orange is good for health");
routes.register("req", (req) => req);

routes.register("task/:task?/:name?", async function (req) {
  return import("./task/cli.js").then((e) => e.default(req));
});

routes.register("bible/:task?/:name?", async function (req) {
  return import("./bible/cli.js").then((e) => e.default(req));
});
