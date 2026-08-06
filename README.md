# identity-extraction

Single source of truth for pulling person names and ID/passport numbers out
of `extracted_data` dicts produced by an OCR/extraction pipeline (Emirates
ID, passport, and similar identity documents). Shared across `ocr-pipeline`
and `identity-verification`, which both consume the same document shapes,
so a fix to how a field is located (nested front/back merges, MRZ line
parsing, role-prefixed party fields) happens once and takes effect in both.

This is the extraction half of a two-package split — see
[matching-utils](https://github.com/Softspaceg/matching-utils) for the
other half: given already-extracted values, deciding whether they match.
Extraction and matching are separate concerns on purpose: extraction is tied
to a specific document schema (which can validly differ between consumers
in the future), while the matching decision is meant to always change in
lockstep.

## Modules

- `identity_extraction.name_extraction` — `find_name_pairs` (recursive,
  role-prefixed, bare/canonical key styles), `extract_name`,
  `extract_all_names`.
- `identity_extraction.id_extraction` — `extract_id_number` (Emirates ID,
  with MRZ fallback), `extract_passport_number` (including the merged
  passport + passport_continue shape).

Depends on [matching-utils](https://github.com/Softspaceg/matching-utils)
for value normalization (`normalize_name`, `normalize_id_number`) — extracted
values are returned already normalized, ready to hand to matching-utils's
comparison functions.

## Using this from another project

Not published to PyPI — install straight from this repo, pinned to a tag:

```
# requirements.txt
git+https://github.com/Softspaceg/identity-extraction.git@v0.1.0
```

```toml
# pyproject.toml
dependencies = [
    "identity-extraction @ git+https://github.com/Softspaceg/identity-extraction.git@v0.1.0",
]
```

```python
from identity_extraction.name_extraction import extract_name
from identity_extraction.id_extraction import extract_id_number

from matching_utils.name_matching import names_match

name_a = extract_name(doc_a.extracted_data)
name_b = extract_name(doc_b.extracted_data)
is_same_person = name_a and name_b and names_match(name_a, name_b, threshold=0.85)
```

Docker images need `git` installed in the build stage for pip to clone this
(the repo is public, so no credentials are needed either locally or in CI).

## Releasing a new version

1. Bump `version` in `pyproject.toml` (and `src/identity_extraction/__init__.py`).
2. Commit, then tag: `git tag -a vX.Y.Z -m "..."` and `git push origin main --tags`.
3. Bump the `@vX.Y.Z` pin in every consuming project's `requirements.txt` /
   `pyproject.toml` and reinstall.

## Development

```bash
pip install -e ".[dev]"
pytest
```
