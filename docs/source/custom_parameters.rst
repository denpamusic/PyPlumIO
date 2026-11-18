Custom Parameters
=================

Overview
--------

ecoMAX firmware varies across controller models: newer models store settings in
the service parameter table (:ref:`EcomaxServiceParameters<EcomaxServiceParameters>`),
and some models shift or repurpose entries in the standard parameter table
(:ref:`EcomaxParameters<EcomaxParameters>`). Custom parameter modules map those
entries to named parameters so they work seamlessly with :doc:`reading` and
:doc:`writing` (``ecomax.get(...)`` and ``ecomax.set(...)``).

A custom module defines one or both of the following tables:

.. list-table::
   :widths: 24 76
   :header-rows: 1

   * - Table
     - Purpose
   * - ``service_parameters``
     - Maps :ref:`EcomaxServiceParameters<EcomaxServiceParameters>` by index.
   * - ``patches``
     - Overrides :ref:`EcomaxParameters<EcomaxParameters>` by name.

To match a module to a controller, PyPlumIO converts
:py:class:`~pyplumio.structures.product_info.ProductInfo` ``model`` (from the
:ref:`UID<UID>` response) into ``<model_slug>`` by replacing ``"-"`` and
``" "`` with ``"_"`` and lowercasing (for example, ``"ecoMAX 350P2-ZF"`` becomes
``ecomax_350p2_zf``). **Both** the exact ``model`` string and numeric ``id``
(visible in the CLI header or via ``await ecomax.get("product")``) must match
the connected controller.

How-To Guides
-------------

Generating a Starter Module with the CLI
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Use the interactive utility in :doc:`cli` to connect to your controller, inspect
raw :ref:`EcomaxServiceParameters<EcomaxServiceParameters>` entries, and export
a starter ``service_parameters`` module, test file, and captured frame JSON
(optionally bundled as ``<model_slug>.zip``). Saving in the CLI regenerates
plain ``number()`` and ``switch()`` entries for ``service_parameters``, so add
manual ``patches`` or ``functools.partial`` helpers afterward.

Writing or Patching a Module by Hand
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Create ``pyplumio/parameters/custom/<model_slug>.py`` with a module docstring,
``from __future__ import annotations``, and a module-level
``PARAMETERS = custom_parameters(...)`` constant. See
`ecomax_350p2_zf.py <https://github.com/denpamusic/PyPlumIO/blob/main/pyplumio/parameters/custom/ecomax_350p2_zf.py>`_
(``pyplumio/parameters/custom/ecomax_350p2_zf.py``) for a complete reference.

For ``service_parameters``, map each raw index to ``number()`` or ``switch()``,
use ``#`` comments to document enum-style numeric options, and factor repeated
descriptors with ``functools.partial``. When raw wire values are scaled or
shifted, PyPlumIO unpacks them as
``unpacked = round((raw - offset) * step, precision)``:

- **Positive offset**: ``number("heating_curve_shift", offset=20, unit="°C")``
  maps raw ``0..40`` to ``-20..20 °C``.
- **Negative offset with step**: ``partial(number, step=10.0, offset=-30, unit="rpm")``
  maps raw ``0..255`` to ``300..2850 rpm``.

.. code-block:: python

    """Contains custom parameters for ecoMAX 860P4-NM TOUCH."""

    from __future__ import annotations

    from functools import partial

    from pyplumio.parameters.custom import custom_parameters, number, switch

    _fan_speed = partial(number, step=10.0, offset=-30, unit="rpm")

    PARAMETERS = custom_parameters(
        model="ecoMAX 860P4-NM TOUCH",
        id=41,
        service_parameters={
            0: number("max_boiler_output", unit="kW"),
            11: _fan_speed("fan_speed_30"),
            # 0 - off, 1 - priority, 2 - no priority.
            90: number("water_heater_pump_mode"),
            100: switch("heat_exchanger"),
            220: number("fuel_correction", offset=20, unit="%"),
        },
    )

For ``patches``, keys are the **original** standard parameter names from
:ref:`EcomaxParameters<EcomaxParameters>`, mapped to replacement ``number()`` or
``switch()`` descriptors (adapted from
``pyplumio/parameters/custom/ecomax_860d3_hb.py``):

.. code-block:: python

    PARAMETERS = custom_parameters(
        model="ecoMAX 860D3-HB",
        id=48,
        patches={
            "disable_pump_on_thermostat": number("water_heater_target_temp", unit="°C"),
            "pump_hysteresis": switch("water_heater_disinfection"),
        },
    )

Testing and Contributing
~~~~~~~~~~~~~~~~~~~~~~~~

You can contribute mapped parameters in two ways:

1. **GitHub Issue**: Attach the ``<model_slug>.zip`` archive exported by
   :doc:`cli` to an issue on `PyPlumIO <https://github.com/denpamusic/PyPlumIO/>`_.
2. **Pull Request**: Open a PR containing all three required files:

   - ``pyplumio/parameters/custom/<model_slug>.py`` — exports ``PARAMETERS``
     with ``model`` matching ``<model_slug>``, a non-bool integer ``id``, and
     non-empty ``service_parameters`` or ``patches``.
   - ``tests/testdata/parameters/<model_slug>.json`` — real frame data captured
     from the controller.
   - ``tests/parameters/custom/test_<model_slug>.py`` — parametrized tests
     verifying each parameter's class, value, bounds, and unit; use
     `test_ecomax_350p2_zf.py <https://github.com/denpamusic/PyPlumIO/blob/main/tests/parameters/custom/test_ecomax_350p2_zf.py>`_
     (``service_parameters``) or
     `test_ecomax_860d3_hb.py <https://github.com/denpamusic/PyPlumIO/blob/main/tests/parameters/custom/test_ecomax_860d3_hb.py>`_
     (``patches``) as a template.

Before opening a PR, verify the test suite and linters pass locally:

.. code-block:: console

    $ uv run pytest
    $ prek run --all-files

DSL Reference
-------------

.. autofunction:: pyplumio.parameters.custom.custom_parameters

.. autofunction:: pyplumio.parameters.custom.number

.. autofunction:: pyplumio.parameters.custom.switch

Supported Units
~~~~~~~~~~~~~~~

``number(..., unit=...)`` accepts ``UnitOfMeasurement`` enum members,
``PERCENTAGE``, ``None``, or any string literal listed below. Passing an
unrecognized string raises ``ValueError``.

.. list-table::
   :widths: 20 35 45
   :header-rows: 1

   * - Literal
     - ``UnitOfMeasurement`` / Constant
     - Meaning
   * - ``"°C"``
     - ``CELSIUS``
     - Degrees Celsius
   * - ``"kW"``
     - ``KILO_WATT``
     - Kilowatts
   * - ``"g"``
     - ``GRAMS``
     - Grams
   * - ``"kg"``
     - ``KILOGRAMS``
     - Kilograms
   * - ``"kWh/kg"``
     - ``KILO_WATT_HOUR_PER_KILOGRAM``
     - Kilowatt-hours per kilogram
   * - ``"kg/h"``
     - ``KILOGRAMS_PER_HOUR``
     - Kilograms per hour
   * - ``"s"``
     - ``SECONDS``
     - Seconds
   * - ``"min"``
     - ``MINUTES``
     - Minutes
   * - ``"days"``
     - ``DAYS``
     - Days
   * - ``"Pa"``
     - ``PASCAL``
     - Pascals
   * - ``"rpm"``
     - ``REVOLUTIONS_PER_MINUTE``
     - Revolutions per minute
   * - ``"%"``
     - ``PERCENTAGE``
     - Percentage
