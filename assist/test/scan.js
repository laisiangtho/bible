// import * as base from "./base.js";

/**
 * Get definitions, see `cli` for more info
 * @param {any} req - {query:{identify?:string, timeout?:number}}
 */
export async function doRequest(req) {
	return "request";
}

/**
 * Get definitions
 * Manually Trigger
 * @param {any} req - {query:{identify?:string, timeout?:number}}
 */
export async function doExport(req) {
	return "export";
}
