# Phase 7 Package 82 — First Symbol-Currency Result

## Classification and Baseline

Classification: `OPERATIONAL`.

Fresh `develop` clone verified exactly at:

```text
f9f5ebdc4ac9813abd19f706eca92f4a9c9f607b
```

Only the redacted report was reviewed. The private success projection and
currency checkpoint were not read or copied into the repository.

## Measured Result

The controlled `--max-items 1` run completed normally with `IN_PROGRESS`:

```text
member_count         = 12,020
attempted_count      = 1
success_count        = 0
final_failure_count  = 1
retry_pending_count  = 0
never_attempted_count = 12,019
failure_category     = INVALID_CURRENCY
halt_category        = null
```

The projection checksum exactly matches the successful Package 79 projection:

```text
d0709f8e83a9f0820327001162fe371129c9c01203112f28e11da0c9ce1f28ea
```

The redacted report SHA-256 is:

```text
8196a29f0bd5556e723e46528e81713af3a7b13ee8fd480d8992afca29d3bbc1
```

## Interpretation

The provider lookup returned at least one exact-symbol row but none supplied a
valid three-letter currency. This is a valid terminal result under the current
fail-closed contract. It does not establish whether the field was absent,
empty, malformed, or located behind a different Yahoo metadata surface.

Do not infer USD and do not expand the scan from this evidence.

## Next Step

Audit and implement one privacy-safe diagnostic for the first private
`INVALID_CURRENCY` outcome. It should repeat only that symbol lookup and report
aggregate exact-match and currency-field shape categories without revealing
the symbol, currency value, provider text, or paths. Broad currency scanning,
batch generation, and ingestion remain blocked.
