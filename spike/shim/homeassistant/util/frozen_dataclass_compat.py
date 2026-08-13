"""Shim of homeassistant.util.frozen_dataclass_compat.

Real HA lets one description base be subclassed by *either* a frozen or a plain
``@dataclass``. Python forbids that directly: a frozen dataclass may not inherit
from a non-frozen one, or the reverse. HA sidesteps it with the ``FrozenOrThawed``
metaclass, and integrations in the wild depend on both halves of that behaviour —

  * ``andrews_arnold_quota`` declares a plain ``@dataclass`` and *mutates*
    ``entity_description.entity_id`` after construction;
  * ``matomo`` declares ``@dataclass(frozen=True, kw_only=True)``.

A shim that picks either frozen or unfrozen for the base can therefore run one of
them, never both. Only reproducing HA's mechanism runs both.

How it works: a class carrying ``frozen_or_thawed=True`` is deliberately *not*
made a dataclass itself. Instead it builds a parallel frozen dataclass in
``cls._dataclass`` and delegates construction to it. Because the class itself is
not a dataclass, ``@dataclass`` on a subclass sees no dataclass base and so no
frozen/non-frozen conflict is raised; the subclass instead inherits the fields
through injected annotations.

Divergence from upstream: HA uses ``annotationlib`` (Python 3.14+) to read
annotations. This reads ``__annotations__`` directly so it runs on 3.12, and
builds fields without calling ``dataclasses._get_field``. The observable contract
is the same.
"""

from __future__ import annotations

import dataclasses
from typing import Any, ClassVar, get_origin


def _own_annotations(cls: type) -> dict[str, Any]:
    """Annotations declared on ``cls`` itself, not inherited ones."""
    return dict(cls.__dict__.get("__annotations__", {}))


def _is_pseudo_field(name: str, type_: Any) -> bool:
    """Names that carry a type but are not dataclass fields."""
    if name.startswith("_FrozenOrThawed__"):
        return True
    if type_ is dataclasses.KW_ONLY:
        return True
    # ClassVar in either evaluated or string form.
    if get_origin(type_) is ClassVar:
        return True
    return isinstance(type_, str) and type_.startswith(("ClassVar", "typing.ClassVar"))


def _class_fields(cls: type, kw_only: bool) -> list[tuple[str, Any, Any]]:
    """Build ``make_dataclass`` field triples from the class's own annotations."""
    fields: list[tuple[str, Any, Any]] = []
    for name, type_ in _own_annotations(cls).items():
        if _is_pseudo_field(name, type_):
            continue
        default = cls.__dict__.get(name, dataclasses.MISSING)
        if isinstance(default, dataclasses.Field):
            spec = default
        elif default is dataclasses.MISSING:
            spec = dataclasses.field(kw_only=kw_only)
        else:
            spec = dataclasses.field(default=default, kw_only=kw_only)
        fields.append((name, type_, spec))
    return fields


class FrozenOrThawed(type):
    """Metaclass allowing a base to be subclassed frozen *or* mutable."""

    def _make_dataclass(cls, name: str, bases: tuple[type, ...], kw_only: bool) -> None:
        class_fields = _class_fields(cls, kw_only)
        # Chain onto each base's frozen counterpart where it has one.
        dataclass_bases = tuple(getattr(base, "_dataclass", base) for base in bases)
        cls._dataclass = dataclasses.make_dataclass(
            name, class_fields, bases=dataclass_bases, frozen=True
        )

    def __new__(
        mcs,
        name: str,
        bases: tuple[type, ...],
        namespace: dict[str, Any],
        frozen_or_thawed: bool = False,
        **kwargs: Any,
    ) -> Any:
        namespace["_FrozenOrThawed__frozen_or_thawed"] = frozen_or_thawed
        return super().__new__(mcs, name, bases, namespace)

    def __init__(
        cls,
        name: str,
        bases: tuple[type, ...],
        namespace: dict[str, Any],
        **kwargs: Any,
    ) -> None:
        super().__init__(name, bases, namespace)

        if not namespace["_FrozenOrThawed__frozen_or_thawed"]:
            # A real dataclass (the integration's own subclass). If every direct
            # parent is already a dataclass, normal inheritance carries the
            # fields. Otherwise the parent is one of ours and is deliberately not
            # a dataclass, so its fields have to be injected as annotations for
            # the pending @dataclass decorator to pick up.
            if bases and all(dataclasses.is_dataclass(base) for base in bases):
                return
            annotations: dict[str, Any] = {}
            for parent in cls.__mro__[::-1]:
                if parent is object:
                    continue
                for field_name, type_ in _own_annotations(parent).items():
                    if not _is_pseudo_field(field_name, type_):
                        annotations[field_name] = type_
            cls.__annotations__ = annotations
            return

        # Fields without defaults must precede fields with them; if this class's
        # shape violates that, retry as keyword-only, as HA does.
        try:
            cls._make_dataclass(name, bases, False)
        except TypeError:
            cls._make_dataclass(name, bases, True)

        def __new__(*args: Any, **kwargs: Any) -> object:
            """Construct via the frozen counterpart unless cls is a real dataclass.

            Deliberately has no named parameters: a field could be called ``cls``.
            """
            cls_, *rest = args
            if dataclasses.is_dataclass(cls_):
                return object.__new__(cls_)
            return cls_._dataclass(*rest, **kwargs)

        cls.__init__ = cls._dataclass.__init__
        cls.__new__ = __new__
