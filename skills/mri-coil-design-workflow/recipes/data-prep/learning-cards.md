# Data-prep Few-shot Learning Cards

Use this recipe after the canonical RD/FD matrices have complete, validated
records. It compiles simulation records into deterministic retrieval-time
few-shot cards. It does not fine-tune an LLM and does not run CST.

## Command

From the repository root:

```powershell
python .agents/skills/mri-coil-design-workflow/scripts/build_learning_cards.py
```

Validate all inputs and preview counts without writing:

```powershell
python .agents/skills/mri-coil-design-workflow/scripts/build_learning_cards.py --dry-run
```

Generate aggregate cards without backfilling record `learning_card` fields:

```powershell
python .agents/skills/mri-coil-design-workflow/scripts/build_learning_cards.py --no-update-records
```

## Input Gate

The compiler reads `results_data_prep/manifest.csv`, the canonical RD/FD
matrices, and `results_data_prep/records/*.json`. Every manifest row must have:

```text
qa_status = validated
sar_status = validated_native_h5
field_archive_status = complete
schema_pass = True
record_hash_match = True
```

The case-local and global copies of each record must be semantically identical.
Compilation fails rather than silently excluding an invalid record.

## Outputs

```text
results_data_prep/learning/
  catalog.json
  cases_global.jsonl
  cases_delta.jsonl
  cases_interaction.jsonl
  cases_prompt_cards.jsonl
```

- `cases_global.jsonl`: one compact structure/performance card per record.
- `cases_delta.jsonl`: one objective-agnostic state/action/outcome card per D2
  perturbation or interaction row.
- `cases_interaction.jsonl`: actual joint delta, additive expectation, and
  residual for every two-parameter interaction.
- `cases_prompt_cards.jsonl`: union of all three card types for retrieval.
- `catalog.json`: counts, QA contract, file map, and retrieval guidance.

The compiler backfills each record's:

```text
learning_card.field_summary_text
learning_card.dominant_effect_labels
learning_card.prompt_card_jsonl_path
```

Summaries and labels are computed from fixed metric thresholds. No LLM-generated
text is used as a training label. Re-running the compiler is idempotent.

An interaction is marked `partial_missing_single_axis_components` when its
matrix does not contain every matching single-axis action around the same
parent. The joint outcome remains usable, but additive expectation and residual
stay `null`; the compiler never borrows an effect from a different parent state.

## Agent Use

For one optimization decision, retrieve:

1. Two to four global cards near the current design.
2. Three to six delta cards matching the contemplated parameter/action.
3. Up to two interaction cards when changing two parameters together.

Cards are evidence, not a replacement for simulation. The agent applies the
runtime objective and constraints, proposes a bounded action, and validates the
candidate in CST before accepting it.
