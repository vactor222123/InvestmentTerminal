"""
Stable public OpenAPI fragments for the grounded AI server route.

These schemas describe only the external transport contract. Internal
application/provider types are intentionally excluded.
"""

GROUNDED_AI_REQUEST_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "request_id",
        "query",
    ],
    "properties": {
        "request_id": {
            "type": "string",
            "minLength": 1,
        },
        "query": {
            "type": "string",
            "minLength": 1,
        },
        "subjects": {
            "type": "array",
            "items": {
                "type": "string",
                "minLength": 1,
            },
            "uniqueItems": True,
            "default": [],
        },
        "max_items": {
            "type": "integer",
            "minimum": 1,
        },
    },
}

GROUNDED_AI_SUCCESS_SCHEMA = {
    "type": "object",
    "required": [
        "status",
        "request_id",
        "data",
    ],
    "properties": {
        "status": {
            "type": "string",
            "enum": ["SUCCESS"],
        },
        "request_id": {
            "type": "string",
        },
        "data": {
            "type": "object",
            "additionalProperties": True,
        },
    },
}

GROUNDED_AI_ERROR_SCHEMA = {
    "type": "object",
    "required": [
        "status",
        "error",
    ],
    "properties": {
        "status": {
            "type": "string",
            "enum": ["ERROR"],
        },
        "request_id": {
            "type": "string",
        },
        "error": {
            "type": "object",
            "required": [
                "category",
                "code",
                "message",
            ],
            "properties": {
                "category": {
                    "type": "string",
                },
                "code": {
                    "type": "string",
                },
                "message": {
                    "type": "string",
                },
            },
        },
    },
}


def grounded_ai_openapi_extra() -> dict:
    return {
        "requestBody": {
            "required": True,
            "content": {
                "application/json": {
                    "schema": GROUNDED_AI_REQUEST_SCHEMA,
                }
            },
        },
        "responses": {
            "200": {
                "description": "Grounded AI response",
                "content": {
                    "application/json": {
                        "schema": GROUNDED_AI_SUCCESS_SCHEMA,
                    }
                },
            },
            "400": {
                "description": "Invalid request",
                "content": {
                    "application/json": {
                        "schema": GROUNDED_AI_ERROR_SCHEMA,
                    }
                },
            },
            "401": {
                "description": "Authentication required",
                "content": {
                    "application/json": {
                        "schema": GROUNDED_AI_ERROR_SCHEMA,
                    }
                },
            },
            "403": {
                "description": "Policy denied",
                "content": {
                    "application/json": {
                        "schema": GROUNDED_AI_ERROR_SCHEMA,
                    }
                },
            },
            "413": {
                "description": "Request body too large",
                "content": {
                    "application/json": {
                        "schema": GROUNDED_AI_ERROR_SCHEMA,
                    }
                },
            },
            "500": {
                "description": "Internal server error",
                "content": {
                    "application/json": {
                        "schema": GROUNDED_AI_ERROR_SCHEMA,
                    }
                },
            },
            "503": {
                "description": "Execution unavailable",
                "content": {
                    "application/json": {
                        "schema": GROUNDED_AI_ERROR_SCHEMA,
                    }
                },
            },
        },
    }
