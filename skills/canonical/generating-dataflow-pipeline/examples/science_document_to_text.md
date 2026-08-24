# Example: Scientific Document or Scanned Image to Text

## Target

“Convert scientific PDFs and scanned page images to Markdown-backed text chunks
without rewriting their content.”

## Sample data

```jsonl
{"source_id":"paper-001","source":"./papers/paper-001.pdf","media_type":"application/pdf","modality":"document"}
{"source_id":"scan-002","source":"./scans/page-002.png","media_type":"image/png","modality":"document"}
```

## Intermediate operator decision

```json
{
  "mode": "science_multimodal",
  "modality": "document",
  "capability_status": "conditional",
  "missing_prerequisites": ["MINERU_API_KEY must be set without exposing its value"],
  "unsupported": [],
  "ops": ["FileOrURLToMarkdownConverterAPI", "KBCChunkGenerator"],
  "field_flow": "source -> text_path -> raw_chunk",
  "reason": "The target needs row-level source text. MinerU converts PDF/images to raw Markdown and the deterministic chunker materializes bounded text chunks. LLM cleaning is omitted to avoid altering scientific content."
}
```

## Pipeline

```python
from dataflow.operators.knowledge_cleaning import (
    FileOrURLToMarkdownConverterAPI,
    KBCChunkGenerator,
)
from dataflow.utils.storage import FileStorage


class ScientificDocumentIngestionPipeline:
    def __init__(self):
        self.storage = FileStorage(
            first_entry_file_name="science_sources.jsonl",
            cache_path="./cache_science_ingestion",
            file_name_prefix="ingest_step",
            cache_type="jsonl",
        )
        self.converter_step1 = FileOrURLToMarkdownConverterAPI(
            intermediate_dir="./cache_science_ingestion/markdown",
            mineru_backend="vlm",
            api_key=None,  # operator reads MINERU_API_KEY from the environment
        )
        self.chunker_step2 = KBCChunkGenerator(
            chunk_size=512,
            chunk_overlap=50,
            split_method="sentence",
            min_tokens_per_chunk=100,
            tokenizer_name="bert-base-uncased",
        )

    def forward(self):
        self.converter_step1.run(
            storage=self.storage.step(),
            input_key="source",
            output_key="text_path",
        )
        self.chunker_step2.run(
            storage=self.storage.step(),
            input_key="text_path",
            output_key="raw_chunk",
        )


if __name__ == "__main__":
    ScientificDocumentIngestionPipeline().forward()
```

## Checks

- Keep `source_id`, `source`, and `text_path`; do not overwrite source fields.
- Stop after the converter when only Markdown files are required.
- Add `KBCTextCleaner` only when explicitly requested, and keep `raw_chunk` as
  the evidence-preserving version.
- Inspect multi-column order, formulas, tables, headers, footers, and empty
  `text_path`/`raw_chunk` values before downstream generation.
