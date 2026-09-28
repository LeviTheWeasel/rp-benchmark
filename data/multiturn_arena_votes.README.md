# data/multiturn_arena_votes.jsonl

Human votes from the round-2 multi-turn arena (full 12-turn dialogues, 20
models, 20 adversarial seeds). Written by `refresh_multiturn_arena_votes.py`;
scored by `analyze_multiturn_arena.py`.

## Source

- Site export: `GET https://plotlightstudios.com/api/plotpoints/raw?round=2&mode=multiturn_arena`
  (round 2, mode `multiturn_arena`; checked against the round archive,
  https://plotlightstudios.com/plotpoints/round/2: 1,943 votes, 482 voters, 190 pairs, closed 2026-06-13).
- Fetched: 2026-09-27T10:48:15+00:00 to 2026-09-27T10:49:40+00:00
- CSV: 503,826 bytes, sha256 `d1a1b33ea070840d41c8a62522b32169e73b0dfb3d5d4f3a2a588f21c957d53c`, 1,943 rows, created_at
  2026-04-19T01:36:28.347+00:00 to 2026-06-13T15:24:01.61933+00:00.
- Plus 30 older rows kept from the previous file, source
  `arena_l3vi4th4n_only`: ballots cast on `arena.l3vi4th4n.ai` (the round-1/2 arena's
  original domain, which the project no longer controls) after its 507
  round-2 votes were imported into the site on 2026-04-30. They never reached
  the site's round-2 tally, so `analyze_multiturn_arena.py` keeps them unscored.

Rows by source: arena_l3vi4th4n_only 30, arena_l3vi4th4n_round_02 507, native 1436. Total 1,973 rows, sorted by server timestamp.

## Fields

`timestamp` is the client timestamp and `server_timestamp` the site's
`created_at`, both as the CSV gives them. `signed_in` is the CSV's boolean;
the export leaves out voter cookie ids, IP hashes, user agents and user ids.

Voter ids: omitted on every row (PLOTPOINTS_VOTER_HMAC_SECRET was not set, and the public CSV carries none). A raw voter id is a long-lived bearer cookie and is never
stored here, so the voter count (the archive's 482) cannot be recomputed from
this file, and the voter-clustered bootstrap
(`analyze_multiturn_arena_bootstrap.py`) cannot run on it.

Before this refresh the file held a 1,262-vote pull from 2026-06-04 (1,232 of
those votes are in the CSV unchanged, plus the 30 kept above).
