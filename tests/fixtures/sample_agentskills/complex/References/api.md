# API Reference

## validate(path)
Run the full validation pipeline against a dataset directory and return a `ValidationReport` instance.

## summarise(report)
Render a markdown summary of a `ValidationReport`. Pure function; no I/O.

## load_manifest(path)
Parse `Resources/dataset-manifest.csv` and return an ordered list of dataset descriptors. Raises `ManifestError` on malformed rows.
