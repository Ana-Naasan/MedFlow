from collections.abc import Iterable


def flatten_markdown(resources: Iterable[dict[str, object]]) -> str:
    """Render a small deterministic markdown view of resource dictionaries."""
    lines: list[str] = []
    for resource in resources:
        resource_type = str(resource.get("resourceType", "Resource"))
        resource_id = str(resource.get("id", "unknown"))
        lines.append(f"## [{resource_type}/{resource_id}]")
        for key in sorted(resource):
            value = resource[key]
            lines.append(f"- {key}: {value}")
    return "\n".join(lines)
