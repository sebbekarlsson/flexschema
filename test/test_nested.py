# pyright: basic
from .utils import load_sample
from flexschema.schema.schema import ESchemaType, parse

def test_nested():
    data = load_sample('nested.json')
    schema = parse(data)

    assert schema.type == ESchemaType.OBJECT
