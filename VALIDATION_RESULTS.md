# Validation results — Phase 1 media evidence

Verified on 2026-10-02 through GitHub Actions. This editing session exposes GitHub tools without a local shell, so execution evidence comes from the repository's runners.

Implementation tested at commit 7b1f6f5265037532748d5f180935bcb63f9b049d:
- [Core schema/validator/lint/package run](https://github.com/trinitywellnessnb/workout-remotion-editor/actions/runs/37007139576)
- [Optional real-tool integration run](https://github.com/trinitywellnessnb/workout-remotion-editor/actions/runs/37007139596)

| Result | Verification | Evidence |
| --- | --- | --- |
| PASS | Core semantic/provider/workflow tests | 31 unittest tests, including all representative fixtures, both validation paths, provider failures, and actual CLI operation with no site packages or executables. |
| PASS | JSON Schema | Draft202012Validator.check_schema; legacy 2.3 and new 2.4 fixtures, source bounds, confidence, ordering, legal overlaps, and provenance references. |
| PASS | Real optional tools | Four integration tests with ffmpeg/ffprobe, PySceneDetect 0.7.1, PyAV 18.0.0, and Auto-Editor 31.6.0. |
| PASS | Signal semantics | Content/adaptive/threshold boundaries, motion and audio regions, candidate support, VFR source timing, and unchanged source bytes. |
| PASS | Fallback | Missing dependencies, unsupported media, timeout, decoder errors, partial audio failures, and invalid provider output. |
| PASS | Lint/compilation | Ruff and compileall for scripts; no Node/Remotion app build or existing static typecheck target exists in this repository. |
| PASS | Packaging | Skill metadata, ZIP integrity, analyzer modules, one schema, LICENSE, and THIRD_PARTY_NOTICES.md included; tests and external packages excluded. |
| PASS | Diff review | Committed-diff whitespace check and separate implementation review. |

Review corrections include per-audio-stream ordering, unknown timestamp-origin handling, final scene endpoint bounds, explicit decoding backend provenance, and a compatible PyAV pin. OpenCV may report invalid terminal timing for VFR media; validation rejects that evidence and preserves the manual workflow. PyAV is the recommended/default optional backend.

All integrations remain evidence only. No exercise identity, set or rep count, footage deletion, timeline selection, or later-phase model integration is introduced.

## Archived v2.3 validation

Validated on 2026-09-17 in the supplied repository environment.

| Result | Command | Notes |
| --- | --- | --- |
| PASS | `python -m json.tool workout-remotion-editor/scripts/analysis-schema.json >/dev/null` | Schema is valid JSON. |
| PASS | `python -m py_compile workout-remotion-editor/scripts/validate_analysis.py` | Validator compiles. |
| PASS | `python workout-remotion-editor/scripts/validate_analysis.py /tmp/v23-valid.json` | Valid v2.3 fixture, including a retention plan, accepted. |
| PASS | `python workout-remotion-editor/scripts/validate_analysis.py /tmp/v23-invalid.json` | Invalid payoff beat reference rejected as expected. |
| PASS | `(cd /tmp/v23-skill && zip -qr /tmp/skill.zip . -x '**/__pycache__/*' '*.pyc') && unzip -t /tmp/skill.zip` | Package archive integrity passed. |
| PASS | `python` dependency-free frontmatter and required-file assertion script | Name, frontmatter keys, and required v2.3 references passed. |
| PASS | `git diff --check` | No whitespace errors. |
| WARNING | `python -m pip install --disable-pip-version-check -q PyYAML jsonschema` | Network proxy returned HTTP 403, so PyYAML could not be added to the local environment. `jsonschema` was already available; CI installs both dependencies. |
