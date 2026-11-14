Command Line Interface
======================

PyPlumIO includes an interactive command-line utility for mapping ecoMAX controller
service parameters and generating custom parameter modules.

Installation
------------

Windows Executable
~~~~~~~~~~~~~~~~~~

On Windows, download the standalone ``pyplumio.exe`` executable from the
`GitHub Releases <https://github.com/denpamusic/PyPlumIO/releases>`_ page. No Python
installation is required—double-click ``pyplumio.exe`` or run it from Command Prompt
or PowerShell. Generated files (or ``<model_slug>.zip``) are saved in the working
directory where ``pyplumio.exe`` is launched unless ``--output`` is specified.

Python Package
~~~~~~~~~~~~~~

Alternatively, install PyPlumIO with the ``cli`` extra (which includes optional
dependencies such as ``prompt_toolkit``):

.. code-block:: console

    $ pip install "pyplumio[cli]"
    # or with uv
    $ uv add "pyplumio[cli]"

Usage
-----

Run the CLI using the standalone executable, console script, or Python module execution:

.. code-block:: console

    $ pyplumio
    # or
    $ python -m pyplumio

Command-Line Options
--------------------

The CLI supports the following arguments:

.. code-block:: text

    usage: pyplumio [-h] [--url URL] [--output DIR] [--interval SECONDS] [--baudrate BAUDRATE] [-z]

    options:
      -h, --help          show this help message and exit
      --url URL           Connection URL (e.g. socket://localhost:8899 or /dev/ttyUSB0).
                          If omitted, you will be prompted interactively.
      --output DIR        Output directory for generated files (default: current working directory).
      --interval SECONDS  Polling interval in seconds (default: 2.0).
      --baudrate BAUDRATE Serial baudrate (default: 115200).
      -z, --zip           Save output as a ZIP archive.

Interactive Connection Setup
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If ``--url`` is omitted, the CLI will guide you through configuring the connection:

1. **Connection Type**: Choose between ``tcp`` and ``serial``.
2. **TCP Settings**: Enter host and port (default: ``8899``).
3. **Serial Settings**: Enter the serial port path (e.g., ``/dev/ttyUSB0`` or ``COM3``).

Workflow & Parameter Mapping
----------------------------

During startup, the CLI connects to the controller, retrieves the product
information and model name, and requests the initial service parameters before
opening the full-screen interface. Progress messages are written to standard
error at each stage: connecting to the URL, requesting product info with attempt
counters (e.g. ``(1/3)``), requesting service parameters for the detected
model, and starting the interface. Each request attempt uses a 5-second timeout
and up to 3 attempts (up to about 30 seconds total in the worst case). If the
controller never answers service parameters requests after all attempts, the
CLI exits before opening the interface with an error explaining that the
controller may not support them. If the connection drops at any point during
this phase, a connection-lost error is reported instead. Once startup succeeds,
the full-screen interface opens with the parameter table already filled and keeps
polling in the background.

The interface consists of:

- **Header**: Shows connected controller model, product ID, connection URL, last update timestamp, and keyboard shortcuts.
- **Table**: Monospace scrollable list showing parameter indices, mapped names, current values, minimums, and maximums. Recently changed parameters are highlighted with inverted colors.
- **Live Preview**: Real-time 4-line framed box docked above the input bar displaying active parameter fields, raw values, and live calculations.
- **Navigation**: Use Up/Down arrow keys or ``PageUp`` and ``PageDown`` to scroll through the parameters list.

Interactive Wizard
~~~~~~~~~~~~~~~~~~

At the bottom of the screen, a wizard guides you through naming and configuring each parameter:

1. **Index**: Enter the parameter index from the table. While navigating the wizard past this step, table row ordering is frozen to prevent rows from jumping while typing.
2. **Name**: Enter a unique snake_case name (e.g. ``heating_temp``):
   - Standard ecoMAX parameter names for the connected device are offered as autocompletion (substring match; names already used by other indices are left out).
   - If the name is already used by another parameter index, it is rejected.
   - Choosing or typing a standard name pre-fills the **Type**, **Offset**, **Step**, and **Unit** defaults from that parameter's standard description. Re-editing an already-mapped parameter and keeping its name preserves its existing settings as defaults. Sharing a name with a standard parameter is intended, so there is no warning any more.
   - Submitting an empty name deletes the parameter (and its comment) if it is already mapped, or cancels and returns to the index prompt if it has not been mapped yet.
3. **Type**: Select ``number`` or ``switch`` (defaults to the pre-filled template type, or ``switch`` if minimum is 0 and maximum is 1, otherwise ``number``).
4. **Number Settings**: If configuring a number (defaults come from the matched template or existing mapping, or fall back to ``0``, ``1``, and ``none``):
   - **Offset**: Raw offset to subtract (default: ``0``).
   - **Step**: Multiplier/step (default: ``1``; e.g. ``1``, ``0.1``, ``10``).
   - **Unit**: Physical unit of measurement (supports autocompletion for unit values such as ``°C``, ``kW``, ``rpm``, ``%``, etc., or enter ``none`` to clear a pre-filled unit).
5. **Comment**: Enter an optional comment (or leave empty for none). When re-editing a parameter that already has a comment (either loaded from an existing custom parameter module or added in the current session), the prompt is pre-filled with the existing comment. Comments are written as wrapped ``# ...`` lines directly above the parameter entry in the generated module.
6. **Confirm**: Confirm the decoded value and range match your controller display (``[y/N]``).
7. Press ``Esc`` at any point to cancel the wizard.

Connection Resilience
---------------------

If the serial connection or TCP bridge drops during a session, the CLI automatically stops background polling and notifies you via the status line:

.. code-block:: text

    Connection lost. Reconnecting in background...

The CLI automatically retries the connection every 20 seconds in the background while keeping the interface fully responsive. Once reconnected, it displays ``Connection restored.`` and resumes polling. Even when disconnected, you can review mapped parameters, continue editing, and press ``Ctrl+S`` to save the files from the last received frame.

Saving & Output Files
---------------------

Press ``Ctrl+S`` to save generated files. At least one parameter must be mapped; attempting to save with no mapped parameters will show:

.. code-block:: text

    Nothing to save: map at least one parameter first.

Unless ``-z`` / ``--zip`` was passed on the command line, you will be asked ``Save as a ZIP archive? [y/N]``:

- Answering ``n`` (or pressing Enter) writes the three generated files directly into the ``<output>`` directory tree. If ``<output>/pyplumio/parameters/custom/<model_slug>.py`` already exists, you will be prompted to confirm overwrite (``Overwrite existing <model_slug>.py? [y/N]``).
- Answering ``y`` (or starting the CLI with ``-z`` / ``--zip``) saves a single ``<output>/<model_slug>.zip`` archive containing the same repository-relative paths inside, which can be attached directly to a GitHub issue instead of opening a PR. If ``<output>/<model_slug>.zip`` already exists, you will be prompted to confirm overwrite (``Overwrite existing <model_slug>.zip? [y/N]``).

The utility produces the following three files (either on disk or inside ``<output>/<model_slug>.zip``):

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
2. Alternatively, create an issue on GitHub and attach the generated ``<model_slug>.zip`` archive (or the three generated files).
