# DermClin-MT Public Preview

This folder is the minimal public companion to the manuscript **DermClin-MT:
An Auditable Multitask Benchmark for Dermatology MLLMs**.

It documents the benchmark organization and record schema without publishing
the complete annotations, task splits, taxonomies, audit traces, source-image
indices, or any clinical images. It is a paper-facing preview, not the full
dataset, and cannot reproduce the reported experiments.

## Manuscript-aligned benchmark summary

DermClin-MT contains 12,415 unique image identifiers and 34,440 audited
question-answer records across five tasks:

| Public task key | Task in the manuscript | Target form |
|---|---|---|
| `descriptors` | Lesion Description / Descriptor Extraction | Terms from a fixed 60-term vocabulary |
| `diagnosis` | Normalized Diagnosis | One of 68 normalized diagnosis classes |
| `differential` | Candidate-Conditioned Differential Diagnosis | One disease selected from four candidates drawn from a 65-class space |
| `management` | Management | Concise management recommendation |
| `consultation` | Consultation | Patient-oriented explanation and follow-up guidance |

The manuscript reports 27,930 training records and 6,510 held-out test records.
Same-task train/test image overlap is zero for all five tasks. Cross-task image
reuse is retained because one case may support different questions.

## Contents

- `examples/schema_examples.json`: five synthetic, image-free schema examples,
  one per task. They are not benchmark records.
- `docs/SCHEMA.md`: public record structure and output constraints.
- `docs/RELEASE_BOUNDARY.md`: explicit inclusion and exclusion boundary.
- `scripts/validate_preview.py`: validates the preview and blocks image files or
  reconstructable source fields.
- `annotation_tool/`: generic, local-only review interface. No annotation
  database or private data are bundled.

## Deliberately not included

- raw, clinical, patient, or demo images;
- original image identifiers, source URLs, relative image paths, or bulk source
  indices;
- complete train/test annotations and empty validation files;
- the 60-term list, 68-class mapping, 65-class differential candidate pool, and
  fine-to-coarse mappings;
- private annotation databases, construction scripts, prompts, internal
  reports, reviewer traces, audit logs, intermediate outputs, or model
  checkpoints.

Raw images must be obtained from the original repositories and used under their
respective terms. Restricted DDI images and reconstructable records are not
redistributed.

## Validate

```bash
python3 scripts/validate_preview.py
```

## Intended use

The preview is intended for research documentation and benchmark inspection.
It is not a medical device and must not be used for autonomous diagnosis,
treatment selection, or clinical decision-making.

## Citation and license

The paper citation will be added after publication. The documentation, synthetic
examples, and validation script in this preview are released under Apache-2.0.
No third-party image or dataset license is sublicensed by this repository.
