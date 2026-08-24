# Multimodal scientific ingestion mode

Use this reference when a JSONL row points to a document, image, audio file,
visual-QA item, PDF-VQA intermediate artifact, or chemistry text that should
produce SMILES. Reuse registered DataFlow operators only. Never describe a
missing perception or chemistry capability as executable.

## Contents

1. [Inspect and partition input](#inspect-and-partition-input)
2. [Use the JSONL semantic contract](#use-the-jsonl-semantic-contract)
3. [Route supported modalities](#route-supported-modalities)
4. [Apply exact operator contracts](#apply-exact-operator-contracts)
5. [Enforce capability guards](#enforce-capability-guards)
6. [Emit decision examples](#emit-decision-examples)
7. [Validate conversion quality](#validate-conversion-quality)

## Inspect and partition input

Read representative rows before choosing operators. Map existing columns to
these roles without renaming user fields unnecessarily:

| Role | Preferred field | Common alternatives |
| --- | --- | --- |
| Stable identity | `source_id` | `paper_id`, `document_id`, `id` |
| File or URL | `source` | `pdf_path`, `image_path`, `audio_path`, `url` |
| MIME hint | `media_type` | `mime_type`, `content_type` |
| Intended treatment | `modality` | `data_type`, `source_type` |
| Visual question | `question` | `prompt`, `query` |
| Chemistry context | `abbreviations` | `monomers`, `chemical_context` |
| SMILES gold label | `golden_label` | `reference_smiles`, `gold_smiles` |

Require an explicit `modality` when the same image extension could mean a
scanned document, a visual-QA item, or a molecular structure diagram. Infer a
modality from a file extension only when the interpretation is unambiguous.

Treat a JSONL containing more than one modality as a collection of homogeneous
subpipelines, not as one dynamically branching pipeline. For each modality:

1. Read the same input JSONL.
2. Apply `GeneralFilter` first, using only existing `modality`/`media_type`/path
   fields to keep the relevant rows.
3. Run the modality-specific chain.
4. Write a separate cache/output JSONL. Do not claim that DataFlow merged the
   outputs unless a real merge step exists.

If `modality` is absent and path inference is insufficient, ask for that field
instead of generating unsafe filter logic.

## Use the JSONL semantic contract

Recommend this shape while accepting equivalent user fields:

```json
{
  "source_id": "stable-id",
  "source": "./path-or-url",
  "media_type": "application/pdf",
  "modality": "document",
  "question": null,
  "abbreviations": null,
  "golden_label": null
}
```

Store paths/URLs and derived fields in JSONL. Never embed PDF, image, or audio
bytes as base64. Preserve `source_id`, the original `source`, and supplied
provenance fields through every conversion.

Use these standard derived fields unless the user requests compatible names:

| Modality | Derived fields |
| --- | --- |
| Document/scanned image | `text_path`; optionally `raw_chunk`, then optionally `cleaned_chunk` |
| Audio | `transcript` |
| Visual QA | `vqa_answer` |
| Chemistry text | `synth_smiles`; optionally `final_result` when gold exists |

Never overwrite the original source. Keep raw and model-cleaned text in separate
fields because cleaning can alter formulas, units, tables, or qualifiers.

## Route supported modalities

| Input and target | Capability | Chain |
| --- | --- | --- |
| PDF/image/HTML/XML/TXT/MD → Markdown path | `supported` | one `FileOrURLToMarkdownConverter*` |
| Markdown path → row-level chunks | `supported` | add `KBCChunkGenerator` |
| Noisy chunks → model-cleaned chunks | `conditional` | optionally add `KBCTextCleaner`; preserve `raw_chunk` |
| Speech path/URL → transcript | `conditional` | `Speech2TextGenerator`; serving must support audio |
| Encoded image+question → answer | `conditional` | `PromptedVQAGenerator`; serving and row shape must support vision |
| PDF-VQA intermediate artifacts → formatted VQA data | `conditional` | select `pdf2vqa` operators only for fields already present |
| OCR/scientific chemistry text → extracted SMILES | `conditional` | `ExtractSmilesFromTextGenerator` |
| Generated SMILES + gold SMILES → equivalence result | `conditional` | `SmilesEquivalenceDatasetEvaluator` |
| Molecular formula alone → unique SMILES | `unsupported` | report structural ambiguity |
| 2D molecular structure image → SMILES | `unsupported` | report missing OCSR operator |

Choose a document converter from actual environment capabilities:

- `FileOrURLToMarkdownConverterAPI`: use when MinerU API access is configured;
  leave `api_key=None` so the operator reads `MINERU_API_KEY` from the environment.
- `FileOrURLToMarkdownConverterLocal`: use when local MinerU and its model/backend
  are available.
- `FileOrURLToMarkdownConverterFlash`: use for the configured FlashMinerU GPU
  path; require a non-null `mineru_model_path`.

Stop after the converter when the target is only a Markdown artifact. Add
`KBCChunkGenerator` when downstream operators need row-level text. Add
`KBCTextCleaner` only when model cleaning is requested and its risk is accepted.

Use `PromptedVQAGenerator` only for visual QA. Do not use it as generic OCR or
as optical chemical structure recognition. For PDF VQA, note that the registered
`pdf2vqa` family formats MinerU/layout/LLM response artifacts; it does not supply
a hidden external inference stage. Mark the plan `conditional` when required
intermediate columns are missing.

## Apply exact operator contracts

In harness/MCP mode, call `get_operator_detail_by_name` for every selected
non-core operator and treat its installed signature as authoritative. Offline,
use these bundled signatures:

```text
FileOrURLToMarkdownConverterAPI(
  intermediate_dir="intermediate", mineru_backend="vlm", api_key=None
).run(storage, input_key="source", output_key="text_path")

FileOrURLToMarkdownConverterLocal(
  intermediate_dir="intermediate", mineru_backend="vlm-auto-engine",
  mineru_source="local", mineru_model_path=None,
  mineru_download_model_type="vlm"
).run(storage, input_key="source", output_key="text_path")

FileOrURLToMarkdownConverterFlash(
  intermediate_dir="intermediate", mineru_model_path=None, batch_size=4,
  replicas=1, num_gpus_per_replica=1,
  engine_gpu_util_rate_to_ray_cap=0.9
).run(storage, input_key="source", output_key="text_path")

Speech2TextGenerator(llm_serving, system_prompt="...").run(
  storage, input_key="source", output_key="transcript"
)

PromptedVQAGenerator(llm_serving, system_prompt="...").run(
  storage, input_key="raw_content", output_key="vqa_answer"
)

ExtractSmilesFromTextGenerator(llm_serving, prompt_template=...).run(
  storage, input_content_key="text", input_abbreviation_key="abbreviations",
  output_key="synth_smiles"
)

SmilesEquivalenceDatasetEvaluator(llm_serving).run(
  storage, input_golden_key="golden_label",
  input_synth_key="synth_smiles", output_key="final_result"
)
```

`PromptedVQAGenerator`'s `raw_content` must already match the installed
operator's image/question encoding. Inspect a sample and the live detail; do not
invent a payload shape from column names.

The `pdf2vqa` operators require explicit intermediate fields:

- `MinerU2LLMInputOperator`: Markdown path → converted layout path.
- `LLMOutputParser`: response path + converted layout + name → QA-list path.
- `QA_Merger`: QA-list path + name → merged QA artifacts/`qa_item`.
- `PDF_Merger`: PDF-list field + name → merged PDF path.
- `VQAFormatter`: `qa_item` → `messages` + `images`.

Only emit operators whose required input fields exist or are produced earlier.

## Enforce capability guards

Return one of `supported`, `conditional`, or `unsupported` before code:

- `supported`: the registry contains a complete chain and required non-secret
  configuration is available.
- `conditional`: the operator exists but a modality-capable serving, model path,
  API-key environment variable, row encoding, gold label, or intermediate
  artifact is missing. List every item in `missing_prerequisites`.
- `unsupported`: no registered operator performs the requested transformation.
  Put the exact request and missing capability in `unsupported`; do not emit
  fake runnable code.

Apply chemistry-specific guards:

- Treat a molecular formula such as `C2H6O` as composition, not structure.
  Multiple isomers can share it, so never output one authoritative SMILES
  without a name, structure, or other disambiguating evidence.
- Treat OCR text containing molecule names, explicit SMILES, monomer context, or
  structural descriptions as eligible for `ExtractSmilesFromTextGenerator`, but
  label its output model-extracted rather than chemically verified.
- Treat a 2D structure diagram as requiring optical chemical structure
  recognition (OCSR). No current registered operator provides it.
- Add `SmilesEquivalenceDatasetEvaluator` only when both generated and golden
  fields exist. Without gold, state `unverified`; do not substitute an LLM score
  for chemical equivalence.
- Remember that failed SMILES response parsing can produce `[]`; inspect and
  report empty-result rates.

## Emit decision examples

For a JSONL containing both document and audio rows, emit separate decisions:

```json
{
  "mode": "science_multimodal",
  "input_strategy": "split_by_modality",
  "subpipelines": [
    {
      "modality": "document",
      "capability_status": "conditional",
      "missing_prerequisites": ["choose one available MinerU backend"],
      "unsupported": [],
      "ops": ["GeneralFilter", "FileOrURLToMarkdownConverterAPI", "KBCChunkGenerator"],
      "field_flow": "all rows -> modality=document -> source -> text_path -> raw_chunk"
    },
    {
      "modality": "audio",
      "capability_status": "conditional",
      "missing_prerequisites": ["confirm audio-capable serving"],
      "unsupported": [],
      "ops": ["GeneralFilter", "Speech2TextGenerator"],
      "field_flow": "all rows -> modality=audio -> source -> transcript"
    }
  ]
}
```

For a formula-only request, do not emit pipeline code:

```json
{
  "mode": "science_multimodal",
  "modality": "molecular_formula",
  "capability_status": "unsupported",
  "missing_prerequisites": ["molecular identity or structural evidence"],
  "unsupported": ["C2H6O does not determine one unique molecular structure or SMILES"],
  "ops": [],
  "field_flow": "molecular_formula -/-> unique_smiles"
}
```

For a 2D molecular diagram, report `missing capability: OCSR` and keep `ops`
empty. For chemistry text without `golden_label`, select only
`ExtractSmilesFromTextGenerator`, set comparison status to `unverified`, and do
not add `SmilesEquivalenceDatasetEvaluator`.

## Validate conversion quality

Before presenting or committing a pipeline, verify applicable gates:

- Every subpipeline filters its modality before any modality-specific operator.
- File paths/URLs remain references in JSONL; no binary/base64 payload is added.
- Document conversion preserves raw Markdown before chunking or cleaning.
- OCR samples preserve reading order, formulas, tables, units, captions, and
  source identity; missing visual content is reported rather than reconstructed.
- Transcription keeps scientific terms, quantities, spelling uncertainty, and
  source linkage; the selected serving supports audio.
- VQA input encoding matches the installed operator and the selected serving
  supports images.
- Chemistry outputs distinguish extracted, equivalent-to-gold, ambiguous, and
  unsupported states.
- Empty conversion output is not silently passed to downstream generation.
