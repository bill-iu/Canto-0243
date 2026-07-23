import { createSqlJsBackend } from '../src/db/sqljs-backend.ts';
import { initSqlJs } from '../src/db/sqljs.ts';
import {
  LexiconLengthInvariantError,
  assertLexiconLengthInvariant,
} from '../src/db/lexicon-length-invariant.ts';

const SQL = await initSqlJs();
const native = new SQL.Database();
native.run('CREATE TABLE words (id INTEGER PRIMARY KEY, char TEXT, length INTEGER)');
native.run("INSERT INTO words(char, length) VALUES ('香', 1), ('香港', 1)");
const db = createSqlJsBackend(native);

let rejected = false;
try {
  await assertLexiconLengthInvariant(db);
} catch (error) {
  rejected = error instanceof LexiconLengthInvariantError;
}
if (!rejected) throw new Error('invalid words.length was accepted');

native.run('UPDATE words SET length = length(char)');
await assertLexiconLengthInvariant(db);
await db.close();
console.log('lexicon length invariant self-check ok');
