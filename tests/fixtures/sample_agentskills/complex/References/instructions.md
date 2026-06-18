# Instructions Reference

This reference document elaborates on the `## Instructions` section of `SKILL.md` for the dataset validator.

## Streaming reader rationale
Datasets occasionally exceed available memory. The validator must use a streaming reader (PyArrow's `iter_batches` or Python's `csv.reader`) so partial validation is still observable for very large files.

## Schema drift policy
Schema drift between the manifest and the actual files is reported, never silently corrected. Operators receive the report through the standard output channel.

## Determinism notes
The report uses sorted file order and a stable hash of validation timings to keep diffs readable across consecutive runs.
