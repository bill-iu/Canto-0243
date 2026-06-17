import assert from "node:assert/strict";
import { describe, it } from "node:test";

import { isRelationSyntaxQuery, normalizeQuerySyntax } from "../frontend/relation-syntax.mjs";

describe("relation-syntax", () => {
  it("detects compound and lookup shapes", () => {
    for (const q of ["!!", "~~", "~開心", "!你", "!與!", "33!!你", "349~與~你"]) {
      assert.equal(isRelationSyntaxQuery(q), true, q);
    }
  });

  it("rejects 0243 search queries", () => {
    for (const q of ["開心", "香??", "23", "香港="]) {
      assert.equal(isRelationSyntaxQuery(q), false, q);
    }
  });

  it("normalizes fullwidth relation punctuation", () => {
    assert.equal(normalizeQuerySyntax("～開心"), "~開心");
    assert.equal(normalizeQuerySyntax("！！"), "!!");
  });
});
