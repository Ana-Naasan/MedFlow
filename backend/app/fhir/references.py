"""Rewrite Synthea urn:uuid references to stable ResourceType/id references.

Synthea (and some other synthetic-data pipelines) emits internal references
as ``urn:uuid:<uuid>`` strings.  *MedFlow* needs every citation to stay stable
across pipeline runs, so we rewrite those UUID references to the permanent
``ResourceType/id`` assigned during ingestion.

Usage
-----
>>> id_map = {"urn:uuid:abc-123": "Patient/p1", "urn:uuid:def-456": "Condition/c1"}
>>> resource = {
...     "resourceType": "Observation",
...     "id": "obs-1",
...     "subject": {"reference": "urn:uuid:abc-123"},
...     "code": {"coding": [{"code": "x"}]},
... }
>>> resolved = resolve_references(resource, id_map)
>>> resolved["subject"]["reference"]
'Patient/p1'
"""

from typing import Any


def _walk_and_replace(obj: Any, id_map: dict[str, str]) -> Any:
    """Recursively walk a FHIR resource dict and replace ``urn:uuid:…`` references.

    Parameters
    ----------
    obj : Any
        A FHIR resource as a nested dict (or a fragment thereof).
    id_map : dict[str, str]
        Mapping from ``urn:uuid:<uuid>`` → ``ResourceType/id``.

    Returns
    -------
    Any
        A new structure with all matched references rewritten.  Unmatched
        ``urn:uuid:…`` values are **left untouched** so they can be detected
        by downstream validation.
    """
    if isinstance(obj, dict):
        new = {}
        for key, value in obj.items():
            if key == "reference" and isinstance(value, str) and value in id_map:
                new[key] = id_map[value]
            else:
                new[key] = _walk_and_replace(value, id_map)
        return new
    if isinstance(obj, list):
        return [_walk_and_replace(item, id_map) for item in obj]
    return obj


def resolve_references(
    resource: dict[str, Any],
    id_map: dict[str, str],
) -> dict[str, Any]:
    """Rewrite any mapped ``urn:uuid:…`` reference strings within *resource*.

    If *id_map* is empty or *resource* is not a dict, *resource* is returned unchanged.

    Parameters
    ----------
    resource : Any
        A raw FHIR resource dictionary (e.g. parsed from JSON) or a nested fragment.
        Non-dict values are returned unchanged.
    id_map : dict[str, str]
        Mapping from ``urn:uuid:<uuid>`` → ``ResourceType/id``.

    Returns
    -------
    Any
        A new structure with each ``reference`` value rewritten when it matches a key in
        *id_map*. (Dict/list nodes are rebuilt recursively; the input is not mutated.)
    Example
    -------
    >>> id_map = {"urn:uuid:bogus-uuid": "Patient/p1"}
    >>> resolve_references(
    ...     {"subject": {"reference": "urn:uuid:bogus-uuid"}},
    ...     id_map,
    ... )
    {'subject': {'reference': 'Patient/p1'}}
    """
    # Fast path: nothing to resolve.
    if not id_map or not isinstance(resource, dict):
        return resource

    return _walk_and_replace(resource, id_map)
