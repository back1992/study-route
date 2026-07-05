# Study Route

Generate personalized study routes from chapter knowledge data.

## Features

- **Linear study path**: Step-by-step learning sequence with estimated time and difficulty
- **Prerequisite DAG**: Directed acyclic graph showing concept dependencies
- **Topological layers**: Identify concepts that can be studied in parallel
- **LLM-enhanced**: Optional OpenAI-compatible LLM integration for smarter prerequisite inference
- **Algorithmic fallback**: Works without LLM using graph analysis

## Installation

```bash
pip install git+https://github.com/back1992/study-route.git
```

Or for development:

```bash
git clone https://github.com/back1992/study-route.git
cd study-route
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

## Usage

### Python API

```python
from study_route import StudyRoutePlanner

planner = StudyRoutePlanner()
route = planner.plan(
    terms=[{"term": "编码", "definition": "...", "page": 1}],
    graph={"nodes": [...], "edges": [...]},
    summaries=[{"section": "第一节", "summary": "..."}],
)

for step in route.steps:
    print(f"Step {step.order}: {step.title} ({step.estimated_time})")
```

### CLI

```bash
# Generate from knowledge JSON
study-route --knowledge-json path/to/knowledge.json

# Extract from PDF and generate (requires knowledge-base package)
study-route --extract --pdf chapter.pdf

# Output as human-readable text
study-route --knowledge-json knowledge.json --format text -o route.txt
```

### With LLM Enhancement

Set environment variables to enable LLM-based prerequisite inference:

```bash
export LLM_API_KEY="your-api-key"
export LLM_BASE_URL="https://api.openai.com/v1"  # or any OpenAI-compatible endpoint
export LLM_MODEL="gpt-4o"
```

## Input Format

The planner accepts:

- **terms**: List of `{"term": str, "definition": str, "page": int}`
- **relationships**: List of `{"source": str, "target": str, "relation_type": str}`
- **graph**: `{"nodes": [...], "edges": [...]}`
- **summaries**: List of `{"section": str, "summary": str}`
- **mindmap**: `{"title": str, "children": [...]}`

## Output

```json
{
  "title": "第四章学习路线",
  "total_steps": 5,
  "estimated_time": "45 min",
  "steps": [
    {
      "order": 1,
      "title": "基础概念",
      "concepts": ["编码", "译码"],
      "estimated_time": "10 min",
      "difficulty": "easy",
      "key_points": [...]
    }
  ],
  "prerequisites": [
    {"source": "编码", "target": "选择性定律", "reason": "...", "strength": 0.8}
  ],
  "layers": [["编码", "译码"], ["选择性定律"], ...]
}
```

## Testing

```bash
pytest tests/ -v
```

## License

MIT
