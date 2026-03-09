## Summary

{{ summary }}

## Spec References

{% if spec_refs %}{% for ref in spec_refs %}- {{ ref }}
{% endfor %}{% else %}_No spec references found._
{% endif %}

## Task References

{% if task_refs %}{% for ref in task_refs %}- {{ ref }}
{% endfor %}{% else %}_No task references found._
{% endif %}

## AI Provenance

- **Total commits**: {{ total_commits }}
- **AI-authored**: {{ ai_commits }} ({{ ai_percentage }}%)
- **Human-edited**: {{ edited_commits }}
- **Agents used**: {{ agents_list }}

## Pipeline Status

| Stage | Status |
|-------|--------|
{% for stage, status in pipeline_status.items() %}| {{ stage }} | {{ status }} |
{% endfor %}

## Commits

{% for c in commits %}- [`{{ c.short_sha }}`] {{ c.subject }}{% if c.is_ai_authored %} 🤖{% endif %}{% if c.is_human_edited %} ✏️{% endif %}
{% endfor %}
