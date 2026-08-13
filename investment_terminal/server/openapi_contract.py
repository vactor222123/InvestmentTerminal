"""
Stable public OpenAPI fragments for the grounded AI server route.
"""

GROUNDED_AI_REQUEST_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["request_id", "query"],
    "properties": {
        "request_id": {"type": "string", "minLength": 1},
        "query": {"type": "string", "minLength": 1},
        "subjects": {
            "type": "array",
            "items": {"type": "string", "minLength": 1},
            "uniqueItems": True,
            "default": [],
        },
        "max_items": {"type": "integer", "minimum": 1},
    },
}

GROUNDED_AI_SUCCESS_SCHEMA = {
    "type": "object",
    "required": ["status", "request_id", "data"],
    "properties": {
        "status": {"type": "string", "enum": ["SUCCESS"]},
        "request_id": {"type": "string"},
        "data": {
            "type": "object",
            "additionalProperties": True,
        },
    },
}

GROUNDED_AI_ERROR_SCHEMA = {
    "type": "object",
    "required": ["status", "error"],
    "properties": {
        "status": {"type": "string", "enum": ["ERROR"]},
        "request_id": {"type": "string"},
        "error": {
            "type": "object",
            "required": ["category", "code", "message"],
            "properties": {
                "category": {"type": "string"},
                "code": {"type": "string"},
                "message": {"type": "string"},
            },
        },
    },
}


def _rate_limit_headers() -> dict:
    return {
        "RateLimit-Limit": {
            "description": "Configured token-bucket capacity",
            "schema": {
                "type": "integer",
                "minimum": 1,
            },
        },
        "RateLimit-Remaining": {
            "description": "Whole requests immediately admissible",
            "schema": {
                "type": "integer",
                "minimum": 0,
            },
        },
        "RateLimit-Reset": {
            "description": "Whole seconds until the bucket is full",
            "schema": {
                "type": "integer",
                "minimum": 0,
            },
        },
    }


def grounded_ai_openapi_extra() -> dict:
    error_content = {
        "application/json": {
            "schema": GROUNDED_AI_ERROR_SCHEMA,
        }
    }
    rate_limit_headers = _rate_limit_headers()
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
                "headers": rate_limit_headers,
                "content": {
                    "application/json": {
                        "schema": GROUNDED_AI_SUCCESS_SCHEMA,
                    }
                },
            },
            "400": {
                "description": "Invalid request",
                "headers": rate_limit_headers,
                "content": error_content,
            },
            "401": {
                "description": "Authentication required",
                "content": error_content,
            },
            "403": {
                "description": "Policy denied",
                "headers": rate_limit_headers,
                "content": error_content,
            },
            "413": {
                "description": "Request body too large",
                "headers": rate_limit_headers,
                "content": error_content,
            },
            "429": {
                "description": "Inbound request rate limit exceeded",
                "headers": {
                    **rate_limit_headers,
                    "Retry-After": {
                        "description": (
                            "Whole seconds until the next admission is expected"
                        ),
                        "schema": {
                            "type": "integer",
                            "minimum": 1,
                        },
                    },
                },
                "content": error_content,
            },
            "500": {
                "description": "Internal server error",
                "content": error_content,
            },
            "503": {
                "description": "Execution unavailable",
                "headers": rate_limit_headers,
                "content": error_content,
            },
        },
    }
