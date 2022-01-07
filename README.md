# PyPlumIO is a native ecoNET library for Plum ecoMAX controllers.

```python
from pyplumio import econet_connection

async def main(ecomax, econet):
    if ecomax.has_data():
        print(ecomax)

with econet_connection('ecomax.home', 8899) as c:
    c.loop(main)
```
