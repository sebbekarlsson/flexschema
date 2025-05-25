# pyright: basic


from collections.abc import Iterable
import dataclasses
from dataclasses import field as FIELD
from enum import StrEnum
from typing import Any, Literal, TypeAlias, cast
import abc

class ESchemaType(StrEnum):
    ARRAY = 'array'
    BOOLEAN = 'boolean'
    NULL = 'null'
    INTEGER = 'integer'
    FLOAT = 'number'
    OBJECT = 'object'
    STRING = 'string'
    UNKNOWN = 'UNKNOWN'




@dataclasses.dataclass
class SchemaBase(abc.ABC):
    type: ESchemaType 
    description: str | None = FIELD(default=None)
    title: str | None = FIELD(default=None)
    name: str | None = FIELD(default=None)
    enum: list[str] = FIELD(default_factory=list)
    anyOf: list['AnySchema'] = FIELD(default_factory=list)
    id: str | None = FIELD(default=None)
    schema: str | None = FIELD(default=None)
    required: bool = FIELD(default=False)
    default: Any | None = FIELD(default=None)
    unique: bool = FIELD(default=False)
    ref: 'str | AnySchema | None' = FIELD(default=None)
    meta: dict[str, Any] = FIELD(default_factory=dict)

    @classmethod
    def get_fields(cls) -> list[dataclasses.Field]:
        return list(dataclasses.fields(cls))

    @property
    def key(self) -> str | None:
        return self.title or self.name

    @property
    def flags(self) -> Iterable[tuple[str, Any]]:
        for field in self.get_fields():
            if field.name in ['default', 'required', 'unique']:
                value = getattr(self, field.name)
                if value is not None:
                    yield field.name, value


@dataclasses.dataclass
class SchemaObject(SchemaBase):
    type: Literal[ESchemaType.OBJECT] = FIELD(default_factory=lambda: ESchemaType.OBJECT)
    properties: dict[str, 'AnySchema'] = FIELD(default_factory=dict)
    required: list[str] | bool = FIELD(default_factory=list)


@dataclasses.dataclass
class SchemaArray(SchemaBase):
    type: Literal[ESchemaType.ARRAY] = FIELD(default_factory=lambda: ESchemaType.ARRAY)
    items: 'AnySchema | None' = FIELD(default=None)


@dataclasses.dataclass
class SchemaString(SchemaBase):
    type: Literal[ESchemaType.STRING] = FIELD(default_factory=lambda: ESchemaType.STRING)
    pattern: str | None = FIELD(default=None)


@dataclasses.dataclass
class SchemaNumeric[T](SchemaBase):
    minimum: T | None = FIELD(default=None)
    maximum: T | None = FIELD(default=None)
    

@dataclasses.dataclass
class SchemaInteger(SchemaNumeric[int]):
    type: Literal[ESchemaType.INTEGER] = FIELD(default_factory=lambda: ESchemaType.INTEGER)


@dataclasses.dataclass
class SchemaFloat(SchemaNumeric[float]):
    type: Literal[ESchemaType.FLOAT] = FIELD(default_factory=lambda: ESchemaType.FLOAT)

    
@dataclasses.dataclass
class SchemaBoolean(SchemaBase):
    type: Literal[ESchemaType.BOOLEAN] = FIELD(default_factory=lambda: ESchemaType.BOOLEAN)


@dataclasses.dataclass
class SchemaNull(SchemaBase):
    type: Literal[ESchemaType.NULL] = FIELD(default_factory=lambda: ESchemaType.NULL)
    
@dataclasses.dataclass
class SchemaUnknown(SchemaBase):
    type: Literal[ESchemaType.UNKNOWN] = FIELD(default_factory=lambda: ESchemaType.UNKNOWN)
    typename: str = FIELD(default_factory=lambda: 'unknown')
    
_mapping: dict[str, type[SchemaBase]] = {
    ESchemaType.OBJECT: SchemaObject,
    ESchemaType.ARRAY: SchemaArray,
    ESchemaType.STRING: SchemaString,
    ESchemaType.INTEGER: SchemaInteger,
    ESchemaType.FLOAT: SchemaFloat,
    ESchemaType.BOOLEAN: SchemaBoolean,
    ESchemaType.NULL: SchemaNull,
    ESchemaType.UNKNOWN: SchemaUnknown,
}

AnySchema: TypeAlias = SchemaNull | SchemaArray | SchemaObject | SchemaFloat | SchemaString | SchemaInteger | SchemaBoolean | SchemaUnknown | dict[str, 'AnySchema'] | list['AnySchema']

def parse(
    data: dict,
    context: dict[str, AnySchema] | None = None
) -> AnySchema:
    context = context or dict()
    
    def _parse(
        data: dict,
        crumbs: list[str | int],
        crumb: str | int | None = None
    ) -> AnySchema:
        copy = {} 
        current_path = '.'.join(map(lambda x: str(x), crumbs))

        def translate_key(k: str):
            if k.startswith('$'):
                return k[1:]
            return k


        for k, v in data.items():
            if k == 'meta':
                copy[k] = v
                continue
            if k == '$ref':
                other = context.get(v)
                if other and isinstance(other, SchemaBase):
                    copy[translate_key(k)] = other
                    continue
            if isinstance(v, dict):
                if k == 'items':
                    copy[k] = _parse(v, [*crumbs, k], k)
                elif k == 'properties':
                    required_keys = data.get('required', [])
                    props = dict()
                    for pk, pv in v.items():
                        field = _parse(pv, [*crumbs, k, pk], pk)
                        if isinstance(field, SchemaBase):
                            field.name = pk
                            if isinstance(required_keys, list) and field.key and field.key in required_keys:
                                field.required = True
                        props[pk] = field
                    copy[k] = props
                    #copy[translate_key(k)] = _parse(v, [*crumbs, k], k)
                else:
                    copy[translate_key(k)] = _parse(v, [*crumbs, k], k)
            elif isinstance(v, (list, set)):
                copy[translate_key(k)] = list([_parse(item, [*crumbs, k, i], i) if isinstance(item, dict) else item for i, item in enumerate(v)])
            else:
                copy[translate_key(k)] = v


        typename = data.get('type', ESchemaType.UNKNOWN)

        if crumb not in ['properties']:
            if not typename or not isinstance(typename, str):
                raise Exception(f'{current_path}: Missing `type`')

        clazz = _mapping.get(typename) or SchemaUnknown

        if clazz == SchemaUnknown:
            copy['typename'] = typename
            copy['type'] = ESchemaType.UNKNOWN

        parsed = cast(AnySchema, clazz(**copy))
        return parsed 

    return _parse(data, crumbs=[])
