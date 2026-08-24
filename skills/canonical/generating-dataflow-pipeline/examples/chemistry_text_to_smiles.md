# Example: Chemistry Text to SMILES

## Target

“Extract SMILES from OCR chemistry text and compare it with a supplied gold
SMILES when available.”

## Sample data

```jsonl
{"source_id":"chem-001","modality":"chemistry_text","text":"The product was aspirin (SMILES: CC(=O)Oc1ccccc1C(=O)O).","abbreviations":"","golden_label":"CC(=O)Oc1ccccc1C(=O)O"}
```

## Intermediate operator decision

```json
{
  "mode": "science_multimodal",
  "modality": "chemistry_text",
  "capability_status": "conditional",
  "missing_prerequisites": ["confirm LLM serving configuration"],
  "unsupported": [],
  "ops": ["ExtractSmilesFromTextGenerator", "SmilesEquivalenceDatasetEvaluator"],
  "field_flow": "text+abbreviations -> synth_smiles; golden_label+synth_smiles -> final_result",
  "reason": "The source contains explicit structural text and a gold label. Extraction is model-produced; equivalence evaluation is added only because golden_label exists."
}
```

## Pipeline

```python
from dataflow.operators.chemistry import (
    ExtractSmilesFromTextGenerator,
    SmilesEquivalenceDatasetEvaluator,
)
from dataflow.serving import APILLMServing_request
from dataflow.utils.storage import FileStorage


class ChemistryTextToSmilesPipeline:
    def __init__(self):
        self.storage = FileStorage(
            first_entry_file_name="chemistry_text.jsonl",
            cache_path="./cache_chemistry",
            file_name_prefix="chem_step",
            cache_type="jsonl",
        )
        self.llm_serving = APILLMServing_request(
            api_url="https://your-endpoint/v1/chat/completions",
            key_name_of_api_key="DF_API_KEY",
            model_name="your-model",
            max_workers=10,
        )
        self.extractor_step1 = ExtractSmilesFromTextGenerator(
            llm_serving=self.llm_serving,
        )
        self.evaluator_step2 = SmilesEquivalenceDatasetEvaluator(
            llm_serving=self.llm_serving,
        )

    def forward(self):
        self.extractor_step1.run(
            storage=self.storage.step(),
            input_content_key="text",
            input_abbreviation_key="abbreviations",
            output_key="synth_smiles",
        )
        self.evaluator_step2.run(
            storage=self.storage.step(),
            input_golden_key="golden_label",
            input_synth_key="synth_smiles",
            output_key="final_result",
        )


if __name__ == "__main__":
    ChemistryTextToSmilesPipeline().forward()
```

## Capability guards

- If `golden_label` is absent, omit the evaluator and label `synth_smiles` as
  model-extracted and unverified.
- If the input is only `C2H6O`, report `ambiguous`: a formula does not uniquely
  identify an isomer or one authoritative SMILES.
- If the source is a 2D molecular structure image, report `unsupported` with
  missing capability `OCSR`; do not use a generic VLM to guess bond structure.
- Inspect `[]` extraction results and report their rate instead of treating them
  as successful conversions.
