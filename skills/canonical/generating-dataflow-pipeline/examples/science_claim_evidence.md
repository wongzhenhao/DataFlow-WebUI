# Example: Scientific Claim-Evidence Extraction

## Target

“Extract each paper's main finding and the exact supporting sentence. Keep
unsupported fields empty and reject records with changed numbers or units.”

## Sample data

```jsonl
{"paper_id":"P001","section":"Results","section_text":"Treatment reduced mean systolic pressure by 8.2 mmHg (95% CI, 4.1 to 12.3; p=0.002) compared with placebo."}
```

## Intermediate operator decision

```json
{
  "mode": "science_text",
  "grounding": "source_only",
  "ops": ["FormatStrPromptedGenerator", "FormatStrPromptedGenerator", "GeneralFilter"],
  "field_flow": "paper_id+section+section_text -> claim_record -> fidelity_score -> filtered_rows",
  "provenance_fields": ["paper_id", "section", "evidence_quote", "support_status"],
  "quality_gates": ["verbatim evidence", "numeric and unit fidelity", "strict JSON"],
  "reason": "The extraction and fidelity check each depend on multiple fields. Separate evidence extraction from evaluation, then apply a deterministic threshold."
}
```

## Operator pattern

1. Use `FormatStrPromptedGenerator` to produce `claim_record` from
   `paper_id`, `section`, and `section_text`. Require strict JSON containing
   `claim`, `evidence_quote`, `support_status`, and `provenance`.
2. Use a second `FormatStrPromptedGenerator` to compare `section_text` with
   `claim_record`. Return an integer `fidelity_score` from 1 to 5 after checking
   support, numbers, signs, ranges, units, and uncertainty language.
3. Parse the score to an integer if needed, then use `GeneralFilter` to retain
   rows with `fidelity_score >= 4`.

## Prompt constraints

Use only `section_text`. Copy `evidence_quote` verbatim. If no span supports the
claim, return `support_status="Unknown"` and `evidence_quote=null`. Never create
a DOI, page, author, citation, value, or unit. Preserve `paper_id` and `section`
unchanged for auditability.

## Caveats

- Do not use `PromptedFilter`: the evaluation needs both source and extraction.
- Do not filter `Unknown` rows if the user needs an audit trail; write them to a
  review output or retain a rejection reason.
- Inspect the exact signature in the `FormatStrPromptedGenerator` reference and
  map every template placeholder to an existing dataframe field.
