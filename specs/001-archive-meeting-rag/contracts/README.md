# Contracts

**Created**: 2025-11-02  
**Feature**: Archive Meeting Retrieval & Grounded Interpretation RAG

## Overview

This directory contains API contracts for the Archive-RAG CLI commands.

## Files

- **cli-commands.md**: Complete CLI command interface specification
  - Command signatures, arguments, options
  - Input/output formats
  - Error handling
  - Examples

## Contract Types

### CLI Commands

Since this is a CLI-focused project (not a web API), contracts define command-line interfaces:

- `index`: Ingest and index meeting JSON files
- `query`: Query RAG system with evidence-bound answers
- `topic-model`: Discover topics in meeting archive
- `extract-entities`: Extract named entities from meetings
- `evaluate`: Run evaluation suite
- `audit-view`: View and analyze audit logs

## Contract Compliance

All CLI commands must:
- Follow Typer CLI conventions
- Support `--help` for documentation
- Use structured JSON output for programmatic use
- Use human-readable text output for interactive use
- Follow error code conventions (0 = success, >0 = error)
- Output errors to stderr, results to stdout

## Validation

Contract tests verify:
- Command signatures match specification
- Output formats match specification
- Error codes match specification
- Options and arguments validated correctly
