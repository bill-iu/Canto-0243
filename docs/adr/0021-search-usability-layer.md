# Search usability layer (查詢語意解釋)

Creators face powerful but position-sensitive anchor syntax (`+`, `=`). Phase 1 adds a **search usability layer**: server-authoritative **查詢語意解釋** driven by existing `normalize_and_parse`, rendered below the search field (debounced live input). Creator copy uses **第 N 個字** and **任意字**, not 格／槽. Parser behavior is unchanged (100% backward compatible). One positional confusion warning ships in MVP (`23o` vs `23+o`). Visual anchor builder (phase B) is deferred; it will reuse the same explain endpoint for previews.

**Considered:** client-side parse duplicate—rejected (drift from **查詢分派**). Natural-language intent input—deferred.