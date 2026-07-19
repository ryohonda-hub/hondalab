#!/usr/bin/env python3
"""
Generate an interactive Sunburst chart from per-file output produced by `du`.

This version is intended for logs created from a NUL-delimited file list, for
example:

    find "$HOME" /work -type f -user "$USER" -print0 > owned_files.list
    du -k --files0-from=owned_files.list > du.log

The input log must contain one file per line in the following form:

    SIZE_IN_KIB    /absolute/path/to/file

Directory sizes are reconstructed by summing the sizes of all files below each
directory. Therefore, multiple top-level locations can be visualized together,
and `--target /` is supported.

Examples
--------
Visualize all files in the log from the filesystem root:

    python plot_du_filelist.py du.log \
        --target / \
        --max-depth 4 \
        --output plot_du.html

Visualize only one user's home directory:

    python plot_du_filelist.py du.log \
        --target /home/ryohonda \
        --max-depth 4 \
        --output plot_home.html

Display all levels:

    python plot_du_filelist.py du.log \
        --target / \
        --max-depth 0 \
        --output plot_du_full.html
"""

from __future__ import annotations

import argparse
import re
from collections import defaultdict
from pathlib import Path

import plotly.graph_objects as go


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Create an interactive Sunburst chart from per-file du output. "
            "Directory sizes are reconstructed automatically."
        )
    )
    parser.add_argument("input", type=Path, help="Per-file output log from du")
    parser.add_argument(
        "--target",
        default="/",
        help="Directory to display (default: /)",
    )
    parser.add_argument(
        "--max-depth",
        type=int,
        default=3,
        help="Maximum directory depth below the target; use 0 for all levels",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("plot_du.html"),
        help="Output HTML file (default: plot_du.html)",
    )
    parser.add_argument("--title", default=None, help="Chart title")
    return parser.parse_args()


def normalize_path(raw_path: str) -> str:
    """Normalize an input path to a slash-separated path without a leading /."""
    raw_path = raw_path.strip()

    if raw_path in ("", ".", "./", "/"):
        return ""

    if raw_path.startswith("./"):
        raw_path = raw_path[2:]

    return raw_path.strip("/")


def normalize_target(target_arg: str) -> tuple[str, str]:
    """Return the normalized target path and a human-readable label."""
    target_arg = target_arg.strip()

    if target_arg in ("", "/"):
        return "", "/"

    if target_arg in (".", "./"):
        return "", "/"

    target = normalize_path(target_arg)
    return target, "/" + target


def parent_path(path: str) -> str:
    if "/" not in path:
        return ""
    return path.rsplit("/", 1)[0]


def basename(path: str) -> str:
    if path == "":
        return "/"
    return path.rsplit("/", 1)[-1]


def depth(path: str) -> int:
    if path == "":
        return 0
    return path.count("/") + 1


def relative_to_target(path: str, target: str) -> str | None:
    if target == "":
        return path
    if path == target:
        return ""
    prefix = target + "/"
    if path.startswith(prefix):
        return path[len(prefix) :]
    return None


def format_size(kib: int) -> str:
    tib = kib / 1024 / 1024 / 1024
    if tib >= 1:
        return f"{tib:,.2f} TiB"

    gib = kib / 1024 / 1024
    if gib >= 1:
        return f"{gib:,.2f} GiB"

    mib = kib / 1024
    if mib >= 1:
        return f"{mib:,.2f} MiB"

    return f"{kib:,} KiB"


def read_file_sizes(path: Path) -> dict[str, int]:
    """Read per-file `du` output as {normalized file path: size in KiB}."""
    file_sizes: dict[str, int] = {}

    with path.open("r", encoding="utf-8", errors="replace") as handle:
        for line_no, line in enumerate(handle, start=1):
            line = line.rstrip("\n")
            if not line.strip():
                continue

            match = re.match(r"^\s*(\d+)\s+(.+?)\s*$", line)
            if not match:
                print(f"Warning: line {line_no} was skipped: {line!r}")
                continue

            size_kib = int(match.group(1))
            normalized = normalize_path(match.group(2))

            if normalized == "":
                print(f"Warning: line {line_no} has no usable file path and was skipped")
                continue

            # If a path occurs more than once, retain one entry rather than double-counting it.
            file_sizes[normalized] = size_kib

    return file_sizes


def aggregate_directory_sizes(
    file_sizes: dict[str, int],
) -> tuple[dict[str, int], dict[str, int]]:
    """
    Reconstruct recursive directory totals and direct-file totals.

    Returns
    -------
    directory_sizes
        Recursive total size for every directory, including the virtual root "".
    direct_file_sizes
        Total size of files stored directly in each directory.
    """
    directory_sizes: defaultdict[str, int] = defaultdict(int)
    direct_file_sizes: defaultdict[str, int] = defaultdict(int)

    for file_path, size_kib in file_sizes.items():
        directory = parent_path(file_path)
        direct_file_sizes[directory] += size_kib

        # Add the file size to its containing directory and every ancestor.
        current = directory
        while True:
            directory_sizes[current] += size_kib
            if current == "":
                break
            current = parent_path(current)

    return dict(directory_sizes), dict(direct_file_sizes)


def build_sunburst_data(
    directory_sizes: dict[str, int],
    direct_file_sizes: dict[str, int],
    target: str,
    target_label: str,
    max_depth: int,
) -> tuple[list[str], list[str], list[str], list[int], list[str]]:
    target_size = directory_sizes[target]

    relative_dirs: dict[str, int] = {}
    for full_path, size in directory_sizes.items():
        rel = relative_to_target(full_path, target)
        if rel is not None:
            relative_dirs[rel] = size

    displayed_dirs = {
        rel: size
        for rel, size in relative_dirs.items()
        if rel == "" or max_depth == 0 or depth(rel) <= max_depth
    }
    displayed_dirs[""] = target_size

    ids: list[str] = []
    labels: list[str] = []
    parents: list[str] = []
    values: list[int] = []
    customdata: list[str] = []

    sorted_dirs = sorted(
        displayed_dirs.items(), key=lambda item: (depth(item[0]), item[0].lower())
    )

    for rel, size in sorted_dirs:
        if rel == "":
            node_id = "__root__"
            label = target_label
            parent_id = ""
        else:
            node_id = "dir:" + rel
            label = basename(rel)
            rel_parent = parent_path(rel)
            parent_id = "__root__" if rel_parent == "" else "dir:" + rel_parent

        ids.append(node_id)
        labels.append(label)
        parents.append(parent_id)
        values.append(size)
        customdata.append(format_size(size))

    # Add a [direct files] node for files located immediately in each displayed
    # directory. At max depth, the whole directory remains a leaf, so a direct
    # files child is intentionally omitted.
    for rel, _ in sorted_dirs:
        if max_depth != 0 and depth(rel) >= max_depth:
            continue

        full_dir = target if rel == "" else (f"{target}/{rel}" if target else rel)
        direct_size = direct_file_sizes.get(full_dir, 0)
        if direct_size <= 0:
            continue

        parent_id = "__root__" if rel == "" else "dir:" + rel
        ids.append(f"direct:{rel or '__root__'}")
        labels.append("[direct files]")
        parents.append(parent_id)
        values.append(direct_size)
        customdata.append(format_size(direct_size))

    return ids, labels, parents, values, customdata


def main() -> None:
    args = parse_args()

    if not args.input.exists():
        raise SystemExit(f"Error: input file was not found: {args.input}")
    if args.input.stat().st_size == 0:
        raise SystemExit(f"Error: input file is empty: {args.input}")
    if args.max_depth < 0:
        raise SystemExit("Error: --max-depth must be 0 or a positive integer")

    file_sizes = read_file_sizes(args.input)
    if not file_sizes:
        raise SystemExit(f"Error: no valid file records were found in {args.input}")

    directory_sizes, direct_file_sizes = aggregate_directory_sizes(file_sizes)
    target, target_label = normalize_target(args.target)

    if target not in directory_sizes:
        raise SystemExit(
            f"Error: target '{target_label}' was not reconstructed from {args.input}. "
            "Confirm that the log contains files below this directory."
        )

    ids, labels, parents, values, customdata = build_sunburst_data(
        directory_sizes=directory_sizes,
        direct_file_sizes=direct_file_sizes,
        target=target,
        target_label=target_label,
        max_depth=args.max_depth,
    )

    if args.title:
        title = args.title
    else:
        depth_text = "all levels" if args.max_depth == 0 else f"through level {args.max_depth}"
        title = f"{target_label}: disk usage {depth_text}"

    fig = go.Figure(
        go.Sunburst(
            ids=ids,
            labels=labels,
            parents=parents,
            values=values,
            branchvalues="total",
            customdata=customdata,
            hovertemplate=(
                "<b>%{label}</b><br>"
                "Size: %{customdata}<br>"
                "Share of parent: %{percentParent:.2%}<br>"
                "Share of total: %{percentRoot:.2%}"
                "<extra></extra>"
            ),
            insidetextorientation="radial",
            maxdepth=-1,
        )
    )

    fig.update_layout(
        title={"text": title, "x": 0.5, "xanchor": "center"},
        margin={"t": 80, "l": 20, "r": 20, "b": 20},
        height=900,
    )

    fig.write_html(args.output, include_plotlyjs="cdn", full_html=True)

    target_size = directory_sizes[target]
    print(f"Saved: {args.output}")
    print(f"Target: {target_label}")
    print(f"Total: {format_size(target_size)}")
    print("Displayed depth: " + ("all levels" if args.max_depth == 0 else str(args.max_depth)))
    print(f"Files read: {len(file_sizes):,}")
    print(f"Nodes: {len(ids):,}")


if __name__ == "__main__":
    main()
