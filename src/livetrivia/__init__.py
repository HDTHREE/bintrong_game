import lazy_loader as lazy


SUBPACKAGES: tuple[str] = ("_fe_app", "_be_app", "text_extraction", "utils")


__getattr__, __dir__, __all__ = lazy.attach(__name__, SUBPACKAGES)
