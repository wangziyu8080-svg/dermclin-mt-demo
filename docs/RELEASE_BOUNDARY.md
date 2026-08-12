# Public release boundary

This repository implements the manuscript's current **public preview** claim.
Its purpose is to show the benchmark scope and machine-readable record shape
without disclosing the complete research artifact.

## Included

- manuscript-aligned benchmark totals and five-task terminology;
- an image-free, synthetic example for each task;
- field definitions and output constraints;
- a release validator that rejects image files and reconstructable source data.
- generic annotation-tool source code, with no embedded data or review state.

## Excluded

- all original and derived clinical images, including thumbnails and examples;
- complete annotations, source indices, task partitions, and per-class counts;
- label vocabularies, taxonomy mappings, candidate pools, and normalization
  dictionaries;
- physician review records and annotation databases, construction code, audit
  outputs, internal notes, and intermediate files;
- training configurations, model weights, and unpublished evaluation artifacts.

## Future release

Subject to source licenses and the paper's publication status, selected derived
annotations, taxonomies, splits, scripts, and audit materials may be released
later. A future release must undergo a separate privacy, licensing, and
manuscript-consistency review. This preview does not make that future material
public by implication.
