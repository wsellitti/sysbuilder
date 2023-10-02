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
                            "pattern": "[0-9]+([KMGTP]|$)",
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
                    "contains": {
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
                                    },
                                    "label": {
                                        "type": "string",
                                    },
                                    "label_flag": {
                                        "type": "string",
                                    },
                                    "args": {
                                        "type": "array",
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
