"""Combine three tagged-shot result files into one temperature submission.

Run from examples/: uv run --locked example_combine.py --temperature 2.375
Use --x, --y, and --z to select different local or Nexus result files.
"""

import argparse
import json
import math
from pathlib import Path


def load_bits(path, basis):
    result = json.loads(path.read_text())
    if "basis" in result and str(result["basis"]).upper() != basis:
        raise ValueError(f"{path}: basis does not match {basis}")
    try:
        rows = [dict(shot)["bits"] for shot in result["results"]]
    except (KeyError, TypeError, ValueError) as error:
        raise ValueError(f"{path}: expected results containing a 'bits' tag per shot") from error
    if len(rows) != 128 or any(not isinstance(row, list) or len(row) != 16 for row in rows):
        raise ValueError(f"{path}: expected 128 shots with 16 bits each")
    if any(type(bit) is not int or bit not in (0, 1) for row in rows for bit in row):
        raise ValueError(f"{path}: expected integer bits 0 or 1")
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--temperature", type=float, default=2.375,
                        help="Target temperature used for all three runs (default: 2.375)")
    for basis in "xyz":
        parser.add_argument(f"--{basis}", type=Path,
                            default=Path(f"tilted_product.{basis}.local.json"))
    parser.add_argument("-o", "--output", type=Path)
    args = parser.parse_args()
    output = args.output or Path(f"submission_{args.temperature:g}.json")
    inputs = {basis: getattr(args, basis.lower()) for basis in "XYZ"}
    if not math.isfinite(args.temperature) or args.temperature <= 0:
        parser.error("temperature must be finite and positive")
    if output.resolve() in {path.resolve() for path in inputs.values()}:
        parser.error("output must differ from the three input files")
    try:
        submission = {"temperature": args.temperature,
                      **{basis: load_bits(path, basis) for basis, path in inputs.items()}}
        output.parent.mkdir(parents=True, exist_ok=True)
        with output.open("x") as stream:
            stream.write('{\n  "temperature": ' + json.dumps(args.temperature) + ',\n')
            for basis in "XYZ":
                stream.write(f'  "{basis}": [\n')
                stream.write(",\n".join("    " + json.dumps(row) for row in submission[basis]))
                stream.write("\n  ]" + ("," if basis != "Z" else "") + "\n")
            stream.write("}\n")
    except (OSError, ValueError, TypeError) as error:
        parser.exit(2, f"{error}\n")
    print(f"Wrote {output}: T={args.temperature:g}, 128 shots per basis")


if __name__ == "__main__":
    main()
