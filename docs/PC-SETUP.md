# ELION-PC setup

1. Receive the repository/folder containing `WorkForce/BeserkForce`.
2. Confirm Python 3.11 or newer is available.
   On Windows, install the Python time-zone data with `python -m pip install tzdata` for the selected Python installation.
3. Copy `config/device.elionpc.example.json` to `config/device.local.json`.
4. Keep `.env` local and never commit it.
5. Run `Install-BeserkForce-App.ps1` once. It installs pywebview and a Desktop shortcut.
6. Run `Start-BeserkForce.ps1`. It opens the BeserkForce window. The server stays on `127.0.0.1:8877` and does not open a browser.

The laptop should use `device.laptop.example.json` as its local override. Do
not sync `data/runtime` between machines until the planned signed-device and
conflict-resolution round trip has passed; Git should synchronize code and
contracts, not two live writers' queues.

