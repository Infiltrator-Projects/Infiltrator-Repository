#!/usr/bin/env python3
"""Regression checks for serialized repository publication."""

from pathlib import Path

workflow = Path(".github/workflows/publish.yml").read_text(encoding="utf-8")

assert "group: pages" in workflow
assert "cancel-in-progress: false" in workflow
assert "cancel-in-progress: true" not in workflow

assert "repository_dispatch:" not in workflow
assert "application-release" not in workflow
assert "/dispatches" not in workflow

# Central discovery must remain an off-boundary five-minute pull. GitHub
# documents higher schedule load at common minute boundaries, especially :00.
assert "cron: '2-57/5 * * * *'" in workflow
assert "cron: '*/5 * * * *'" not in workflow

publish_index = workflow.index("name: Publish Beta Repository")
concurrency_index = workflow.index("concurrency:", publish_index)
cancel_index = workflow.index("cancel-in-progress: false", concurrency_index)
assert publish_index < concurrency_index < cancel_index

print("Repository publication concurrency contract passed")
