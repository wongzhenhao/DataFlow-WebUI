# Example: Scientific Audio to Transcript

## Target

“Transcribe scientific interview recordings into text while retaining source
identity.”

## Sample data

```jsonl
{"source_id":"interview-001","source":"./audio/interview-001.wav","media_type":"audio/wav","modality":"audio"}
```

## Intermediate operator decision

```json
{
  "mode": "science_multimodal",
  "modality": "audio",
  "capability_status": "conditional",
  "missing_prerequisites": ["confirm that the configured serving/model accepts audio"],
  "unsupported": [],
  "ops": ["Speech2TextGenerator"],
  "field_flow": "source -> transcript",
  "reason": "Speech2TextGenerator is the registered speech transcription operator. The output key is mapped to transcript while source_id and source remain unchanged."
}
```

## Pipeline

```python
from dataflow.operators.core_speech import Speech2TextGenerator
from dataflow.serving import APILLMServing_request
from dataflow.utils.storage import FileStorage


class ScientificAudioTranscriptionPipeline:
    def __init__(self):
        self.storage = FileStorage(
            first_entry_file_name="science_audio.jsonl",
            cache_path="./cache_science_audio",
            file_name_prefix="audio_step",
            cache_type="jsonl",
        )
        self.llm_serving = APILLMServing_request(
            api_url="https://your-multimodal-endpoint/v1/chat/completions",
            key_name_of_api_key="DF_API_KEY",
            model_name="your-audio-capable-model",
            max_workers=10,
        )
        self.transcriber_step1 = Speech2TextGenerator(
            llm_serving=self.llm_serving,
            system_prompt=(
                "Transcribe the supplied scientific audio faithfully. Preserve "
                "technical terms, quantities, units, uncertainty, and speaker wording."
            ),
        )

    def forward(self):
        self.transcriber_step1.run(
            storage=self.storage.step(),
            input_key="source",
            output_key="transcript",
        )


if __name__ == "__main__":
    ScientificAudioTranscriptionPipeline().forward()
```

## Checks

- Confirm audio support before emitting runnable code; an ordinary text-only LLM
  endpoint is insufficient.
- Keep empty or failed transcripts out of downstream scientific generation.
- Preserve uncertain terminology rather than silently normalizing it.
