---
name: graphify
description: "Generate and navigate a dependency graph of the repository"
type: prompt
---

You are in Graphify mode. Analyze the repository as a dependency graph.

## Step 1 — Check for existing graph

Look for `.mycoder/graphs/repo_graph.json` in the project root.
If found, load and use it. If not, generate one.

## Step 2 — Generate the graph

Scan all source files and extract dependency relationships:

**Python**: `import X`, `from X import Y`
**JavaScript/TypeScript**: `import ... from`, `require(...)`
**Go**: `import "..."`
**Rust**: `use ...`, `mod ...`

Build a graph with:
```json
{
  "nodes": [
    {"id": "path/to/file", "type": "module", "language": "python", "imports": 5, "imported_by": 3}
  ],
  "edges": [
    {"from": "path/a.py", "to": "path/b.py", "type": "import"}
  ],
  "stats": {
    "total_files": 42,
    "total_edges": 128,
    "most_connected": ["path/core.py", "path/utils.py"],
    "circular_deps": []
  }
}
```

Save to `.mycoder/graphs/repo_graph.json`.

## Step 3 — Work on graph nodes

Use the graph to:
- **Impact analysis**: Which files are affected by changes to module X?
- **Circular dependencies**: Flag and suggest fixes
- **Architecture overview**: Show the module hierarchy
- **Change planning**: Minimize blast radius of modifications
- **Entry points**: Identify root modules and leaf utilities

## Output format

Always show:
1. Summary statistics (files, edges, clusters)
2. Top connected nodes (highest import/imported_by)
3. Any circular dependencies found
4. Relevant subgraph for the user's specific question
