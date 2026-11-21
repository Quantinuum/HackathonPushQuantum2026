# Quantinuum Challenge -- PushQuantum Hackathon 2026


## Problem Statement

The goal of this challenge is to develop and implement a practical thermal state preparation algorithm for the current quantum devices.  

The target Hamiltonian is the transverse field Ising (TFI) model on a 4x4 square lattice with periodic boundary conditions.

**TFI Hamiltonian**
```math
H = - \sum_{\langle i,j \rangle} Z_i Z_j - g \sum_{i} X_i .
```

Throughout the challenge, we will study the case where the transverse field strength $g = 1$.
Here $X_i$ and $Z_i$ are Pauli operators.

A quantum thermal state $\rho(T)$ at temperature $T$ is defined as:

```math
\rho(T) = \frac{e^{-H/T}}{Z} \quad \text{with} \quad Z = \text{Tr}(e^{-H/T})
```
We assume that $$k_B = 1$$, where $k_B$ is the Boltzmann constant.


The participants have to come up with quantum algorithms to prepare the thermal states at the given temperatures $T \in [10^{-2}, 1.1875, 2.375, 4]$.
For each state at the given temperature T, measure the state in three different bases: X, Y, and Z, using 128 shots per basis.
Upload all the shots for scoring.

![Squared Z magnetization versus temperature and transverse field for the 4×4 periodic Ising model](docs/images/mz2_temperature_vs_field.png)

The squared magnetization $\langle m_z^2\rangle$, with
$m_z=\frac{1}{16}\sum_i Z_i$, shows ferromagnetic correlations at low temperature
and low transverse field. The dotted line highlights the challenge field $g=1$.
White lines mark constant values of $\langle m_z^2\rangle$ on this finite lattice.




## Motivation 
Many interesting physical phenomena happen at finite temperature and could have potential in applications.
For example, we can consider the follow questions:
- At what temperature does a magnet lose its magnetization?
- How does the conductivity of a material change with temperature?
- Do some quantum phenomenon predicted at zero temperature survive at finite temperature?

To answer these questions, we often need to
(i) prepare thermal states at finite temperature  
(ii) perform time evolution
(iii) measure the expectation values of observables.

Today, we focus on (i) and (iii).


## Requirements and Constraints

- Circuits should use maximum 24 qubits.
- Write Guppy circuit and run on H2-1E or H2-2E emulator to collect shots.
- For each temperature and measurement basis, submit exactly 128 shots.


## Getting Started

Run `uv tool install` from the repository root to make `compile`, `local-sim`,
and `nexus-emulator` available as standalone commands.

```bash
uv tool install --python 3.12 .
```

If your shell cannot find the commands, run `uv tool update-shell` and open a
new terminal. You can then run the commands from any directory. To pick up
changes from your checkout, rerun the install command with `--reinstall`.

Define a module-level, zero-argument `@guppy` function named `main` that returns
`array[qubit, 16]`. Return the prepared system qubits in lattice order
`q = x + 4*y`. The tools measure these qubits in the requested basis and record
the outcomes under the `bits` tag. You can emit diagnostics under other tags.

This minimal `program.py` prepares all 16 qubits in the zero state.

```python
from guppylang import guppy
from guppylang.std.builtins import array
from guppylang.std.quantum import qubit


@guppy
def main() -> array[qubit, 16]:
    return array(qubit() for _ in range(16))
```

```bash
compile program.py --basis x
compile program.py --basis y --format llvm-ir
local-sim program.py --basis z --seed 42
nexus-emulator program.py --basis z --project MyNexusProject
nexus-emulator program.x.bc --project MyNexusProject
```

To use the versions in the repository's lockfile, run `uv sync --locked` from
the repository root and prefix the commands with `uv run --locked`, for example
`uv run --locked compile program.py --basis x`. The scorer and
[tilted-product example](examples/README.md) also use this project environment.

- `compile` targets H2 and writes LLVM bitcode such as `program.x.bc` by
  default. Use `--format llvm-ir` for text QIR such as `program.y.ll`.
- `local-sim` reads the required qubit count from the compiled QIR and uses it
  to run Guppy in Selene, noiseless by default. Its default output includes
  the basis, for example `program.z.local.json`.
- `nexus-emulator` accepts Guppy source or LLVM bitcode. It logs in to Nexus,
  executes on H2-1E using emulator credits, and writes a file such as
  `program.z.nexus.json`. The file records the job ID while the command waits
  for results. Omit `--basis` for bitcode because it already includes measurement.

Default output paths are beside the input file. Use `-o` or `--output` to
choose a path. Both emulators default to 128 shots and accept `--shots`.
Each JSON `results` element is one shot containing ordered `[tag, value]` pairs
on a single line.
Both commands write the measurement outcomes under `bits` as integers `0` and `1`.
For other QIR output layouts, Nexus results that cannot be decoded as Guppy
tags are stored as a serialized pytket `backend_result`. Use the shot values
to build the submission format below.

### Local simulation with noise

Enable depolarizing noise with `--noise-model depolarizing`. Use a separate
output file to keep the ideal and noisy results for comparison.

```bash
local-sim program.py --basis z --noise-model depolarizing --seed 42 -o program.z.noisy.local.json
```

The model uses `p_1q=1e-5` for one-qubit gates, `p_2q=1.4e-4` for two-qubit
gates, `p_meas=1e-3` for measurement, and `p_init=1e-5` for initialization.
The error model uses the `--seed` value when supplied and `123141` otherwise.
Noisy output includes `"noise_model": "depolarizing"`.
[Selene error model guide](https://docs.quantinuum.com/selene/user_guide/error_model.html)


### Submission format

Submit one JSON file per temperature, with the following structure:

```json
{
  "temperature": 2.375,
  "X": [
    [0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1],
    [1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0]
  ],
  "Y": [
    [1, 1, 0, 0, 1, 1, 0, 0, 1, 1, 0, 0, 1, 1, 0, 0],
    [0, 1, 1, 0, 0, 1, 1, 0, 0, 1, 1, 0, 0, 1, 1, 0]
  ],
  "Z": [
    [0, 0, 1, 1, 0, 0, 1, 1, 0, 0, 1, 1, 0, 0, 1, 1],
    [1, 1, 0, 0, 1, 1, 0, 0, 1, 1, 0, 0, 1, 1, 0, 0]
  ]
}
```

This illustrative example shows only two shots per basis. A complete submission
contains **128 rows for each of `X`, `Y`, and `Z` basis measurement**,
with **16 measured bits in each row**.

- `temperature` is the specific target temperatures given.
- Each row is one shot. Column (index) $q=x+4y$ corresponds to lattice site $(x,y)$,
  where $x,y\in\{0,1,2,3\}$.
- A bit $b\in\{0,1\}$ represents the measured Pauli eigenvalue $1-2b$:
  bit 0 means +1 and bit 1 means -1, in the basis specified by the array key.
- Include the 16 system-qubit outcomes only; omit ancilla outcomes.
- Classical preparation labels, shot indices, circuit parameters, and Nexus job
  IDs are not required in the scoring submission. Keep all preparation branches
  together when collecting the shots for a basis, without conditioning on labels.

The example's detailed execution JSON also records preparation labels and job
metadata for debugging. To construct a submission from it, use the experiment's
`temperature` and collect the `bits` arrays from its `measurements` under the
corresponding `basis` key. This is a data-format conversion and requires no new
emulator execution.


### Score formula

We score **30 observables**:
- the single-site expectation value $< X_i >$, $< Y_i >$, and $< Z_i >$
- the two-site expectation value $<X_i X_j>$, $<Y_i Y_j>$, and $<Z_i Z_j>$ for the nine displacements $(d_x, d_y)$
`(0,1), (0,2), (1,0), (1,1), (1,2), (1,3), (2,0), (2,1), (2,2)`.

For each observable, we compute the average over all 128 shots and all 16 sites.
For measured eigenvalues $s_{n,i}^a=1-2b_{n,i}^a$, define

```math
\widehat m_a=\frac{1}{128\cdot16}\sum_{n,i}s_{n,i}^a,
\qquad
\widehat C_a(\mathbf d)=\frac{1}{128\cdot16}\sum_{n,i}s_{n,i}^a s_{n,i+\mathbf d}^a.
```

Sites wrap periodically. Use the nine displacements $(d_x,d_y)$
`(0,1), (0,2), (1,0), (1,1), (1,2), (1,3), (2,0), (2,1), (2,2)`.
Opposite displacements give the same translation average and are counted once.
Directions such as horizontal and vertical remain separate: **no C4 averaging**.
These are raw correlations, without subtracting one-site means.

Compare with the exact Gibbs expectations at the submitted temperature:

```math
\mathrm{score}(T)=9\sum_{a\in\{X,Y,Z\}}(\widehat m_a-m_a^\star(T))^2
+\sum_{a\in\{X,Y,Z\}}\sum_{\mathbf d\in\mathcal D}
(\widehat C_a(\mathbf d)-C_a^\star(\mathbf d,T))^2.
```

Average over sites **before squaring**. Each of the 27 correlation errors has
unit weight; each magnetization error has weight 9. There is no additional
pair-count weighting, square root, or overall normalization. Lower is better.
Spatial averaging reduces sampling noise but can hide spatial inhomogeneity.
The score is an observable-based proxy with a limited role in prize judging;
scalability, applicability, and thermal-state preparation are also considered.

### Running the scorer

From the repository directory:

```bash
uv run --locked score.py submission_2.375.json
# Score multiple temperature files, reporting each separately:
uv run --locked score.py submission_0.01.json submission_1.1875.json submission_2.375.json submission_4.json --output scores.json
# Run the scorer's validation tests:
uv run --locked python -m unittest discover -s tests -v
```

`score.py` accepts the simple submission format above and reports the total score,
the weighted `single_site_score`, and the `pair_correlation_score`. It also
reports the estimated and exact site-averaged magnetizations. It validates
the temperature, all three basis arrays, their 128-by-16 shapes, and integer
outcomes 0 or 1. Nonbinary outcomes are rejected rather than silently converted.
Exact references for all four challenge temperatures are bundled in
`data/reference_g1.npz`; scoring needs only NumPy and does not require a GPU or
access to Nexus. In particular, the first target is evaluated at $T=0.01$, not
the earlier ground-state exploration temperature $10^{-8}$.

