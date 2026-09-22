from typing import Type, get_args, get_origin
from pydantic import BaseModel

def pydantic_to_gbnf(schema: Type[BaseModel]) -> str:
    """
    Translates a Pydantic BaseModel into a GBNF grammar.
    This is a simplified implementation for the MVP.
    """
    rules = []

    # Root rule
    rules.append('root ::= object')

    # Basic object definition
    # This is a simplified version. A real GBNF generator for JSON
    # would be more comprehensive.
    fields = schema.model_fields
    field_rules = []

    for name, field in fields.items():
        # Determine the GBNF type for this field
        field_type = field.annotation
        origin = get_origin(field_type)
        args = get_args(field_type)

        if origin is list:
            type_str = f"list_{name}"
            rules.append(f"{type_str} ::= '[' [ {type_str} ',' ]* value ']'")
        elif origin is dict:
            type_str = f"dict_{name}"
            rules.append(f"{type_str} ::= '{{' [ {type_str} ',' ]* '}}'")
        elif field_type is str:
            type_str = "string"
        elif field_type is int:
            type_str = "number"
        else:
            type_str = "string" # Default to string for MVP

        field_rules.append(f'"{name}": {type_str}')

    # Construct the object rule
    object_rule = 'object ::= "{" + (", ".join(field_rules)) + "}"'
    # In GBNF, this needs to be formatted as specific sequences
    # This is a high-level representation.

    # For the MVP, we will provide a valid GBNF structure that constraints
    # the output to a JSON object containing the required keys.

    field_constraints = [f'"{k}": string' for k in fields.keys()]
    gbnf = f"root ::= object\n"
    gbnf += f"object ::= \"{{\" {' '.join(field_constraints)} \"}}\"\n"
    gbnf += f"string ::= \"[^\"]*\""

    return gbnf
