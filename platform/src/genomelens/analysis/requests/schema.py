"""AnalysisRequest JSON schema(结构) 定义"""

# region import
from __future__ import annotations

from copy import deepcopy

# endregion


# region schema 定义
ANALYSIS_REQUEST_JSON_SCHEMA: dict[str, object] = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "$id": "https://genomelens.local/schemas/analysis-request.schema.json",
    "title": "GenomeLens AnalysisRequest",
    "type": "object",
    "required": ["schema_version", "kind", "method", "input", "output"],
    "additionalProperties": False,
    "properties": {
        "schema_version": {
            "type": "integer",
            "const": 1,
        },
        "kind": {
            "type": "string",
            "const": "analysis_request",
        },
        "method": {
            "type": "string",
            "enum": ["mcscan"],
        },
        "input": {
            "$ref": "#/$defs/input",
        },
        "output": {
            "$ref": "#/$defs/output",
        },
        "config": {
            "$ref": "#/$defs/config_ref",
        },
        "options": {
            "$ref": "#/$defs/options",
        },
        "method_config": {
            "$ref": "#/$defs/mcscan_method_config",
        },
    },
    "$defs": {
        "input": {
            "type": "object",
            "required": ["mode"],
            "additionalProperties": False,
            "properties": {
                "mode": {
                    "type": "string",
                    "enum": ["auto_directory", "bed_cds", "gff_genome"],
                },
                "directory": {
                    "type": "string",
                    "default": "",
                },
                "species": {
                    "type": "array",
                    "items": {
                        "$ref": "#/$defs/species_input",
                    },
                    "default": [],
                },
                "reference_index": {
                    "type": "integer",
                    "minimum": 0,
                    "default": 0,
                },
            },
        },
        "species_input": {
            "type": "object",
            "required": ["name", "input_mode"],
            "additionalProperties": False,
            "properties": {
                "name": {
                    "type": "string",
                    "minLength": 1,
                },
                "input_mode": {
                    "type": "string",
                    "enum": ["bed_cds", "gff_genome"],
                },
                "bed": {
                    "type": "string",
                    "default": "",
                },
                "cds": {
                    "type": "string",
                    "default": "",
                },
                "gff": {
                    "type": "string",
                    "default": "",
                },
                "genome": {
                    "type": "string",
                    "default": "",
                },
            },
        },
        "output": {
            "type": "object",
            "required": ["directory"],
            "additionalProperties": False,
            "properties": {
                "directory": {
                    "type": "string",
                    "minLength": 1,
                },
                "force": {
                    "type": "boolean",
                    "default": False,
                },
                "formats": {
                    "type": "array",
                    "items": {
                        "type": "string",
                    },
                    "default": ["svg"],
                },
            },
        },
        "config_ref": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "project_config": {
                    "type": "string",
                    "default": "",
                },
                "method_config": {
                    "type": "string",
                    "default": "",
                },
            },
        },
        "options": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "preset": {
                    "type": "string",
                    "default": "auto",
                },
                "threads": {
                    "type": ["integer", "null"],
                    "minimum": 1,
                    "default": None,
                },
                "min_block_size": {
                    "type": ["integer", "null"],
                    "minimum": 1,
                    "default": None,
                },
            },
        },
        "mcscan_method_config": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "workflow": {
                    "type": "string",
                    "default": "graphics_synteny",
                },
                "jcvi_engine": {
                    "type": "string",
                    "default": "",
                },
                "blastn": {
                    "type": "string",
                    "default": "",
                },
                "makeblastdb": {
                    "type": "string",
                    "default": "",
                },
                "jcvi_layout": {
                    "type": "string",
                    "default": "",
                },
                "jcvi_seqids": {
                    "type": "string",
                    "default": "",
                },
                "allow_simplified_fallback": {
                    "type": "boolean",
                    "default": False,
                },
                "align_soft": {
                    "type": "string",
                    "enum": ["blast", "last", "diamond_blastp"],
                    "default": "blast",
                },
                "dbtype": {
                    "type": "string",
                    "enum": ["nucl", "prot"],
                    "default": "nucl",
                },
                "cscore": {
                    "type": "number",
                    "default": 0.7,
                },
                "dist": {
                    "type": "integer",
                    "minimum": 1,
                    "default": 20,
                },
                "iter": {
                    "type": "integer",
                    "minimum": 1,
                    "default": 1,
                },
                "target_gene_ids": {
                    "type": "array",
                    "items": {
                        "type": "string",
                    },
                    "default": [],
                },
                "up": {
                    "type": "integer",
                    "minimum": 0,
                    "default": 20,
                },
                "down": {
                    "type": "integer",
                    "minimum": 0,
                    "default": 20,
                },
                "split_targets": {
                    "type": "boolean",
                    "default": False,
                },
                "label_targets": {
                    "type": "boolean",
                    "default": False,
                },
                "glyphstyle": {
                    "type": "string",
                    "default": "",
                },
                "glyphcolor": {
                    "type": "string",
                    "default": "",
                },
                "shadestyle": {
                    "type": "string",
                    "default": "",
                },
                "figsize": {
                    "type": "string",
                    "default": "",
                },
                "dpi": {
                    "type": "integer",
                    "minimum": 1,
                    "default": 300,
                },
            },
        },
    },
}

# endregion


# region 对外函数
def analysis_request_json_schema() -> dict[str, object]:
    """返回 AnalysisRequest JSON schema 的副本"""

    return deepcopy(ANALYSIS_REQUEST_JSON_SCHEMA)


# endregion
