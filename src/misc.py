from typing import Any, Dict

__all__ = [
    'object_collect_fields',
    'object_repr',
    'object_str',
]


def object_collect_fields(obj: object) -> Dict[str, Any]:
    _cls = obj.__class__

    # __slots__ of class
    if hasattr(_cls, '__slots__'):
        attrs = _cls.__slots__
        if isinstance(attrs, str):
            attrs = (attrs,)
    # __dict__ of object
    elif hasattr(obj, '__dict__') and obj.__dict__:
        attrs = obj.__dict__.keys()
    # __annotations__ of class
    elif hasattr(_cls, '__annotations__') and _cls.__annotations__:
        attrs = _cls.__annotations__.keys()
    # fallback to __dir__() of object without dander methods
    else:
        attrs = (attr for attr in obj.__dir__() if not attr.startswith('__'))

    # Collecting all available attributes to dictionary
    fields = {attr: getattr(obj, attr, '<missing>') for attr in attrs}

    return fields


def object_repr(obj: object) -> str:
    _cls = obj.__class__
    class_name = _cls.__name__

    fields = [f'{k}={v!r}' for k, v in object_collect_fields(obj).items()]
    fields_str = ', '.join(fields)

    return f'{class_name}({fields_str})'


def object_str(obj: object) -> str:
    _cls = obj.__class__
    class_name = _cls.__name__

    class_name_cool = f'==== "{class_name}" Instance: ===='
    fields = [
        f'{k.replace("_", " ").capitalize()}: {v!s}' for k, v
        in object_collect_fields(obj).items()
    ]
    fields_str = '\n'.join(fields)

    return f'{class_name_cool}\n{fields_str}\n{"=" * len(class_name_cool)}'
