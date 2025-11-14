import lazy_loader as lazy


SUBPACKAGES: tuple[str] = ("text_extraction", "utils")


SUBMOD_ATTRS: dict[str, list[str]] = {"_fe_app": ["app"], "_be_app": ["api"]}


__getattr__, __dir__, __all__ = lazy.attach(__name__, SUBPACKAGES, SUBMOD_ATTRS)
