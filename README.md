# Study Route

Generate personalized study routes from chapter knowledge data.

Analyzes concepts, definitions, and relationships to produce:
- A **linear step-by-step study path** with estimated time and difficulty
- A **prerequisite DAG** showing concept dependencies
- **Topological layers** for parallel study options

## Usage

```python
from study_route import StudyRoutePlanner

planner = StudyRoutePlanner()
route = planner.plan(
    terms=[{"term": "编码", "definition": "...", "page": 1}],
    graph={"nodes": [...], "edges": [...]},
    summaries=[{"section": "第一节", "summary": "..."}],
    mindmap={"title": "第四章", "children": [...]},
)

for step in route.steps:
    print(f"Step {step.order}: {step.title} ({step.estimated_time})")
```

## CLI

```bash
study-route --knowledge-json ../knowledge-base/output/knowledge.json
study-route --pdf chapter.pdf --extract
```
