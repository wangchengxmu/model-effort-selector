# Model and Effort Selector

A Codex skill for choosing a GPT model **and** reasoning effort for a task.
It provides a recommendation and escalation criteria, without changing models,
starting the underlying task, or making inference API calls.

Useful for scientific writing, literature extraction, coding, debugging,
architecture, and evidence-based analysis. MIT licensed; independently maintained
and not an official OpenAI product.

## What it does

- Separates model capability from reasoning effort.
- Reads relevant files when a project folder is identified; otherwise recommends directly from prompts, labeled prompt-only, without asking for a folder.
- Distinguishes routine reporting from difficult interpretation.
- Reserves xhigh for a specific difficult reasoning problem, not simply a long task.
- Recognizes missing evidence and failed tools as problems that more reasoning cannot fix.
- Preserves explicitly requested models and supported reasoning levels.
- Includes an offline, deterministic Python helper and automated tests.

## Install

Clone this repository into your Codex skills directory. If that destination already
exists, inspect it first rather than overwriting an existing installation.

### macOS or Linux

```sh
SKILL_ROOT="${CODEX_HOME:-$HOME/.codex}/skills"
mkdir -p "$SKILL_ROOT"
git clone https://github.com/wangchengxmu/model-effort-selector.git "$SKILL_ROOT/model-effort-selector"
```

### Windows PowerShell

```powershell
$codexHome = if ($env:CODEX_HOME) { $env:CODEX_HOME } else { Join-Path $HOME '.codex' }
$skillRoot = Join-Path $codexHome 'skills'
New-Item -ItemType Directory -Path $skillRoot -Force | Out-Null
git clone https://github.com/wangchengxmu/model-effort-selector.git (Join-Path $skillRoot 'model-effort-selector')
```

Invoke it in Codex:

> Use $model-effort-selector to inspect the relevant files in my project folder,
> then recommend a model and reasoning effort for writing my Results section while
> interpreting experimental data and checking calculations.

If it is not discovered yet, start a new task or ask Codex to read the installed
`SKILL.md` directly. Do not replace unrelated settings or other skills.

No folder identified? Just describe the task. The skill uses your prompts and
relevant conversation context, states its assumptions, and does not ask for a
folder or scan unrelated locations. This applies to real and hypothetical tasks.
An explicitly supplied invalid or inaccessible folder is reported as an evidence
limitation, not silently treated as an absent folder.

## Which model runs the selector?

It uses the model already selected for the current task. The skill itself is not
a model and cannot select its own runtime. A dedicated routing task can start
with Luna medium, but that suggestion has not been benchmarked as an optimal
router. Keep ambiguous scientific or architectural classification with a capable
primary agent. No additional model or paid service is required for the helper.

## Offline helper

### Project-aware assessment

For work in a real folder, inspect evidence before selecting the model:

```sh
python scripts/inspect_project.py /path/to/project --focus notes/result_summary.md
python scripts/select_model.py --project /path/to/project --focus notes/result_summary.md --workload scientific-writing --results
```

Use an existing project-relative file after `--focus`, or omit it for automatic
README, AGENTS, manifest, and project-note sampling. The first selector call returns
`needs_project_review`, not a final recommendation. The agent must read the files,
identify actual dependencies and uncertainty, and then supply the classification:

```sh
python scripts/select_model.py --project /path/to/project --focus notes/result_summary.md --project-reviewed --workload scientific-writing --complexity integrated --results --calculations
```

`--project-reviewed` is the caller's assertion of semantic review, not proof from
the script. Empty/unreadable evidence does not pass that gate. The skill requires
the final answer to name inspected evidence and explain how it affects the choice.
For PDF or image-dependent work, the agent must use a suitable parser/renderer;
the helper cannot interpret those formats.

Collection is bounded to 1,000 directory entries, 200 file records, three levels
below the root, eight text excerpts, and 16 KB of excerpt bytes. It skips hidden
and obvious credential paths, symlinks/junctions, and common dependency/weight
directories. Possible secret-bearing excerpts are withheld on a best-effort basis.
No project code is executed. Reports can contain private source text: keep them
local and review them before sharing. No automatic upload or telemetry exists.

### Prompt-only fallback

Requires Python 3.10+ and only the standard library. Run from this repository:

```sh
python scripts/select_model.py --workload extraction
python scripts/select_model.py --workload scientific-writing --complexity integrated --results --calculations
python scripts/select_model.py --workload debugging --complexity hard --reasoning-blocked
python scripts/select_model.py --help
```

When no folder is identified, the agent classifies the prompt into task flags and
omits `--project`. The helper returns a recommendation immediately, with
`evidence_basis: task_flags_only`; it does not inspect the current directory or
require project review. This is prompt-only guidance, not a claim that project
files were reviewed. Output is JSON with a candidate pair, reason, warnings, availability basis,
and `dispatch_performed: false`. No credentials are read and no network requests
are made by this helper. An optional agent using the skill may consult official
documentation when current product details are needed.

| Input | Starter recommendation |
| --- | --- |
| Routine text extraction | Luna low |
| Multi-step extraction | Luna medium |
| Ordinary multi-file coding | Terra medium |
| Settled scientific reporting from results | Astra medium |
| Coupled experimental interpretation and writing | Astra high |
| A specific unresolved reasoning problem after a checked high pass | Astra xhigh |

`--results` means claims depend on experimental evidence. `--calculations` adds
traceability guidance; it does not raise effort by itself. `--deep-reasoning`
means inherently difficult reasoning, not merely important work.
`--evidence-missing` prevents automatic xhigh escalation.

### Availability and overrides

The bundled catalog is an example **2026-09-06 Codex host snapshot**. It is not live
discovery, a guarantee of account access, or an API compatibility table. Some host
effort labels, such as `ultra`, may not be valid API parameters.

Pass model IDs observed in your runtime:

```sh
python scripts/select_model.py --workload coding --available gpt-5.6-luna,gpt-5.6-terra
python scripts/select_model.py --workload coding --model gpt-5.5 --effort medium
```

The helper accepts a subset of its known IDs, not arbitrary future models. Verify
the chosen effort against your current runtime too. If the preferred pair is
unavailable, the JSON status is `recommended_pair_unavailable`, with null model
and effort rather than a silent downgrade. Invalid arguments exit nonzero.
Update `CATALOG` and its tests when adopting new models or runtime capabilities.

## Validation and limitations

```sh
python -m unittest discover -s scripts -p "test_*.py" -v
```

Tests include 14 realistic routing cases and 13,824 parameter combinations, plus
project-content collection, review gates, credential/path exclusions, bounded reads,
availability, override, and CLI checks. These verify deterministic logic, **not
model quality, financial savings, or superiority over another configuration**.
Agent or human interpretation still matters: the helper collects project content
but does not semantically classify raw prose or understand scientific evidence itself.

The economy and balanced policies share conservative baseline routing; neither
is a pricing optimizer. Quality preference can raise a tier; speed preference
selects Spark only for a small, known coding fix. There are no live prices or
subscription quota estimates. A high-effort smaller model is not assumed to be
equivalent to a lower-effort larger model.

General model-role grounding: [OpenAI model catalog](https://developers.openai.com/api/docs/models).
Supported Astra API efforts: [Astra documentation](https://developers.openai.com/api/docs/models/gpt-6-astra).
Check current documentation before deployment; the workload mappings here are
independent heuristics, not OpenAI's official routing policy.

## Contributing

Include a realistic task description, expected routing behavior and rationale,
and a regression test with proposed changes. Do not submit credentials, unpublished
research data, or private project paths. Keep selector recommendations separate
from model execution and from claims of measured performance.

## License

[MIT](LICENSE). Copyright (c) 2026 wangchengxmu.
