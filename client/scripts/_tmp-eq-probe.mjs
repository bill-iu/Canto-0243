import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { createRequire } from "node:module";

// Use dynamic import of compiled paths via tsx if available - instead use python for parity check only
// Direct SQL probe for suffix alignment
import initSqlJs from "sql.js";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)));
const dbPath = path.join(root, "lyrics.db");
const SQL = await initSqlJs();
const db = new SQL.Database(fs.readFileSync(dbPath));
const lit = "困潦倒";
const r1 = db.exec(`SELECT char, jyutping, finals FROM words WHERE char = '${lit}' LIMIT 3`);
console.log("exact", JSON.stringify(r1));
const r2 = db.exec(`SELECT char, jyutping, finals FROM words WHERE char LIKE '%${lit}' LIMIT 5`);
console.log("suffix count rows", r2[0]?.values?.length, r2[0]?.values?.slice(0,2));
const r3 = db.exec(`SELECT COUNT(*) FROM words WHERE length=4 OR ((length IS NULL OR length=0) AND length(char)=4)`);
console.log("len4", r3[0]?.values);
db.close();
