__all__ = ["MainWindow"]


def __getattr__(name):
    if name == "MainWindow":
        from .window import MainWindow

        return MainWindow
    raise AttributeError(name)
