import argparse
import time

from praktika.result import Result
from praktika.settings import Settings
from praktika.utils import MetaClasses, Shell, Utils

from jobs.scripts.clickhouse_proc import ClickHouseProc
from jobs.fast_test import update_path_ch_config


class JobStages(metaclass=MetaClasses.WithIter):
    INSTALL_CLICKHOUSE = "Install"
    TEST = "Test"


def parse_args():
    parser = argparse.ArgumentParser(description="ClickHouse Build Job")
    parser.add_argument("BUILD_TYPE", help="Type: <amd|arm_debug|release_sanitizer>")
    parser.add_argument("--param", help="Optional custom job start stage", default=None)
    return parser.parse_args()


def main():

    args = parse_args()

    stop_watch = Utils.Stopwatch()

    stages = list(JobStages)
    stage = args.param or JobStages.INSTALL_CLICKHOUSE
    if stage:
        assert stage in JobStages, f"--param must be one of [{list(JobStages)}]"
        print(f"Job will start from stage [{stage}]")
        while stage in stages:
            stages.pop(0)
        stages.insert(0, stage)

    res = True
    results = []

    Utils.add_to_PATH(f"{Settings.INPUT_DIR}:tests")

    if res and JobStages.INSTALL_CLICKHOUSE in stages:
        commands = [
            f"chmod +x {Settings.INPUT_DIR}/clickhouse",
            f"ln -sf {Settings.INPUT_DIR}/clickhouse {Settings.INPUT_DIR}/clickhouse-server",
            f"ln -sf {Settings.INPUT_DIR}/clickhouse {Settings.INPUT_DIR}/clickhouse-client",
            f"rm -rf {Settings.TEMP_DIR}/etc/ && mkdir -p {Settings.TEMP_DIR}/etc/clickhouse-client {Settings.TEMP_DIR}/etc/clickhouse-server",
            f"cp programs/server/config.xml programs/server/users.xml {Settings.TEMP_DIR}/etc/clickhouse-server/",
            f"tests/config/install.sh {Settings.TEMP_DIR}/etc/clickhouse-server {Settings.TEMP_DIR}/etc/clickhouse-client",
            update_path_ch_config,
            f"clickhouse-server --version",
        ]
        results.append(
            Result.create_from_command_execution(
                name=JobStages.INSTALL_CLICKHOUSE, command=commands
            )
        )
        res = results[-1].is_ok()

    CH = ClickHouseProc()
    if res and JobStages.TEST in stages:
        stop_watch_ = Utils.Stopwatch()
        step_name = "Start ClickHouse Server"
        print(step_name)
        res = res and CH.start_minio()
        res = res and CH.start()
        res = res and CH.wait_ready()
        results.append(
            Result.create_from(name=step_name, status=res, stopwatch=stop_watch_)
        )

    Result.create_from(results=results, stopwatch=stop_watch).complete_job()


if __name__ == "__main__":
    main()
