# PyPlumIO is a native ecoNET library for Plum ecoMAX controllers.
[![PyPI version](https://badge.fury.io/py/PyPlumIO.svg)](https://badge.fury.io/py/PyPlumIO)
[![PyPI Supported Python Versions](https://img.shields.io/pypi/pyversions/pyplumio.svg)](https://pypi.python.org/pypi/pyplumio/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

```python
from pyplumio import econet_connection

async def main(ecomax, econet):
    if ecomax.has_data():
        print(ecomax)

with econet_connection("ecomax.home", 8899) as c:
    c.loop(main)
```
