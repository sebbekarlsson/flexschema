# pyright basic


from flexschema.schema.schema import AnySchema, ESchemaType, SchemaBase, SchemaNumeric
from flexschema.translate.translation import Translation

def makepad(x: int) -> str:
    if x <= 0:
        return ''
    return ' ' * x

def pad_left(x: str, pad: int) -> str:
    return f'{makepad(pad)}{x}'

def _translate(schema: AnySchema) -> Translation:
    enums: list[str] = []


    def make_enum(name: str, keys: list[str]):
        ename = f'E{name.title()}'
        content = ''
        content += f'export enum {ename}'
        content += ' {\n'
        content += ',\n'.join(list(map(lambda x: f'{makepad(2)}{x} = "{x}"', keys)))
        content += '\n};'
        enums.append(content)
        return ename
    
    def trans(schema: AnySchema, depth: int = 0) -> str:
        out: list[str] = []

        if isinstance(schema, list):
            for item in schema:
                out.append(trans(item, depth+1))
        elif isinstance(schema, dict):
            for k, v in schema.items():
                vstr = trans(v, depth+1)
                out.append(vstr)
        elif schema.type == ESchemaType.OBJECT:
            name = schema.key or f'SomeObject'
            name = name.replace(' ', '')
            out.append((f'export type {name} = ' if depth <= 0 else '') + '{\n')
            for k, v in schema.properties.items():
                vstr = trans(v, depth+1)
                mark = ''
                if isinstance(v, SchemaBase) and not v.required:
                    mark = '?'
                out.append(pad_left(f'{k}{mark}: {vstr};\n', depth*2+2))
            out.append(pad_left('}' + (';' if depth <= 0 else ''), depth*2))
        elif isinstance(schema, SchemaNumeric):
            out.append('number')
        elif schema.type == ESchemaType.STRING:
            if schema.enum:
                ename = make_enum(schema.key or '_unknown_', schema.enum)
                out.append(ename)
            else:
                out.append('string')
        elif schema.type == ESchemaType.ARRAY:
            if schema.items:
                out.append(f'Array<{trans(schema.items)}>')
            else:
                out.append('Array<any>')
        elif schema.type == ESchemaType.UNKNOWN:
            return 'unknown'



        return ''.join(out)


    contents = trans(schema, 0)

    if len(enums) > 0:
        contents += '\n'
        contents += '\n'.join(enums)
    
    return Translation(output=contents, extension='.ts')


def translate(schema: AnySchema) -> Translation:
    return _translate(schema)
