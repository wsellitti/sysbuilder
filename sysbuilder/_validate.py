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
                        "ptable": {
                            "type": "string",
                            "enum": [
                                "gpt",
                            ],
                        },
                        "path": {"type": "string"},
                        "type": {
                            "type": "string",
                            "enum": [
                                "physical",
                                "sparse",
                                "raw",
                            ],
                        },
                        "size": {
                            "type": "string",
                            "pattern": "[0-9]+[MGTP]",
                        },
                    },
                    "required": [
                        "path",
                        "ptable",
                        "type",
                    ],
                },
                "layout": {
                    "type": "array",
                    "minItems": 1,
                    "maxItems": 128,
                    "items": {
                        "type": "object",
                        "properties": {
                            "start": {
                                "type": "string",
                            },
                            "end": {"type": "string"},
                            "typecode": {
                                "type": "string",
                            },
                            "filesystem": {
                                "type": "object",
                                "required": [
                                    "type",
                                    "mountpoint",
                                ],
                                "properties": {
                                    "type": {
                                        "type": "string",
                                    },
                                    "mountpoint": {
                                        "type": "string",
                                        "pattern": r"^(/.*|swap)",
                                    },
                                    "label": {
                                        "type": "string",
                                    },
                                    "label_flag": {
                                        "type": "string",
                                    },
                                    "args": {
                                        "type": "array",
                                        "items": {
                                            "type": "string",
                                        },
                                    },
                                },
                            },
                        },
                        "required": [
                            "start",
                            "end",
                            "typecode",
                            "filesystem",
                        ],
                    },
                },
            },
            "required": [
                "disk",
                "layout",
            ],
        },
        "install": {
            "type": "object",
        },
    },
    "required": [
        "storage",
        "install",
    ],
}
