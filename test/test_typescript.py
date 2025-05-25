# pyright: basic
from .utils import load_sample
from flexschema.schema.schema import ESchemaType, parse
from flexschema.translate.typescript.translate import translate

def test_nested():
    print('')
    data = load_sample('nested.json')
    schema = parse(data)

    code = translate(schema)
    print(code)
