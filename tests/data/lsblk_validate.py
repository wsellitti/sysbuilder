"""
The dictionary to test lsblk output against. Hardware commands are dependent
on the system doing the testing so this is a simple check to make sure the
important keys are present and of the right value.
"""

blockdev_properties = {
    "alignment": {
        "type": "integer",
    },
    "id-link": {
        "type": "string",
    },
    "id": {
        "type": "string",
    },
    "disc-aln": {
        "type": "integer",
    },
    "dax": {
        "type": "boolean",
    },
    "disc-gran": {
        "type": "string",
    },
    "disk-seq": {
        "type": "integer",
    },
    "disc-max": {
        "type": "string",
    },
    "disc-zero": {
        "type": "boolean",
    },
    "fsavail": {
        "type": [
            "string",
            "null",
        ]
    },
    "fsroots": {
        "type": "array",
        "items": {
            "type": [
                "string",
                "null",
            ],
        },
    },
    "fssize": {
        "type": [
            "string",
            "null",
        ],
    },
    "fstype": {
        "type": [
            "string",
            "null",
        ],
    },
    "fsused": {
        "type": [
            "string",
            "null",
        ],
    },
    "fsuse%": {
        "type": [
            "string",
            "null",
        ],
    },
    "fsver": {
        "type": [
            "string",
            "null",
        ],
    },
    "group": {
        "type": "string",
    },
    "hctl": {
        "type": [
            "string",
            "null",
        ],
    },
    "hotplug": {
        "type": "boolean",
    },
    "kname": {
        "type": "string",
    },
    "label": {
        "type": [
            "string",
            "null",
        ],
    },
    "log-sec": {
        "type": "integer",
    },
    "maj:min": {
        "type": "string",
    },
    "min-io": {
        "type": "integer",
    },
    "mode": {
        "type": "string",
    },
    "model": {
        "type": [
            "string",
            "null",
        ],
    },
    "mq": {
        "type": "string",
    },
    "name": {
        "type": "string",
    },
    "opt-io": {
        "type": "integer",
    },
    "owner": {
        "type": "string",
    },
    "partflags": {
        "type": [
            "string",
            "null",
        ],
    },
    "partlabel": {
        "type": [
            "string",
            "null",
        ],
    },
    "partn": {
        "type": [
            "integer",
            "null",
        ],
    },
    "parttype": {
        "type": [
            "string",
            "null",
        ],
    },
    "parttypename": {
        "type": [
            "string",
            "null",
        ],
    },
    "partuuid": {
        "type": [
            "string",
            "null",
        ],
    },
    "path": {
        "type": "string",
    },
    "phy-sec": {
        "type": "integer",
    },
    "pkname": {
        "type": [
            "string",
            "null",
        ],
    },
    "pttype": {
        "type": [
            "string",
            "null",
        ],
    },
    "ptuuid": {
        "type": [
            "string",
            "null",
        ],
    },
    "ra": {
        "type": "integer",
    },
    "rand": {
        "type": "boolean",
    },
    "rev": {
        "type": [
            "string",
            "null",
        ],
    },
    "rm": {
        "type": "boolean",
    },
    "ro": {
        "type": "boolean",
    },
    "rota": {
        "type": "boolean",
    },
    "rq-size": {
        "type": [
            "integer",
            "null",
        ],
    },
    "sched": {
        "type": [
            "string",
            "null",
        ],
    },
    "serial": {
        "type": [
            "string",
            "null",
        ],
    },
    "size": {
        "type": "string",
    },
    "start": {
        "type": [
            "integer",
            "null",
        ]
    },
    "state": {
        "type": [
            "string",
            "null",
        ],
    },
    "subsystems": {
        "type": "string",
    },
    "mountpoint": {
        "type": [
            "string",
            "null",
        ],
    },
    "mountpoints": {
        "type": "array",
        "items": {
            "type": [
                "string",
                "null",
            ],
        },
    },
    "tran": {
        "type": [
            "string",
            "null",
        ],
    },
    "type": {
        "type": "string",
    },
    "uuid": {
        "type": [
            "string",
            "null",
        ],
    },
    "vendor": {
        "type": [
            "string",
            "null",
        ],
    },
    "wsame": {
        "type": "string",
    },
    "wwn": {
        "type": [
            "string",
            "null",
        ],
    },
    "zoned": {
        "type": "string",
    },
    "zone-sz": {
        "type": "string",
    },
    "zone-wgran": {
        "type": "string",
    },
    "zone-app": {
        "type": "string",
    },
    "zone-nr": {
        "type": "integer",
    },
    "zone-omax": {
        "type": "integer",
    },
    "zone-amax": {
        "type": "integer",
    },
    "children": {
        "type": "array",
        "items": {
            "type": [
                "null",
                "object",
            ],
        },
    },
}

blockdev_required_properties = [
    "alignment",
    "disc-aln",
    "dax",
    "disc-gran",
    "disc-max",
    "disc-zero",
    "fsavail",
    "fsroots",
    "fssize",
    "fstype",
    "fsused",
    "fsuse%",
    "fsver",
    "group",
    "hctl",
    "hotplug",
    "kname",
    "label",
    "log-sec",
    "maj:min",
    "min-io",
    "mode",
    "model",
    "name",
    "opt-io",
    "owner",
    "partflags",
    "partlabel",
    "parttype",
    "parttypename",
    "partuuid",
    "path",
    "phy-sec",
    "pkname",
    "pttype",
    "ptuuid",
    "ra",
    "rand",
    "rev",
    "rm",
    "ro",
    "rota",
    "rq-size",
    "sched",
    "serial",
    "size",
    "state",
    "subsystems",
    "mountpoint",
    "mountpoints",
    "tran",
    "type",
    "uuid",
    "vendor",
    "wsame",
    "wwn",
    "zoned",
]

validate_json = {
    "type": "array",
    "minItems": 1,
    "items": {
        "type": "object",
        "properties": blockdev_properties,
        "required": blockdev_required_properties,
    },
}
