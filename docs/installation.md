# Installation

## Requirements

- Python 3.11+
- pip

## Install from PyPI

```bash
pip install intentspec
```

## Install from source

```bash
git clone https://github.com/onicarps/intentspec.git
cd intentspec
pip install -e ".[dev]"
```

## Verify

```bash
intentspec --version
# IntentSpec 0.1.0
```

## Quickstart

Initialize a new intent spec interactively:

```bash
intentspec init --quickstart
```

Or from an existing AGENTS.md:

```bash
intentspec init --from AGENTS.md ./AGENTS.md
```

Validate your spec:

```bash
intentspec validate
```

Check the Intent Debt Score:

```bash
intentspec score
```
