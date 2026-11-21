H2_PLATFORMS = ("nexus:H2-1E", "nexus:H2-2E")


def add_submission_arguments(parser, *, team_required=False):
    parser.add_argument("--platform", choices=H2_PLATFORMS, default=H2_PLATFORMS[0],
                        help="Aqora platform (default: nexus:H2-1E).")
    parser.add_argument("--team", required=team_required, type=str.strip,
                        help="Aqora team username or ID for emulator quota.")


def submit_qir(programs, *, platform, team, shots):
    if platform not in H2_PLATFORMS:
        raise ValueError(f"Unsupported Aqora platform: {platform}")
    if not team or not team.strip():
        raise ValueError("An Aqora team is required for submission.")

    from aqora import QPU

    return QPU(platform=platform, as_entity=team.strip()).run(programs, shots=shots)


def wait_for_results(job, expected_count):
    print(f"Waiting for Aqora job {job.job_id}", flush=True)
    job.wait()
    results = job.result_items()
    if sorted(result.index for result in results) != list(range(expected_count)):
        raise ValueError(f"Aqora job {job.job_id} returned unexpected program indices")
    return results
