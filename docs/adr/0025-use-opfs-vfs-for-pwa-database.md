# ADR-0025: Use OPFS VFS for PWA database queries

## Status

Accepted - 2026-07-06

## Context

The PWA previously had a `VITE_DB_BACKEND=opfs` path, but that path only used OPFS
as a local byte cache. Query execution still read the entire SQLite database back
into a `Uint8Array` and opened it with sql.js, which put the full database in the
sql.js heap.

That shape reduced repeat network fetches, but it did not address private-browser
memory pressure or the risk of repeated large downloads during failed OPFS probes.

## Decision

`VITE_DB_BACKEND=opfs` now means a real OPFS-backed SQLite VFS backend. It is also
accepted as `VITE_DB_BACKEND=opfs-vfs` for explicitness.

The PWA keeps `sqljs` as the default and fallback backend until real-device DB-5
measurements prove the OPFS VFS path is stable enough to flip by default.

The OPFS VFS backend:

- runs wa-sqlite in a dedicated Worker;
- streams the versioned `lyrics.{version}.db` response directly into OPFS;
- opens the OPFS file through `OPFSCoopSyncVFS`;
- exposes the same async `DatabaseBackend` query surface used by sql.js.

## Consequences

All browser query execution now targets an async database backend contract. The
sql.js adapter remains sync internally, but its app-facing API is async so query
logic can run unchanged against OPFS VFS.

The OPFS path no longer imports the whole database into the sql.js heap. First
install still downloads the database once, but the response is streamed to OPFS
instead of materialising one full DB byte array for sql.js.

The fallback matters: private browsing modes and older browsers may expose OPFS
capability differently, so production should not require OPFS VFS until DB-5
device measurements pass.
