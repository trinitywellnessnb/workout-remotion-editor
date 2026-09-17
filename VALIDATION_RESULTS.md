# Validation results — Workout Remotion Editor v2.3

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
