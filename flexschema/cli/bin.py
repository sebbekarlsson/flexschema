# pyright: basic

from argparse import ArgumentParser
from os.path import splitext
from flexschema.schema.schema import AnySchema, SchemaBase, parse
from flexschema.translate.translation import Translation
from flexschema.translate.typescript.translate import translate as translate_typescript
from flexschema.translate.mongoengine.translate import translate as translate_mongoengine
import dataclasses
import json
import os

parser = ArgumentParser()
_ = parser.add_argument(
    '--input-file',
    required=True,
    type=str,
    help='JSON file with an array of schemas'
)
_ = parser.add_argument(
    '--out-name',
    required=False,
    type=str,
    help='File to write to (without extension)'
)
_ = parser.add_argument(
    '--out-dir',
    required=False,
    type=str,
    help='Directory to write to. If specified, separate files will be created.'
)
_ = parser.add_argument(
    '--debug',
    required=False,
    type=bool,
    help='If set, will just print'
)

###########################
#  Mongoengine options
###########################
_ = parser.add_argument(
    '--mongoengine-base-class',
    required=False,
    type=str,
    help='The base class for each model'
)
_ = parser.add_argument(
    '--mongoengine-base-class-import',
    required=False,
    type=str,
    help='The import for the base class specified by `--mongoengine-base-class`'
)
###########################

args = parser.parse_args()


def read_and_close(filepath: str) -> str:
    file = open(filepath, 'r')
    content = file.read()
    file.close()
    return content


def write_and_close(filepath: str, content: str):
    if args.debug:
        print(f'FILE: {filepath}')
        print('--------------------------')
        print(content)
        print('--------------------------')
        return
    file = open(filepath, 'w+')
    file.write(content)
    file.close()

def maybe_make_dir(dirpath: str):
    if args.debug:
        return
    if not os.path.exists(dirpath):
        os.makedirs(dirpath)

@dataclasses.dataclass
class TranslationUnit:
    translation: Translation
    filepath: str

def process_schema(schema: AnySchema, i: int) -> list[TranslationUnit]:
    name = ((schema.key if isinstance(schema, SchemaBase) else None) or f'schema_{i}').replace(' ', '')

    typescript_filename = f'{name}.ts'
    typescript_filepath = os.path.join(args.out_dir, typescript_filename) if args.out_dir else typescript_filename
    typescript_code = translate_typescript(schema)

    #write_and_close(typescript_filepath, typescript_code)

    mongoengine_filename = f'{name}.py'
    mongoengine_filepath = os.path.join(args.out_dir, mongoengine_filename) if args.out_dir else mongoengine_filename
    extra_deps: list[str] = []
    if args.mongoengine_base_class_import:
        extra_deps.append(args.mongoengine_base_class_import)
    mongoengine_code = translate_mongoengine(schema, base_class=args.mongoengine_base_class, extra_deps=extra_deps)


    return [
        TranslationUnit(translation=typescript_code, filepath=typescript_filepath),
        TranslationUnit(translation=mongoengine_code, filepath=mongoengine_filepath)
    ]
    #return ProcessOutput(typescript_code=typescript_code, mongoengine_code=mongoengine_code)

    #write_and_close(mongoengine_filepath, mongoengine_code)

    
        
def run():
    json_data:list[dict] = json.loads(read_and_close(args.input_file))
    if not isinstance(json_data, list):
        raise Exception('Not an array') # pyright: ignore

    

    schemas = [parse(item) for item in json_data]

    if args.out_name and args.out_dir:
        outputs: dict[str, list[str]] = {}
        deps: dict[str, set[str]] = {}
        heads: dict[str, set[str]] = {}
        did_write_deps: bool = False
        
        for i, schema in enumerate(schemas):
            if isinstance(schema, SchemaBase):
                units = process_schema(schema, i)

                for unit in units:
                    _, ext = splitext(unit.filepath)
                    outputs[ext] = outputs.get(ext, []) or []
                    outputs[ext].append(unit.translation.output)
                    deps[ext] = deps.get(ext, set()) or set()
                    deps[ext].update(unit.translation.deps)
                    heads[ext] = heads.get(ext, set()) or set()
                    heads[ext].update(unit.translation.head)

        for k, v in outputs.items():
            filepath = os.path.basename(f'{args.out_name}{k}') 
            filepath = os.path.join(args.out_dir, filepath)
            unit_heads = heads.get(k)

            code = ''
            
            if unit_heads is not None and len(unit_heads) > 0:
                code += '\n'.join(list(unit_heads))
                code += '\n'
                
            code += '\n'.join(v)
            
            unit_deps = deps.get(k)

                

            if unit_deps and '#<DEPS>' in code and not did_write_deps:
                deps_str = '\n'.join(list(unit_deps))
                code = code.replace('#<DEPS>', deps_str + '\n', 1)
                did_write_deps = True
                code = code.replace('#<DEPS>', '')
            
            write_and_close(filepath, code)

    elif args.out_dir:
        maybe_make_dir(args.out_dir)

        for i, schema in enumerate(schemas):
            if isinstance(schema, SchemaBase):
                units = process_schema(schema, i)

                for unit in units:
                    code = ''

                    unit_heads = unit.translation.head
                    code = ''

                    if unit_heads and len(unit_heads) > 0:
                        code += '\n'.join(list(unit_heads))
                        code += '\n'
                    
                    code += unit.translation.output
                    if '#<DEPS>' in code:
                        deps_str = '\n'.join(list(unit.translation.deps))
                        code = code.replace('#<DEPS>', deps_str + '\n')
                    write_and_close(unit.filepath, code)
    else:
        raise Exception('--out-dir or --out-name must be specified')
            
