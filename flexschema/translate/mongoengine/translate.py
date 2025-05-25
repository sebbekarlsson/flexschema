# pyright: basic
from typing import Any
from flexschema.schema.schema import AnySchema, ESchemaType, SchemaBase, SchemaObject
from flexschema.translate.translation import Translation

def makepad(x: int) -> str:
    if x <= 0:
        return ''
    return ' ' * x

def pad_left(x: str, pad: int) -> str:
    return f'{makepad(pad)}{x}'

def _translate(schema: AnySchema, base_class: str = 'Document', extra_deps: list[str] | None = None) -> Translation:
    enums: list[str] = []
    classes: list[str] = []
    deps: set[str] = set()

    if extra_deps is not None:
        deps.update(extra_deps)

    if base_class == 'Document':
        deps.add('from mongoengine import Document')


    python_types:dict[str, str] = {
        'string': 'str',
        'number': 'float',
        'int': 'int',
        'integer': 'int',
        'StringField': 'str',
        'IntField': 'int',
        'FloatField': 'float'
    }

    def make_enum(name: str, keys: list[str]):
        ename = f'E{name.title()}'
        content = ''
        content += f'class {ename}(StrEnum):\n'
        content += '\n'.join(list(map(lambda x: f'{makepad(4)}{x} = "{x}"', keys)))
        enums.append(content)
        return ename

    def make_class(schema: SchemaObject):
        content = ''
        name = schema.key or f'SomeObject'
        name = name.replace(' ', '').title()
        content += ((f'class {name}({base_class}):') + '\n')
        for k, v in schema.properties.items():
            vstr = trans(v)
            mark = ':Any'
            if isinstance(v, SchemaBase):
                if v.type == ESchemaType.OBJECT:
                    mark = f":'{vstr}'"
                    vstr = f"ReferenceField('{vstr}')"
                    deps.add('from mongoengine import ReferenceField')
                elif v.type == ESchemaType.ARRAY:
                    pytype = 'Any'
                    if v.items and isinstance(v.items, SchemaBase):
                        pytype = python_types.get(v.items.type) or pytype
                    mark = f':list[{pytype}]'
                elif v.type:
                    pytype = python_types.get(v.type)
                    if pytype:
                        mark = f':{pytype}'

                if v.type == ESchemaType.UNKNOWN:
                    if v.typename:
                        mark = f':{v.typename}'
                if v.ref and isinstance(v.ref, str):
                    mark = f":'{v.ref}'"
            if mark == ':Any':
                deps.add('from typing import Any')
            content += pad_left(f'{k}{mark} = {vstr}  # pyright: ignore\n', 4)
        classes.append(content)
        return name

    def get_flags(schema: AnySchema) -> list[str]:
        if not isinstance(schema, SchemaBase):
            return []

        def to_literal(x: Any) -> Any: # pyright:ignore
            if isinstance(x, str):
                return f"'{x}'"
            return x
        flags = map(lambda x: f'{x[0]}={to_literal(x[1])}', filter(lambda x: x[1] is not None and x[1] is not False, list(schema.flags)))
        return list(flags)
    
    def trans(schema: AnySchema, depth: int = 0) -> str:
        out: list[str] = []

        if isinstance(schema, list):
            for item in schema:
                out.append(trans(item, depth+1))
            return ''.join(out)
        elif isinstance(schema, dict):
            for k, v in schema.items():
                vstr = trans(v, depth+1)
                out.append(vstr)
            return ''.join(out)
        if schema.ref and isinstance(schema.ref, str):
            deps.add('from mongoengine import ReferenceField')
            return f"ReferenceField('{schema.ref}')"
        elif schema.type == ESchemaType.OBJECT:
            classname = make_class(schema)
            return classname
        elif schema.type == ESchemaType.INTEGER:
            deps.add('from mongoengine import IntField')
            flags_str = ', '.join(get_flags(schema))
            return f'IntField({flags_str})'
        elif schema.type == ESchemaType.FLOAT:
            deps.add('from mongoengine import FloatField')
            flags_str = ', '.join(get_flags(schema))
            return f'FloatField({flags_str})'
        elif schema.type == ESchemaType.STRING:
            if schema.enum:
                deps.add('from enum import StrEnum')
                _ = make_enum(schema.key or '_unknown_', schema.enum)
                flags_str = ', '.join(get_flags(schema))
                return f'StringField({flags_str})'
            else:
                flags_str = ', '.join(get_flags(schema))
                deps.add('from mongoengine import StringField')
                return f'StringField({flags_str})'
        elif schema.type == ESchemaType.ARRAY:
            deps.add('from mongoengine import ListField')
            if schema.items:
                return f'ListField({trans(schema.items)})'
            else:
                return 'ListField()'
        elif schema.type == ESchemaType.UNKNOWN:
            if schema.typename == 'file':
                deps.add('from mongoengine import FileField')
                return 'FileField()'
        return '?'



    # contents = '\n'
    contents = '#<DEPS>'
    _  = trans(schema, 0)

    if len(enums) > 0:
        contents += '\n'
        contents += '\n'.join(enums)
        contents += '\n'

    if len(classes) > 0:
        contents += '\n'
        contents += '\n'.join(classes)
    
    return Translation(output=contents, deps=deps, extension='.py', head=['# pyright: basic'])


def translate(schema: AnySchema, base_class: str = 'Document', extra_deps: list[str] | None = None) -> Translation:
    return _translate(schema, base_class=base_class, extra_deps=extra_deps)
