"""Initialize empyrean: download SPICE kernels and load the data dir.

Reproducer for the "Initialize & Data" section of
https://empyrean-dynamics.com/install. The marked region below is the
literal snippet shown in the install page; the surrounding harness is
what makes the file `python install-page/initialize.py`-runnable.

Run:
    pip install empyrean
    python install-page/initialize.py
"""

from __future__ import annotations


def main() -> None:
    # spielberg:snippet:start
    import empyrean
    from empyrean import Epochs, TimeScale, Frame, Origin

    empyrean.download_data()  # first-run only
    empyrean.initialize()
    # spielberg:snippet:end
    _ = (Epochs, TimeScale, Frame, Origin)  # silence "unused"
    print("empyrean initialized OK")


if __name__ == "__main__":
    main()
