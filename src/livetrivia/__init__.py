import lazy_loader as lazy


SUBPACKAGES: tuple[str] = ("text_extraction", "utils")


SUBMOD_ATTRS: dict[str, list[str]] = {"_app": ["app"], "_api": ["api"]}


__getattr__, __dir__, __all__ = lazy.attach(__name__, SUBPACKAGES, SUBMOD_ATTRS)
