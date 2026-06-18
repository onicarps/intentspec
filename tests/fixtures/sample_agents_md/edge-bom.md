# BOM Prefixed Agent

An agent specification whose file begins with a UTF-8 byte-order mark to exercise BOM-tolerant readers.

## Goals
- Verify the converter strips the BOM before kebab-casing the H1 into agent.name.
- Confirm extraction is byte-equal to a BOM-less twin file once both pass through yaml.safe_load.

## Constraints
- MUST decode the source file with utf-8-sig so the BOM is removed before tokenisation.
- ALWAYS preserve the agent.name as plain ASCII without any leading invisible characters.

## Non-negotiables
- NEVER emit a YAML output that itself begins with a BOM.

## Tools

| Tool | Why |
|------|-----|
| python3 | Reference interpreter for BOM-aware decoding |
| iconv | Optional fallback to normalise stray encodings |
