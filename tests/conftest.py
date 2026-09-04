"""Put the goggles package on the path for pytest.

`smart_goggles/` modules import `config` absolutely, so the package only
resolves with that directory on sys.path.
"""

import os
import sys

sys.path.insert(
    0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "smart_goggles"))
