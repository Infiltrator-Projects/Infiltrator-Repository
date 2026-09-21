#!/usr/bin/env python3
"""Regression checks for serialized repository publication."""

from pathlib import Path

workflow = Path(".github/workflows/publish.yml").read_text(encoding="utf-8")

assert "group: pages" in workflow
assert "cancel-in-progress: false" in workflow
assert "cancel-in-progress: true" not in workflow

assert "repository_dispatch:" in workflow
assert "types: [application-release]" in workflow

publish_index = workflow.index("name: Publish Beta Repository")
concurrency_index = workflow.index("concurrency:", publish_index)
cancel_index = workflow.index("cancel-in-progress: false", concurrency_index)
assert publish_index < concurrency_index < cancel_index

print("Repository publication concurrency contract passed")
