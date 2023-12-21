import core from "./core.js";
import "./assist/command.js";
import { config } from "./assist/index.js";

/**
 * Please mind the reserved keywords (sql,mongo,Config,args,etc) in module.exports
 * @example
 * node run [?]
 * process.argv.splice(2),__dirname
 */
const app = core.command();
// app.environment();

/**
 * const usage = app.memoryUsage();
 * for (var name in usage) console.log(usage, app.byteToMB(usage[name]), "mb");
 */
app.listen(function(msg) {
	if (msg) {
		console.log("...", msg);
	}
});

app.close(function(error) {
	if (error) {
		console.log("...", error);
	}
	core.db.mysql.close();
});
