# Scientific-text mode

Use this mode for papers, abstracts, methods/results sections, literature corpora,
research reports, and other text-modal science data. Keep the existing DataFlow
runtime and operators; specialize the field contract, prompts, and quality gates.

## Establish the data contract

Inspect the sample before selecting operators. Identify, or explicitly create,
these semantic roles:

| Role | Common fields | Rule |
| --- | --- | --- |
| Stable identity | `paper_id`, `document_id`, `source_id`, `doi` | Preserve it through every stage. |
| Source content | `abstract`, `text`, `content`, `section_text`, `cleaned_chunk` | Treat it as the evidence boundary. |
| Location | `section`, `page`, `chunk_id`, `char_start`, `char_end` | Preserve supplied locations; never invent missing ones. |
| Structured result | `science_record`, `claims`, `evidence`, `qa_pairs` | Create a new field; do not overwrite the source. |
| Provenance | `provenance`, `support_status`, `evidence_quote` | Distinguish source-backed output from inference or simulation. |

Default to `grounding=source_only`. Use external knowledge only when the user
explicitly asks for enrichment, and keep enriched facts in a separate field.

## Select the smallest useful workflow

| Scientific-text objective | Preferred chain |
| --- | --- |
| Extract problem, method, data, metrics, findings, limitations | `FormatStrPromptedGenerator` with a strict JSON schema |
| Extract claims with supporting evidence | `FormatStrPromptedGenerator`; require a verbatim evidence span or `Unknown` |
| Generate grounded QA from sufficiently long text | `Text2MultiHopQAGenerator`; retain `supporting_facts` |
| Score fidelity across source and generated fields | `FormatStrPromptedGenerator` → `GeneralFilter` |
| Refine an existing scientific answer while preserving facts | `PromptedRefiner`; inspect its bundled reference first |
| Start from a PDF, URL, or document path | KBC trio, then one of the chains above |
| Remove exact/near duplicates or surface noise | A suitable `general_text` operator after preserving identity fields |

Do not add an LLM stage when a deterministic field transform is sufficient.
Do not use the `chemistry` category merely because a paper is about chemistry;
use it only for supported structured operations such as SMILES extraction or
SMILES-equivalence evaluation.

## Build evidence-first prompts

Gather evidence before asking for synthesis. Keep extraction and synthesis as
separate stages when the task is complex enough that a single prompt would hide
which source text supports which claim.

For structured extraction, require a schema with at least:

```json
{
  "problem": null,
  "method": null,
  "data_or_materials": [],
  "metrics": [
    {
      "name": "",
      "value": null,
      "unit": null,
      "evidence_quote": null
    }
  ],
  "findings": [
    {
      "claim": "",
      "evidence_quote": null,
      "support_status": "Supported|Conflict|Unknown"
    }
  ],
  "limitations": [],
  "provenance": "source"
}
```

Use instructions equivalent to:

```text
Use only SOURCE_TEXT. Do not add background knowledge or repair missing facts.
Copy evidence_quote verbatim from SOURCE_TEXT. Keep every number, sign, range,
unit, chemical symbol, and formula unchanged. If a field is not supported, use
null or []; do not guess. Mark contradictory evidence as Conflict. Return only
JSON matching the schema.
```

For claim-evidence records, require one evidence span per claim. If no local
span supports a claim, set `support_status` to `Unknown` and
`evidence_quote` to `null`; do not manufacture a quotation or citation.

For grounded QA, require:

- answer only from the supplied text;
- `supporting_facts` copied or tightly anchored to the supplied text;
- a refusal or explicit insufficient-evidence result when the answer is absent;
- no citation identifier, page number, or experimental result that is not present;
- questions that remain answerable after the output is separated from hidden prompt context.

For evaluation, score each dimension separately before filtering:

1. Evidence fidelity: every substantive claim is supported.
2. Numeric fidelity: values, signs, ranges, units, and comparison directions match.
3. Entity fidelity: methods, datasets, organisms, materials, and formulas are preserved.
4. Coverage: required schema fields were considered; missing evidence remains null.
5. Provenance clarity: source-backed, inferred, and simulated content are not mixed.

Prefer machine-parseable integer or JSON scores. Parse them into typed fields
before applying `GeneralFilter`.

## Guard against common scientific-data failures

Check each applicable failure explicitly:

- **Reading order corruption**: multi-column PDFs may interleave columns,
  captions, headers, or footers. Inspect converted samples before chunking.
- **Table/formula loss**: text extraction can omit figures, table structure, or
  equations. Do not claim that absent content was parsed successfully.
- **Boundary loss**: chunking can separate a result from its qualifier, unit,
  caption, or section heading. Prefer sentence/semantic splitting and sufficient
  overlap; retain section and chunk identifiers when available.
- **Abstract overconfidence**: an abstract rarely supports detailed experimental
  claims. Mark unsupported details `Unknown` rather than extrapolating.
- **Citation fabrication or misattribution**: never generate DOI, title, author,
  page, or reference metadata that is absent from the row.
- **Numeric drift**: reject outputs that change decimal points, signs, ranges,
  units, inequality direction, or baseline/comparator association.
- **Hedge escalation**: preserve uncertainty terms such as “may”, “suggests”,
  and “not statistically significant”; do not rewrite them as certainty.
- **Synthetic-source pollution**: keep generated summaries/captions in separate
  fields and never treat them as original evidence.
- **Nested QA output**: `Text2MultiHopQAGenerator` returns a list of QA dicts per
  row. Explode it before addressing `question` or `answer` as dataframe columns.
- **Schema drift**: require exact keys, no commentary outside JSON, and
  `additionalProperties: false` when the serving supports JSON schema output.

## Apply release gates

Before presenting or committing the pipeline, verify:

- sample identities and source text survive every step;
- every consumed field exists before use;
- prompts state the evidence boundary and missing-data behavior;
- output fields distinguish evidence from synthesis;
- a small sample has been inspected for PDF order, schema validity, numeric
  preservation, and unsupported claims;
- the pipeline reports or preserves rejected/`Unknown` rows when auditability is
  required instead of silently dropping them;
- real, inferred, simulated, and illustrative records are explicitly labeled.
