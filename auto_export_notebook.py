"""Notebook Exporter
Export the current Jupyter notebook (with cell outputs) to HTML.

Filename rules
--------------
- If a global variable `n_features` exists (int-like) in the *current* kernel
  (i.e., in the `globals()` you pass), the filename is:
      <notebookname>_<n_features>features_<timestamp>.html
- If `n_features` is not present, the filename is:
      <notebookname>_<timestamp>.html
"""

from __future__ import annotations
from pathlib import Path
import datetime
import subprocess
import sys
import time



def _detect_current_notebook_path() -> Path | None:
    """Detect the path of the *current* notebook.
    Strategy:
      1) Use ipynbname if available.
      2) Fallback: most recently modified .ipynb in the CWD.
    """
    try:  # 1) most reliable on local Jupyter
        import ipynbname  # type: ignore
        return Path(ipynbname.path())
    except Exception:
        pass

    # 2) fallback
    try:
        nbs = sorted(
            Path(".").glob("*.ipynb"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        return nbs[0] if nbs else None
    except Exception:
        return None


def _extract_features_count(globals_dict) -> int | None:
    """Return n_features as int if present and int-like; else None.
    Accepts Python ints and NumPy integer types.
    """
    if isinstance(globals_dict, dict) and "n_features" in globals_dict:
        try:
            return int(globals_dict["n_features"])
        except Exception:
            return None
    return None


def _attempt_frontend_save(delay_seconds: float = 1.0) -> None:
    """Ask the Jupyter front-end to save the notebook (classic *and* JupyterLab)."""
    try:
        from IPython.display import Javascript, display  # type: ignore
        js = """
        (async () => {
          try {
            // Classic Notebook
            if (typeof Jupyter !== 'undefined' && Jupyter.notebook) {
              await Jupyter.notebook.save_checkpoint();
            }
            if (typeof IPython !== 'undefined' && IPython.notebook) {
              await IPython.notebook.save_checkpoint();
            }
            // JupyterLab
            if (window && window.jupyterapp && window.jupyterapp.commands) {
              await window.jupyterapp.commands.execute('docmanager:save');
            }
          } catch (e) { /* ignore */ }
        })();
        """
        display(Javascript(js))
        import time as _t
        _t.sleep(delay_seconds)  # give the frontend time to write to disk
    except Exception:
        pass




def export_current_notebook(
    globals_dict=None,
    output_dir: str = "exported_notebooks",
    ensure_save: bool = True,          # kept for compatibility; harmless in VS Code
    save_wait_seconds: float = 1.0,
    notebook_path: str | None = None,  # explicit .ipynb path to avoid auto-detect
    wait_for_disk_save: bool = True,   # wait until the .ipynb mtime updates
    wait_timeout_sec: float = 5.0,     # max wait time for mtime update
    wait_poll_sec: float = 0.25        # polling interval for mtime
) -> str:
    """
    Export the current notebook (with stored outputs) to HTML.

    This function does NOT re-execute the notebook. It converts the .ipynb on disk.
    In VS Code, the front-end JavaScript save hooks are not available, so we
    optionally wait until the file's mtime changes on disk before converting.
    """
    # Resolve the notebook file to convert
    nb_path = Path(notebook_path) if notebook_path else _detect_current_notebook_path()
    if nb_path is None or not nb_path.exists():
        raise FileNotFoundError("Could not detect the current notebook file.")

    # Build the output filename (optionally including n_features from the live kernel)
    features_count = _extract_features_count(globals_dict or {})
    notebook_name = nb_path.stem
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    out_name = (
        f"{notebook_name}_{features_count}features_{ts}.html"
        if features_count is not None else
        f"{notebook_name}_{ts}.html"
    )

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = (out_dir / out_name).absolute()

    # Try a front-end save (no-op in VS Code, but safe everywhere)
    if ensure_save:
        _attempt_frontend_save(delay_seconds=save_wait_seconds)

    # VS Code path: wait until the .ipynb on disk is actually saved/updated
    if wait_for_disk_save:
        try:
            before = nb_path.stat().st_mtime
            deadline = time.time() + wait_timeout_sec
            while time.time() < deadline:
                time.sleep(wait_poll_sec)
                after = nb_path.stat().st_mtime
                if after > before:
                    break  # file was updated on disk
        except Exception:
            # Do not block export if stat() fails; proceed with conversion
            pass

    # Convert to HTML (Lab template + embedded images)
    cmd = [
        sys.executable, "-m", "jupyter", "nbconvert",
        "--to", "html",
        "--template", "lab",
        "--HTMLExporter.embed_images=True",
        "--output", str(out_file),
        str(nb_path),
    ]
    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as e:
        raise RuntimeError(
            f"nbconvert failed with code {e.returncode}\n"
            f"STDOUT:\n{e.stdout}\n\nSTDERR:\n{e.stderr}"
        ) from e

    return str(out_file)
