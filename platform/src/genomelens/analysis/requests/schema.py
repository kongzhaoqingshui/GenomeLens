"""WorkflowRequest JSON schema(结构) 定义"""

# region import
from __future__ import annotations

from copy import deepcopy

# endregion


# region schema 定义
WORKFLOW_REQUEST_JSON_SCHEMA: dict[str, object] = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "$id": "https://genomelens.local/schemas/workflow-request.schema.json",
    "title": "GenomeLens WorkflowRequest",
    "type": "object",
    "required": ["schema_version", "kind", "workflow_id", "output"],
    "additionalProperties": False,
    "properties": {
        "schema_version": {"type": "integer", "const": 2},
        "kind": {"type": "string", "const": "workflow_request"},
        "workflow_id": {
            "type": "string",
            "enum": ["synteny", "local_synteny", "graphics_histogram", "graphics_heatmap"],
        },
        "species": {"type": "array", "items": {"$ref": "#/$defs/species_input"}, "default": []},
        "reference_index": {"type": "integer", "minimum": 0, "default": 0},
        "inputs": {"type": "object", "default": {}},
        "parameters": {"$ref": "#/$defs/parameters"},
        "output": {"$ref": "#/$defs/output"},
        "runtime": {"$ref": "#/$defs/runtime"},
    },
    "$defs": {
        "species_input": {
            "type": "object",
            "required": ["name", "input_mode"],
            "additionalProperties": False,
            "properties": {
                "name": {"type": "string", "minLength": 1},
                "input_mode": {"type": "string", "enum": ["bed_cds", "gff_genome"]},
                "bed": {"type": "string", "default": ""},
                "cds": {"type": "string", "default": ""},
                "gff": {"type": "string", "default": ""},
                "genome": {"type": "string", "default": ""},
            },
        },
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
        "parameters": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "synteny": {"$ref": "#/$defs/synteny_parameters"},
                "local_synteny": {"$ref": "#/$defs/local_synteny_parameters"},
                "plot": {"$ref": "#/$defs/plot_parameters"},
                "histogram": {"$ref": "#/$defs/histogram_parameters"},
                "heatmap": {"$ref": "#/$defs/heatmap_parameters"},
                "extras": {"type": "object", "default": {}},
            },
            "default": {},
        },
        "synteny_parameters": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "align_soft": {"type": "string", "enum": ["blast", "last", "diamond_blastp"], "default": "blast"},
                "dbtype": {"type": "string", "enum": ["nucl", "prot"], "default": "nucl"},
                "cscore": {"type": "number", "default": 0.7},
                "dist": {"type": "integer", "minimum": 1, "default": 20},
                "iter": {"type": "integer", "minimum": 1, "default": 1},
                "allow_simplified_fallback": {"type": "boolean", "default": False},
            },
        },
        "local_synteny_parameters": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "target_gene_ids": {"type": "array", "items": {"type": "string"}, "default": []},
                "up": {"type": "integer", "minimum": 0, "default": 20},
                "down": {"type": "integer", "minimum": 0, "default": 20},
                "split_targets": {"type": "boolean", "default": False},
                "label_targets": {"type": "boolean", "default": False},
                "use_native_renderer": {"type": "boolean", "default": False},
            },
        },
        "plot_parameters": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "glyphstyle": {"type": "string", "default": ""},
                "glyphcolor": {"type": "string", "default": ""},
                "shadestyle": {"type": "string", "default": ""},
                "figsize": {"type": "string", "default": ""},
                "dpi": {"type": "integer", "minimum": 1, "default": 300},
                "auto_optimization": {"type": "object", "default": {}},
            },
        },
        "histogram_parameters": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "inputs": {"type": "array", "items": {"type": "string"}, "default": []},
                "columns": {"type": "array", "items": {"type": "integer", "minimum": 0}, "default": [0]},
                "skip": {"type": "integer", "minimum": 0, "default": 0},
                "bins": {"type": "integer", "minimum": 1, "default": 20},
                "vmin": {"type": ["number", "null"], "default": 0.0},
                "vmax": {"type": ["number", "null"], "default": None},
                "xlabel": {"type": "string", "default": "value"},
                "title": {"type": "string", "default": ""},
                "base": {"type": "integer", "enum": [0, 2, 10], "default": 0},
                "facet": {"type": "boolean", "default": False},
                "fill": {"type": "string", "default": "white"},
            },
        },
        "heatmap_parameters": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "matrix": {"type": "string", "default": ""},
                "rowgroups": {"type": "string", "default": ""},
                "cmap": {"type": "string", "default": ""},
                "groups": {"type": "boolean", "default": False},
                "horizontalbar": {"type": "boolean", "default": False},
            },
        },
    },
}

# endregion


# region 对外函数
def analysis_request_json_schema() -> dict[str, object]:
    """返回 WorkflowRequest JSON schema 的副本"""

    return deepcopy(WORKFLOW_REQUEST_JSON_SCHEMA)


# endregion
