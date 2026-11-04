Command Line Interface
======================

PyPlumIO includes an interactive command-line utility for mapping ecoMAX controller
service parameters and generating custom parameter modules.

Installation
------------

The CLI utility requires optional dependencies (such as ``prompt_toolkit``).
Install PyPlumIO with the ``cli`` extra:

.. code-block:: console

    $ pip install "pyplumio[cli]"
    # or with uv
    $ uv add "pyplumio[cli]"

Usage
-----

Run the CLI using the console script or Python module execution:

.. code-block:: console

    $ pyplumio
    # or
    $ python -m pyplumio

Command-Line Options
--------------------

The CLI supports the following arguments:

.. code-block:: text

    usage: pyplumio [-h] [--url URL] [--output DIR] [--interval SECONDS] [--baudrate BAUDRATE]

    options:
      -h, --help          show this help message and exit
      --url URL           Connection URL (e.g. socket://localhost:8899 or /dev/ttyUSB0).
                          If omitted, you will be prompted interactively.
      --output DIR        Output directory for generated files (default: current working directory).
      --interval SECONDS  Polling interval in seconds (default: 2.0).
      --baudrate BAUDRATE Serial baudrate (default: 115200).

Interactive Connection Setup
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If ``--url`` is omitted, the CLI will guide you through configuring the connection:

1. **Connection Type**: Choose between ``tcp`` and ``serial``.
2. **TCP Settings**: Enter host and port (default: ``8899``).
3. **Serial Settings**: Enter the serial port path (e.g., ``/dev/ttyUSB0`` or ``COM3``).

Workflow & Parameter Mapping
----------------------------

Once connected, the CLI retrieves the controller model and product ID and continuously
polls service parameters.

The interface consists of:

- **Header**: Shows connected controller model, product ID, connection URL, last update timestamp, and keyboard shortcuts.
- **Table**: Monospace scrollable list showing parameter indices, mapped names, current values, minimums, and maximums. Values changed in the latest response are prefixed with an asterisk (``*``).
- **Navigation**: Use Up/Down arrow keys or ``PageUp`` and ``PageDown`` to scroll through the parameters list.

Interactive Wizard
~~~~~~~~~~~~~~~~~~

At the bottom of the screen, a wizard guides you through naming and configuring each parameter:

1. **Index**: Enter the parameter index from the table.
2. **Name**: Enter a unique snake_case name (e.g. ``heating_temp``).
3. **Type**: Select ``number`` (default) or ``switch``.
4. **Number Settings**: If configuring a number:
   - **Step**: Multiplier/step (e.g. ``1``, ``0.1``, ``10``).
   - **Offset**: Raw offset to subtract (default: ``0``).
   - **Unit**: Physical unit of measurement (supports autocompletion for unit values such as ``°C``, ``kW``, ``rpm``, ``%``, etc., or enter ``none``).
5. **Preview**: Confirm the decoded value and range match your controller display (``[y/N]``).
6. Press ``Esc`` at any point to cancel the wizard.

Saving & Output Files
---------------------

Press ``Ctrl+S`` to save generated files. If files already exist in the target directory,
you will be prompted to confirm overwrite.

The utility produces three files in the output directory:

1. **Custom Parameter Module**:
   ``<output>/pyplumio/parameters/custom/<model_slug>.py``
   Contains the ``CustomParameters`` class definition, model signature, and descriptions dictionary.

2. **Test Module**:
   ``<output>/tests/parameters/custom/test_<model_slug>.py``
   Parametrized pytest tests verifying every mapped parameter against real frame data.

3. **Captured Frame Test Data**:
   ``<output>/tests/testdata/parameters/<model_slug>.json``
   Raw frame capture used for reproducible testing.

Press ``Ctrl+Q`` to exit the application cleanly.

Contributing Mapped Parameters
------------------------------

Once you have mapped parameters for your controller model:

1. Open a pull request against `PyPlumIO <https://github.com/denpamusic/PyPlumIO/>`_ adding the generated files.
2. Alternatively, create an issue on GitHub and attach the generated files (or a zip archive containing them).
