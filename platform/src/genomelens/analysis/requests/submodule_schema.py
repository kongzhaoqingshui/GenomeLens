"""SubmoduleRequest JSON schema(结构) 定义"""

# region import
from __future__ import annotations

from copy import deepcopy

# endregion


SUBMODULE_REQUEST_JSON_SCHEMA: dict[str, object] = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "$id": "https://genomelens.local/schemas/submodule-request.schema.json",
    "title": "GenomeLens SubmoduleRequest",
    "type": "object",
    "required": ["schema_version", "kind", "module_id", "output"],
    "additionalProperties": False,
    "properties": {
        "schema_version": {"type": "integer", "const": 3},
        "kind": {"type": "string", "const": "submodule_request"},
        "module_id": {"type": "string", "minLength": 1},
        "inputs": {"type": "object", "default": {}},
        "parameters": {"type": "object", "default": {}},
        "output": {"$ref": "#/$defs/output"},
        "runtime": {"$ref": "#/$defs/runtime"},
    },
    "$defs": {
        "output": {
            "type": "object",
            "required": ["directory"],
            "additionalProperties": False,
            "properties": {
                "directory": {"type": "string", "minLength": 1},
                "force": {"type": "boolean", "default": False},
                "formats": {"type": "array", "items": {"type": "string"}, "default": ["svg"]},
            },
        },
        "runtime": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "project_config": {"type": "string", "default": ""},
                "engine_config": {"type": "string", "default": ""},
                "jcvi_engine": {"type": "string", "default": ""},
                "blastn": {"type": "string", "default": ""},
                "makeblastdb": {"type": "string", "default": ""},
                "lastal": {"type": "string", "default": ""},
                "lastdb": {"type": "string", "default": ""},
                "threads": {"type": ["integer", "null"], "minimum": 1, "default": None},
                "min_block_size": {"type": ["integer", "null"], "minimum": 1, "default": None},
                "log_level": {"type": "string", "default": "INFO"},
                "verbose": {"type": "boolean", "default": False},
                "console_log": {"type": "boolean", "default": False},
            },
        },
    },
}


def submodule_request_json_schema() -> dict[str, object]:
    """返回 SubmoduleRequest JSON schema 的副本"""

    return deepcopy(SUBMODULE_REQUEST_JSON_SCHEMA)


__all__ = ["SUBMODULE_REQUEST_JSON_SCHEMA", "submodule_request_json_schema"]
