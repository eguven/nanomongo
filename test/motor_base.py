import os
import functools
import time

from tornado import gen, ioloop
from tornado.stack_context import ExceptionStackContext

# async_test_engine, AssertEqual
# taken from motor library by GitHub @mongodb @ajdavis


def async_test_engine(timeout_sec=5, io_loop=None):
    if timeout_sec is not None and not isinstance(timeout_sec, (int, float)):
        raise TypeError("""\
Expected int or float, got %r
Use async_test_engine like:
    @async_test_engine()
or:
    @async_test_engine(timeout_sec=10)""" % timeout_sec)

    timeout_sec = max(float(os.environ.get('TIMEOUT_SEC', 0)), timeout_sec)

    def decorator(func):
        @functools.wraps(func)
        def _async_test(self):
            loop = io_loop or ioloop.IOLoop.instance()
            start = time.time()
            is_done = [False]
            error = [None]

            def on_exception(exc_type, exc_value, exc_traceback):
                error[0] = exc_value
                loop.stop()

            def done():
                is_done[0] = True
                loop.stop()

            def start_test():
                gen.engine(func)(self, done)

            def on_timeout():
                error[0] = AssertionError(
                    '%s timed out after %.2f seconds' % (
                        func, time.time() - start))
                loop.stop()

            timeout = loop.add_timeout(start + timeout_sec, on_timeout)

            with ExceptionStackContext(on_exception):
                loop.add_callback(start_test)

            loop.start()
            loop.remove_timeout(timeout)
            if error[0]:
                raise error[0]

            if not is_done[0]:
                raise Exception('%s did not call done()' % func)

        return _async_test
    return decorator

async_test_engine.__test__ = False  # Nose otherwise mistakes it for a test


class AssertEqual(gen.Task):
    def __init__(self, expected, func, *args, **kwargs):
        super(AssertEqual, self).__init__(func, *args, **kwargs)
        self.expected = expected

    def get_result(self):
        (result, error), _ = self.runner.pop_result(self.key)
        if error:
            raise error

        if self.expected != result:
            raise AssertionError("%s returned %s\nnot\n%s" % (
                self.func, repr(result), repr(self.expected)))

        return result
