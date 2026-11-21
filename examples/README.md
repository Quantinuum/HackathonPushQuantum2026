# Tilted-product example

This baseline requires the target thermal observables
$m_x=\langle\sum_i X_i/16\rangle$ and
$\langle m_z^2\rangle=\langle(\sum_i Z_i/16)^2\rangle$ to be known beforehand,
as well as the ability to sample a correlated classical Ising distribution.
It fits the tilt angle to $m_x$ and the classical distribution parameter to
$\langle m_z^2\rangle$; here, both targets come from exact diagonalization at $g=1$.

The method is a simplified, calibrated baseline related to variational thermal
state preparation: it fits known target observables rather than learning the
state from the Hamiltonian and temperature alone. It prepares a separable
approximation, and the exact-data calibration and exhaustive classical sampling
used here do not constitute a generally scalable thermal-state preparation method.

Install the CLI from the repository root, then switch to the `examples/`
directory. The preprocessed files for `T=2.375` are included.

```bash
uv tool install --python 3.12 .
cd examples
compile tilted_product.py --basis x -o results/tilted_product.x.bc
local-sim tilted_product.py --basis y -o results/tilted_product.y.local.json
```

If your shell cannot find the commands, run `uv tool update-shell` and open a
new terminal.

The CLI selects the saved table for the requested basis and measures the
16 qubits returned by `main`. For remote runs, sign in to Aqora and submit with
your team username or ID to use your team's emulator quota.

```bash
uv tool install aqora
aqora login
nexus-emulator tilted_product.py --basis z --team my-team -o results/tilted_product.z.nexus.json
```

You can target `nexus:H2-1E` (the default) or `nexus:H2-2E` with `--platform`.
Both the standalone command and the batch runner accept these two platforms.

Use `submit.py` to run several bases or temperatures and validate the
preparation labels. The Python scripts below use the repository's locked
project environment through `uv run --locked`.

```bash
# Calibrate and sample once (T=2.375; pre-generated files are also included).
uv run --locked preprocessing.py

# Validate the three T=2.375 programs through the H2 checker, without Nexus access.
uv run --locked submit.py --compile-only --output results/compile_check.json

# Noiseless local simulation: T=2.375, three bases, 128 shots each.
uv run --locked submit.py --local

# Submit the three bases to H2-1E through Aqora.
uv run --locked submit.py --team my-team
```

The batch runner saves the Aqora job ID before waiting. It writes
`results/tilted_product_h2_1e.json` by default and
`results/tilted_product_h2_2e.json` with `--platform nexus:H2-2E`. If interrupted,
resume the same job with `uv run --locked submit.py --resume results/tilted_product_h2_1e.json`
or pass the path of your H2-2E manifest.
Use `--temperature 2.375 --basis Z --output results/smoke.json` for one experiment.
The H2 emulators use their default noise models. Local Selene runs are
noiseless and record that in the JSON output.

The files have separate responsibilities:

- `preprocessing.py` loads the spectrum, fits `k` and `theta`, samples 128 whole
  configurations independently for each basis, and saves:
  - `data/parameters_2.375.json`: fitted parameters and sampling seeds.
  - `data/samples_2.375.npz`: X/Y/Z sample labels and packed H2 lookup masks.
- `tilted_product.py` loads the saved data and provides a zero-argument `main`
  that returns the prepared qubits. `uv run --locked tilted_product.py` exports
  one measured HUGR program for H2.
- `submit.py` uses the same measurement wrapper as the CLI. It executes the
  programs locally or on Nexus and saves the results.

To draw a new sample table, run `uv run --locked preprocessing.py --seed 42`. Seed control
belongs to preprocessing, not submission. To preserve the existing table, add
`--output-dir data/seed42` and pass `--data-dir data/seed42` to `submit.py` or
`tilted_product.py`. For another temperature, first preprocess it explicitly, e.g.
`uv run --locked preprocessing.py --temperature 1.1875`.

At runtime, `get_current_shot()` selects the saved configuration. H2 indices
start at 1; Selene indices start at 0. Submit exactly 128 shots with the default
shot numbering. Recompiling or rerunning reuses the saved samples. The emitted
`shot` and `label` outputs are validated when collecting results. Preprocessing
packs the samples into two 64-bit masks per qubit to avoid H2's unsupported
dynamic array indexing; the circuit file only applies those masks and rotations.

For sampled spin s_q=+1 (bit 0), apply Ry(theta); for s_q=-1 (bit 1), apply
Ry(pi-theta). The label distribution is exp[-k E_classical(s)]/Z, where k is a
fitted parameter, not necessarily 1/T. A shot produces a pure product branch;
averaging the independently sampled branches produces the mixture.

The supplied `data/ising_spectra.npz` is a compact subset of the parent project's
exact-diagonalization data: the g=0 computational-basis energies in integer-label
order, and g=1 eigenenergies, symmetry multiplicities, and eigenstate mx/mz2.
Never interpret the g=1 eigenstate index as a computational-basis bitstring.
When preprocessing T=0.01, calibration uses the finite-temperature spectrum;
the earlier T=1e-8 coherent-cat benchmark is not used.

Each JSON experiment records T, basis, calibration parameters, sampled labels,
and 128 measurements, with one shot per line. `bits[q]` corresponds to site
`q=x+4*y`. Bit `b` represents the measured Pauli eigenvalue `1-2*b`.
X readout applies H. Y readout applies S-dagger then H.
All basis settings measure all 16 qubits. The default example uses T=2.375 only:
three bases times 128 shots gives 384 total shots. Other challenge temperatures
can be selected explicitly with `--temperature`.

H2 conversion and submission follow the current
[hugr-qir workflow](https://quantinuum.github.io/hugr-qir/getting-started.html).
The supported subset includes shot indices, fixed loops, and measurement arrays;
see the [H2 support matrix](https://quantinuum.github.io/hugr-qir/guppy-for-h2/support-matrix.html).
