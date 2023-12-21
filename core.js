import core from "lethil";

core.config.root(process.cwd());
// core.config.root("./test?");
// core.config.hostname("localhost");
// core.config.port(8082);

core.environment();

// core.config.mysql("mysql2");
// core.config.mongo(mongodb);
// core.config.merge(abc);

export default core;
