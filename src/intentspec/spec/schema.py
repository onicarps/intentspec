"""
intent.yaml v1 JSON Schema.

Complete schema with types, enums, patterns, and constraints.
Validated by jsonschema (draft-07) in the validate command.
"""

INTENT_SCHEMA_V1 = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "$id": "https://intentspec.dev/schema/v1/intent.json",
    "title": "intent.yaml v1.0",
    "description": "IntentSpec v1 schema — documents agent intent as code",
    "type": "object",
    "additionalProperties": False,
    "required": ["version", "agent", "intent"],

    "properties": {
        "version": {
            "type": "string",
            "const": "1.0",
            "description": "Format version. Must be '1.0'.",
        },

        "agent": {
            "type": "object",
            "additionalProperties": False,
            "required": ["name", "type", "description"],
            "description": "Agent identity block.",
            "properties": {
                "name": {
                    "type": "string",
                    "pattern": "^[a-z][a-z0-9-]*$",
                    "minLength": 1,
                    "maxLength": 64,
                    "description": "Unique agent identifier. kebab-case.",
                },
                "type": {
                    "type": "string",
                    "enum": ["coding", "research", "service", "data", "coordinator", "custom"],
                    "description": "Agent type classification.",
                },
                "description": {
                    "type": "string",
                    "minLength": 1,
                    "maxLength": 200,
                    "description": "Human-readable agent description. ≤200 chars.",
                },
            },
        },

        "intent": {
            "type": "object",
            "additionalProperties": False,
            "description": "Intent specification block.",
            "properties": {
                "goals": {
                    "type": "array",
                    "description": "What the agent is trying to achieve.",
                    "items": {
                        "type": "object",
                        "additionalProperties": False,
                        "required": ["description"],
                        "properties": {
                            "description": {
                                "type": "string",
                                "minLength": 10,
                                "maxLength": 500,
                                "description": "Goal description. 10-500 chars.",
                            },
                            "priority": {
                                "type": "string",
                                "enum": ["high", "medium", "low"],
                                "default": "medium",
                                "description": "Goal priority.",
                            },
                            "success_criteria": {
                                "type": "string",
                                "minLength": 10,
                                "maxLength": 500,
                                "description": "How to measure this goal. 10-500 chars.",
                            },
                        },
                    },
                },

                "constraints": {
                    "type": "array",
                    "description": "Rules the agent must follow.",
                    "items": {
                        "type": "object",
                        "additionalProperties": False,
                        "required": ["rule", "enforceable"],
                        "properties": {
                            "rule": {
                                "type": "string",
                                "minLength": 5,
                                "maxLength": 500,
                                "description": "The rule text. 5-500 chars.",
                            },
                            "enforceable": {
                                "type": "boolean",
                                "description": "true = auto-checkable, false = human judgment.",
                            },
                        },
                    },
                },

                "non_negotiables": {
                    "type": "array",
                    "description": "Hard boundaries the agent must never cross.",
                    "items": {
                        "type": "object",
                        "additionalProperties": False,
                        "required": ["rule", "severity"],
                        "properties": {
                            "rule": {
                                "type": "string",
                                "minLength": 5,
                                "maxLength": 500,
                                "description": "The rule text. 5-500 chars.",
                            },
                            "severity": {
                                "type": "string",
                                "enum": ["hard", "soft"],
                                "description": "hard = CI fail, soft = CI warning.",
                            },
                        },
                    },
                },

                "tools": {
                    "type": "object",
                    "additionalProperties": False,
                    "description": "Tool permissions with rationale.",
                    "properties": {
                        "allowed": {
                            "type": "array",
                            "description": "Tools the agent CAN use.",
                            "items": {
                                "type": "object",
                                "additionalProperties": False,
                                "required": ["name", "rationale"],
                                "properties": {
                                    "name": {
                                        "type": "string",
                                        "minLength": 1,
                                        "maxLength": 128,
                                        "description": "Tool name.",
                                    },
                                    "rationale": {
                                        "type": "string",
                                        "minLength": 5,
                                        "maxLength": 500,
                                        "description": "WHY this tool is needed. 5-500 chars.",
                                    },
                                },
                            },
                        },
                        "denied": {
                            "type": "array",
                            "description": "Tools the agent CANNOT use.",
                            "items": {
                                "type": "object",
                                "additionalProperties": False,
                                "required": ["name", "rationale"],
                                "properties": {
                                    "name": {
                                        "type": "string",
                                        "minLength": 1,
                                        "maxLength": 128,
                                        "description": "Tool name.",
                                    },
                                    "rationale": {
                                        "type": "string",
                                        "minLength": 5,
                                        "maxLength": 500,
                                        "description": "WHY this tool is forbidden. 5-500 chars.",
                                    },
                                },
                            },
                        },
                    },
                },

                "boundaries": {
                    "type": "array",
                    "description": "Scope boundaries.",
                    "items": {
                        "type": "object",
                        "additionalProperties": False,
                        "required": ["scope", "out_of_scope"],
                        "properties": {
                            "scope": {
                                "type": "string",
                                "minLength": 5,
                                "maxLength": 500,
                                "description": "What's in scope. 5-500 chars.",
                            },
                            "out_of_scope": {
                                "type": "string",
                                "minLength": 5,
                                "maxLength": 500,
                                "description": "What's explicitly out. 5-500 chars.",
                            },
                        },
                    },
                },

                "escalation": {
                    "type": "object",
                    "additionalProperties": False,
                    "description": "Escalation protocol.",
                    "properties": {
                        "trigger": {
                            "type": "string",
                            "minLength": 5,
                            "maxLength": 500,
                            "description": "When to escalate. 5-500 chars.",
                        },
                        "method": {
                            "type": "string",
                            "minLength": 5,
                            "maxLength": 500,
                            "description": "How to escalate. 5-500 chars.",
                        },
                    },
                },

                "failure_modes": {
                    "type": "array",
                    "description": "Known ways this agent can fail.",
                    "items": {
                        "type": "object",
                        "additionalProperties": False,
                        "required": ["mode", "mitigation"],
                        "properties": {
                            "mode": {
                                "type": "string",
                                "minLength": 5,
                                "maxLength": 500,
                                "description": "Failure mode description. 5-500 chars.",
                            },
                            "mitigation": {
                                "type": "string",
                                "minLength": 5,
                                "maxLength": 500,
                                "description": "How to mitigate. 5-500 chars.",
                            },
                        },
                    },
                },

                "sub_agents": {
                    "type": "array",
                    "description": "Child agent names. Reserved for Phase 4.",
                    "items": {
                        "type": "string",
                        "pattern": "^[a-z][a-z0-9-]*$",
                    },
                },

                "extends": {
                    "type": "string",
                    "description": "Path to parent intent.yaml. Reserved for Phase 4.",
                },
            },
        },

        "metadata": {
            "type": "object",
            "additionalProperties": False,
            "description": "Provenance and lifecycle.",
            "properties": {
                "status": {
                    "type": "string",
                    "enum": ["draft", "active", "deprecated"],
                    "default": "draft",
                    "description": "Lifecycle status.",
                },
                "owner": {
                    "type": "string",
                    "minLength": 1,
                    "maxLength": 200,
                    "description": "Team/person accountable.",
                },
                "created": {
                    "type": "string",
                    "format": "date-time",
                    "description": "ISO-8601 creation timestamp.",
                },
                "updated": {
                    "type": "string",
                    "format": "date-time",
                    "description": "ISO-8601 last update timestamp.",
                },
                "review_cycle": {
                    "type": "string",
                    "enum": ["weekly", "monthly", "quarterly"],
                    "default": "monthly",
                    "description": "How often this spec should be reviewed.",
                },
                "tags": {
                    "type": "array",
                    "description": "Free-form tags for categorization.",
                    "items": {
                        "type": "string",
                        "minLength": 1,
                        "maxLength": 50,
                    },
                },
            },
        },
    },
}
