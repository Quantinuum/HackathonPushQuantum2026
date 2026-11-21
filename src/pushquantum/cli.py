import argparse
import sys
from contextlib import contextmanager
from importlib.machinery import SourceFileLoader
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

from pushquantum.nexus import add_submission_arguments, submit_qir, wait_for_results
from pushquantum.program import BASES, RunConfig, current_run, with_measurement
from pushquantum.results import write_json


def command(description, input_help, *, basis_required=True):
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument("input", type=Path, help=input_help)
    parser.add_argument("--basis", type=str.lower, choices=BASES, required=basis_required,
                        help="Measurement basis (required for Guppy source).")
    parser.add_argument("-o", "--output", type=Path, help="Set the output path.")
    return parser


def paths(parser, args, default_suffix, *, guppy_only=True):
    source = args.input
    if not source.is_file():
        parser.error(f"Input file does not exist: {source}")
    if guppy_only and source.suffix.lower() != ".py":
        parser.error("Input must be a Python (.py) file.")
    basis_suffix = f".{args.basis}" if args.basis else ""
    output = args.output or source.with_suffix(basis_suffix + default_suffix)
    if output.resolve() == source.resolve() or (output.exists() and output.samefile(source)):
        parser.error("Input and output must be different files.")
    return source, output


def positive_int(value):
    number = int(value)
    if number < 1:
        raise argparse.ArgumentTypeError("Expected a positive integer.")
    return number


@contextmanager
def measured_program(source, basis, *, shot_offset, shots=128):
    from guppylang.defs import GuppyFunctionDefinition

    source = source.resolve()
    module_name = "_pushquantum_input"
    loader = SourceFileLoader(module_name, str(source))
    spec = spec_from_file_location(module_name, source, loader=loader)
    module = module_from_spec(spec)
    sys.modules[module_name] = module
    source_dir = str(source.parent)
    sys.path.insert(0, source_dir)
    token = current_run.set(RunConfig(basis, shot_offset, shots))
    try:
        loader.exec_module(module)
        main = getattr(module, "main", None)
        if not isinstance(main, GuppyFunctionDefinition):
            raise SystemExit(
                f"{source} must define a zero-argument Guppy main returning array[qubit, 16]."
            )
        yield with_measurement(main, basis)
    finally:
        current_run.reset(token)
        sys.path.remove(source_dir)
        del sys.modules[module_name]


def qir_entrypoint(module):
    from pyqir import is_entry_point

    entries = [function for function in module.functions if is_entry_point(function)]
    if len(entries) != 1:
        raise SystemExit("Expected QIR with exactly one entry point.")
    return entries[0]


def shot_results(result, *, integer_bits=False):
    shots = []
    for shot in result.results:
        entries = []
        for tag, value in shot.entries:
            if integer_bits and tag == "bits" and isinstance(value, list):
                value = [int(bit) if isinstance(bit, bool) else bit for bit in value]
            entries.append((tag, value))
        shots.append(entries)
    return shots


def compile_main():
    parser = command("Compile Guppy to QIR.", "Python file defining a Guppy main.")
    parser.add_argument(
        "--format", "--output-format", choices=("bitcode", "llvm-ir"), default="bitcode",
        help="QIR format (default: bitcode).",
    )
    args = parser.parse_args()
    suffix = ".bc" if args.format == "bitcode" else ".ll"
    source, output = paths(parser, args, suffix)

    from hugr_qir.hugr_to_qir import hugr_to_qir
    from hugr_qir.output import OutputFormat

    with measured_program(source, args.basis, shot_offset=1) as main:
        qir = hugr_to_qir(main.compile(), output_format=OutputFormat(args.format))
    output.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(qir, bytes):
        output.write_bytes(qir)
    else:
        output.write_text(qir, encoding="utf-8")
    print(f"Wrote {output}")


def local_sim_main():
    parser = command("Run a Guppy program in the local Selene emulator.",
                     "Python file defining a Guppy main.")
    parser.add_argument("--shots", type=positive_int, default=128, help="Shot count (default: 128).")
    parser.add_argument("--seed", type=int, help="Random seed for the emulator.")
    parser.add_argument("--noise-model", choices=("ideal", "depolarizing"), default="ideal",
                        help="Selene noise model (default: ideal).")
    args = parser.parse_args()
    source, output = paths(parser, args, ".local.json")

    from hugr_qir.hugr_to_qir import to_qir_str
    from pyqir import Context, Module, required_num_qubits

    with measured_program(source, args.basis, shot_offset=0, shots=args.shots) as main:
        ir = to_qir_str(main.compile())
        entry = qir_entrypoint(Module.from_ir(Context(), ir))
        qubits = required_num_qubits(entry)
        if qubits is None:
            raise SystemExit("QIR entry point does not declare its required qubit count.")
        emulator = main.emulator(n_qubits=qubits).with_shots(args.shots).with_seed(args.seed)
        if args.noise_model == "depolarizing":
            from selene_sim import DepolarizingErrorModel

            error_model = DepolarizingErrorModel(
                random_seed=123141 if args.seed is None else args.seed,
                p_1q=1e-5,
                p_2q=1.4e-4,
                p_meas=1e-3,
                p_init=1e-5,
            )
            emulator = emulator.with_error_model(error_model)
        result = emulator.run()

    document = {"backend": "Selene", "basis": args.basis, "qubits": qubits, "shots": args.shots}
    if args.noise_model == "depolarizing":
        document["noise_model"] = args.noise_model
    document["results"] = shot_results(result)
    write_json(output, document)
    print(f"Wrote {output}")


def nexus_emulator_main():
    parser = command("Run a program on a Nexus H2 emulator through Aqora.",
                     "Python file defining a Guppy main, or QIR bitcode.", basis_required=False)
    parser.add_argument("--shots", type=positive_int, default=128, help="Shot count (default: 128).")
    add_submission_arguments(parser, team_required=True)
    args = parser.parse_args()
    is_source = args.input.suffix.lower() == ".py"
    if is_source and args.basis is None:
        parser.error("--basis is required for Guppy source.")
    if not is_source and args.basis is not None:
        parser.error("Omit --basis for QIR bitcode, which already contains the measurement.")
    source, output = paths(parser, args, ".nexus.json", guppy_only=False)

    if is_source:
        from hugr_qir.hugr_to_qir import to_qir_bytes

        with measured_program(source, args.basis, shot_offset=1, shots=args.shots) as main:
            qir = to_qir_bytes(main.compile())
    else:
        from pyqir import Context, Module

        qir = source.read_bytes()
        try:
            module = Module.from_bitcode(Context(), qir)
        except ValueError as error:
            parser.error(f"Expected LLVM bitcode: {error}")
        qir_entrypoint(module)

    from hugr_qir.h2_helpers.results import ResultConversionError, backendresult_to_qsysresult

    output.parent.mkdir(parents=True, exist_ok=True)
    job = submit_qir(qir, platform=args.platform, team=args.team, shots=args.shots)
    document = {"backend": args.platform.removeprefix("nexus:"), "shots": args.shots,
                "platform": args.platform, "team": args.team, "job_id": job.job_id,
                "status": "submitted"}
    if is_source:
        document["basis"] = args.basis
    write_json(output, document)
    provider_result, = wait_for_results(job, expected_count=1)
    result = provider_result.to_backend_result()
    backend_result = result.to_dict()
    if "shots" in backend_result:
        try:
            document["results"] = shot_results(backendresult_to_qsysresult(result), integer_bits=True)
        except ResultConversionError:
            document["backend_result"] = backend_result
    else:
        document["backend_result"] = backend_result
    document.update(result_index=provider_result.index, status="completed")
    write_json(output, document)
    print(f"Wrote {output}")
