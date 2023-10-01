"""
The dictionary used to validate the config.json
"""

validate_json = {
    "type": "object",
    "properties": {
        "storage": {
            "type": "object",
            "properties": {
                "disk": {
                    "type": "object",
                    "properties": {
                        "ptable": {"type": "string", "enum": ["gpt"]},
                        "path": {"type": "string"},
                        "type": {
                            "type": "string",
                            "enum": ["physical", "sparse", "raw"],
                        },
                        "size": {
                            "type": "string",
                            "pattern": "[0-9]+([KMGTP]|$)",
                        },
                    },
                    "required": ["path", "ptable", "type"],
                },
                "layout": {"type": "array", "minItems": 1, "maxItems": 128},
            },
            "required": ["disk", "layout"],
        },
        "install": {"type": "object"},
    },
    "required": ["storage", "install"],
}
