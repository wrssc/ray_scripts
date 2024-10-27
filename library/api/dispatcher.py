# dispatcher.py
import functools
import logging
from library.api.api_utils import detect_api_version


class APIDispatcher:
    def __init__(self):
        self.version, self.subversion = detect_api_version()
        self.function_map = {}

    def register(self, func_key, version, func):
        if func_key not in self.function_map:
            self.function_map[func_key] = {}
        self.function_map[func_key][version] = func

    def dispatch(self, function_key):
        def decorator(func):
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                func_to_call = self.function_map[function_key].get(self.version)
                if func_to_call:
                    return func_to_call(*args, **kwargs)
                else:
                    error_msg = f"No implementation for {function_key} under API version {self.version}"
                    logging.error(error_msg)
                    raise NotImplementedError(error_msg)
            return wrapper
        return decorator
