# Copyright 2012 Mixpanel, Inc.
# Copyright 2014 Rackspace, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import contextlib
import functools
import os
import random
import string
import time

# subprocess is not monkey-patched, hence the special import
import sys
if 'eventlet' in sys.modules:
    from eventlet.green import subprocess
else:
    import subprocess

low_port = 11000
high_port = 11210


def terminated(f):
    class terminating(tuple):
        def __new__(cls, t):
            return super(terminating, cls).__new__(cls, t)

        def __enter__(self):
            return self

        def __exit__(self, *exc_info):
            if self[0].returncode is None:
                self[0].terminate()
                self[0].wait()

    @functools.wraps(f)
    def wrapped(*args, **kwargs):
        return terminating(f(*args, **kwargs))

    return wrapped


# spin up new memcached instance to test against
@terminated
def start_new_memcached_server(port=None, mock=False, additional_args=[]):
    if not port:
        global low_port
        ports = range(low_port, high_port + 1)
        low_port += 1
    else:
        ports = [port]

    # try multiple ports so that can cleanly run tests
    # w/o having to wait for a particular port to free up
    for attempted_port in ports:
        try:
            if mock:
                command = [
                    'python',
                    os.path.join(os.path.dirname(__file__),
                                 'mock_memcached.py'),
                    '-p',
                    str(attempted_port),
                ]
            else:
                command = [
                    'memcached',
                    '-p',
                    str(attempted_port),
                    '-m',
                    '1',  # 1MB
                    '-l',
                    '127.0.0.1',
                ]
            command.extend(additional_args)
            p = subprocess.Popen(command)
            time.sleep(2)  # needed otherwise unittest races against startup
            return p, attempted_port
        except:
            pass  # try again
    else:
        raise Exception('could not start memcached -- no available ports')


@contextlib.contextmanager
def expect(*exc_type):
    """A context manager to validate raised expections.

    :param *exc_type: Exception type(s) expected to be raised during
        execution of the "with" context.
    """
    assert len(exc_type) > 0

    try:
        yield
    except exc_type:
        pass
    else:
        raise AssertionError(
            'Not raised: %s' % ', '.join(e.__name__ for e in exc_type))


def random_key(maxlen=10, chars=string.ascii_lowercase + string.digits):
    l = random.randint(1, maxlen)
    return ''.join(random.choice(chars) for _ in range(l))
