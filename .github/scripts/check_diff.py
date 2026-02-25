import json
import sys
from typing import Dict

LIB_DIRS_PYTHON = ["libs/langchain-turbopuffer"]
LIB_DIRS_JS = ["libs/langchainjs-turbopuffer"]

LIB_DIRS = LIB_DIRS_PYTHON + LIB_DIRS_JS

if __name__ == "__main__":
    files = sys.argv[1:]

    dirs_to_run: Dict[str, set] = {
        "lint-py": set(),
        "test-py": set(),
        "lint-js": set(),
        "test-js": set(),
    }

    if len(files) == 300:
        # max diff length is 300 files - there are likely files missing
        raise ValueError("Max diff reached. Please manually run CI on changed libs.")

    for file in files:
        if any(
            file.startswith(dir_)
            for dir_ in (
                ".github/workflows",
                ".github/tools",
                ".github/actions",
                ".github/scripts/check_diff.py",
            )
        ):
            # add all dirs for infra changes
            dirs_to_run["test-py"].update(LIB_DIRS_PYTHON)
            dirs_to_run["test-js"].update(LIB_DIRS_JS)

        if any(file.startswith(dir_) for dir_ in LIB_DIRS):
            for dir_ in LIB_DIRS_PYTHON:
                if file.startswith(dir_):
                    dirs_to_run["test-py"].add(dir_)
            for dir_ in LIB_DIRS_JS:
                if file.startswith(dir_):
                    dirs_to_run["test-js"].add(dir_)
        elif file.startswith("libs/"):
            raise ValueError(
                f"Unknown lib: {file}. check_diff.py likely needs "
                "an update for this new library!"
            )

    outputs = {
        "dirs-to-lint-py": list(dirs_to_run["lint-py"] | dirs_to_run["test-py"]),
        "dirs-to-test-py": list(dirs_to_run["test-py"]),
        "dirs-to-lint-js": list(dirs_to_run["lint-js"] | dirs_to_run["test-js"]),
        "dirs-to-test-js": list(dirs_to_run["test-js"]),
    }
    for key, value in outputs.items():
        json_output = json.dumps(value)
        print(f"{key}={json_output}")  # noqa: T201
