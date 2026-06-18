---
name: log-rotator
description: "Rotates and compresses application log files on a daily cadence."
version: 0.1.0
tags: [ops, logs]
---

# Log Rotator

## Overview
A small skill that rotates yesterday's log file, compresses it with gzip, and prunes archives older than 30 days.

## Instructions
- MUST run `Scripts/run.sh` once per day from the operator's cron.
- ALWAYS verify the destination directory has at least 1 GB free before rotating.
- DO NOT rotate logs that are still being written by an active process holding the file handle.

## Notes
- Never delete the most recent rotated archive even if the retention window has elapsed.
