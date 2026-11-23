#!/bin/bash
# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# Creates a pip-enabled .venv for a Managed MLflow notebook and registers a
# Jupyter kernel for it. Works on Linux (local or remote SSH workstation) and
# macOS (including the stock bash 3.2).
#
# Usage:
#   setup_venv.sh --project-dir DIR [--python 3.13] [--kernel-name NAME]
#                 [--display-name "Display Name"] [-- EXTRA_PACKAGE ...]
#
# Safe to rerun: an existing .venv with the requested Python minor version is
# reused (and repaired if it lacks pip).

set -euo pipefail

project_dir=""
python_version="3.13"  # Managed Spark serverless runtime 4.0 executors.
kernel_name="managed-mlflow"
display_name=""
extra_packages=()

die() {
  echo "ERROR: $*" >&2
  exit 1
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --project-dir) project_dir="$2"; shift 2 ;;
    --python) python_version="$2"; shift 2 ;;
    --kernel-name) kernel_name="$2"; shift 2 ;;
    --display-name) display_name="$2"; shift 2 ;;
    --) shift; extra_packages=("$@"); break ;;
    -h|--help) sed -n '16,25p' "$0"; exit 0 ;;
    *) die "Unknown argument: $1 (put extra packages after --)" ;;
  esac
done

[[ -n "${project_dir}" ]] || die "--project-dir is required."
[[ -n "${display_name}" ]] || display_name="Python ${python_version} (${kernel_name})"
[[ "${kernel_name}" =~ ^[A-Za-z0-9._-]+$ ]] \
  || die "--kernel-name may only contain letters, digits, '.', '_' and '-'."

os_name="$(uname -s)"

# Refuse shared source-mount paths whose top-level packages (e.g. calendar) can
# shadow the Python standard library. Check before mkdir and after resolving
# symlinks.
refuse_source_mount() {
  case "$1" in
    /google/src/*|/google_src/*|/Volumes/google/src/*)
      die "$1 is inside a shared source mount whose packages can shadow the Python standard library. Use a local directory such as \$HOME/<project>." ;;
  esac
}
refuse_source_mount "${project_dir}"
mkdir -p "${project_dir}"
project_dir="$(cd "${project_dir}" && pwd -P)"
refuse_source_mount "${project_dir}"

# Run everything from the project dir so the caller's working directory is not on sys.path.
cd "${project_dir}"

uv_bin="$(command -v uv || true)"
if [[ -z "${uv_bin}" ]]; then
  # uv's installer puts it in ~/.local/bin, which a fresh shell may not have on
  # PATH yet.
  for candidate in "${HOME}/.local/bin/uv" "${HOME}/.cargo/bin/uv" /opt/homebrew/bin/uv /usr/local/bin/uv; do
    if [[ -x "${candidate}" ]]; then uv_bin="${candidate}"; break; fi
  done
fi
if [[ -z "${uv_bin}" ]]; then
  if [[ "${os_name}" == "Darwin" ]]; then
    die "uv not found. Install it with 'brew install uv' (or 'curl -LsSf https://astral.sh/uv/install.sh | sh') and rerun."
  fi
  die "uv not found. Install it with 'curl -LsSf https://astral.sh/uv/install.sh | sh' (adds ~/.local/bin/uv) and rerun."
fi

venv_python="${project_dir}/.venv/bin/python"

if [[ -e "${venv_python}" || -L "${venv_python}" ]]; then
  # A .venv copied or synced from another machine (Linux <-> macOS) has a
  # python symlink or binary that doesn't run here.
  if ! current="$("${venv_python}" -c 'import sys; print(f"{sys.version_info[0]}.{sys.version_info[1]}")' 2>/dev/null)"; then
    die ".venv/bin/python doesn't run on this machine (was the .venv created on another machine, e.g. Linux vs. macOS?). Remove ${project_dir}/.venv and rerun."
  fi
  if [[ "${current}" != "${python_version}" ]]; then
    die ".venv uses Python ${current}, not ${python_version}. Remove ${project_dir}/.venv and rerun."
  fi
  echo "Reusing existing .venv (Python ${current})."
else
  echo "Creating .venv with Python ${python_version}..."
  # --python-preference managed: use a uv-managed CPython (downloaded if
  # needed) so Linux and macOS get the same interpreter version instead of
  # whatever Homebrew, Xcode, or the OS provides.
  "${uv_bin}" venv --seed --python "${python_version}" --python-preference managed .venv
fi

# --seed only applies at creation; also repair .venvs made without it, so the
# notebook's %pip cells work. The ${arr[@]+...} form keeps an empty array from
# tripping `set -u` on macOS bash 3.2.
"${uv_bin}" pip install --python "${venv_python}" pip ipykernel google-cloud-managed-mlflow \
  ${extra_packages[@]+"${extra_packages[@]}"}

"${venv_python}" -m ipykernel install --user \
  --name "${kernel_name}" --display-name "${display_name}"

echo
echo "=== Verification ==="
"${venv_python}" -m pip --version
"${venv_python}" -c 'import ipykernel, mlflow; print("ipykernel", ipykernel.__version__); print("mlflow", mlflow.__version__)'

# macOS xgboost wheels link @rpath/libomp.dylib and don't bundle OpenMP, so
# `import xgboost` fails until libomp is installed. Install it with Homebrew
# when Homebrew is already there; never install Homebrew itself (see SKILL.md).
if "${venv_python}" -c 'import importlib.util, sys; sys.exit(0 if importlib.util.find_spec("xgboost") else 1)'; then
  if ! "${venv_python}" -c 'import xgboost; print("xgboost", xgboost.__version__)'; then
    [[ "${os_name}" == "Darwin" ]] || die "xgboost is installed in .venv but fails to import (see the error above)."
    brew_bin="$(command -v brew || true)"
    for candidate in /opt/homebrew/bin/brew /usr/local/bin/brew; do
      if [[ -z "${brew_bin}" && -x "${candidate}" ]]; then brew_bin="${candidate}"; fi
    done
    [[ -n "${brew_bin}" ]] \
      || die "xgboost can't load libomp.dylib on macOS and Homebrew (brew) wasn't found. Install Homebrew and run 'brew install libomp', or use the kernel fallback in SKILL.md (macOS: missing Homebrew / libomp)."
    echo "xgboost needs libomp on macOS; installing it with ${brew_bin}..."
    "${brew_bin}" install libomp
    "${venv_python}" -c 'import xgboost; print("xgboost", xgboost.__version__)' \
      || die "xgboost still can't load libomp after 'brew install libomp'."
  fi
fi

# Ask Jupyter where user kernelspecs live: ~/.local/share/jupyter on Linux,
# ~/Library/Jupyter on macOS. ipykernel lowercases the kernel directory name.
kernel_json="$("${venv_python}" -c 'import os, sys; from jupyter_core.paths import jupyter_data_dir; print(os.path.join(jupyter_data_dir(), "kernels", sys.argv[1].lower(), "kernel.json"))' "${kernel_name}")"
[[ -f "${kernel_json}" ]] || die "Kernelspec was not written to ${kernel_json}."
echo "Kernelspec: ${kernel_json}"
echo "Kernel display name: ${display_name}"
echo "Host: $(hostname) (${os_name}). The kernel exists only on this machine."
echo "Done. Select '${display_name}' as the notebook kernel."
