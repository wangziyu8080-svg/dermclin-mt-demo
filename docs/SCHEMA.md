# Image-free public schema

The complete benchmark uses image-prompt-answer records. This preview replaces
every image reference with the non-resolving placeholder `<image-withheld>` and
uses synthetic sample identifiers. No example is copied from the benchmark.

```json
{
  "id": "synthetic-diagnosis-001",
  "example_type": "synthetic_schema_only",
  "task": "diagnosis",
  "image": "<image-withheld>",
  "conversations": [
    {"from": "human", "value": "<image>\nQuestion text"},
    {"from": "gpt", "value": "Normalized answer"}
  ]
}
```

## Required fields

- `id`: synthetic preview identifier; it does not match a benchmark identifier.
- `example_type`: always `synthetic_schema_only` in this repository.
- `task`: `descriptors`, `diagnosis`, `differential`, `management`, or
  `consultation`.
- `image`: always the literal string `<image-withheld>`.
- `conversations`: exactly one human prompt followed by one target answer.

Differential examples additionally contain `mcq_meta.options` with four
candidates and `mcq_meta.answer_text` with the normalized disease name. The
target is a disease name, not an option letter.

The descriptor target is a comma-separated sequence of normalized terms. The
complete 60-term vocabulary is intentionally not included in this preview.

