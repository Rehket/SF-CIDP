import subprocess

import shutil
import os
import sys
from pathlib import Path
from typing import List

from loguru import logger

from config import WORKING_DIR


logger.add(
    "file_{time}.log", format="{time} {level} {message}", level="DEBUG", rotation="5 MB"
)


def execute(cmd: List[str], cwd: str):
    logger.info(f"Executing {cmd} in shell.")
    popen = subprocess.Popen(
        cmd, cwd=Path(WORKING_DIR, cwd), stdout=subprocess.PIPE, universal_newlines=True, shell=True
    )
    for stdout_line in iter(popen.stdout.readline, ""):
        yield stdout_line.strip("\n")
    popen.stdout.close()
    return_code = popen.wait()
    if return_code:
        raise subprocess.CalledProcessError(return_code, cmd)


def pull_git_repo(repo_url: str) -> str:
    dir_name = os.path.split(github_url)[1][0:-4]
    if Path(os.getcwd(), WORKING_DIR, dir_name).exists():
        logger.info(f"Found {dir_name} in working directory. Deleting it.")
        os.rename(Path(os.getcwd(), dir_name), Path(os.getcwd(), dir_name + "_Copy"))
    logger.info(f"Pulling repo for {repo_url}")
    git_clone = subprocess.run(
        ["git", "clone", github_url], cwd=Path(WORKING_DIR), capture_output=True
    )
    if git_clone.returncode:
        logger.error(git_clone.stderr.decode("utf-8").strip("\n").replace("\n", " "))
        sys.exit(git_clone.returncode)

    return dir_name


def checkout_branch(branch: str, repo_dir: str):
    git_branch = subprocess.run(
        ["git", "checkout", branch], cwd=Path(WORKING_DIR, repo_dir), capture_output=True
    )
    if git_branch.returncode:
        logger.error(git_branch.stderr.decode("utf-8").strip("\n").replace("\n", " "))
        sys.exit(git_branch.returncode)

    else:
        logger.info(git_branch.stdout.decode("utf-8").strip("\n").replace("\n", " "))


def get_branches(repo_dir: str) -> List:
    git_branch = subprocess.run(["git", "branch"], cwd=Path(WORKING_DIR, repo_dir), capture_output=True)

    logger.info(git_branch.stdout.decode("utf-8").strip("\n").replace("\n", " "))
    branches = [
        x
        for x in str(
            git_branch.stdout.decode("utf-8").strip("\n").replace("\n", " ")
        ).split()
    ]

    return branches


def checkout_or_create_branch(branch_name: str, branches: List[str], repo_dir: str):
    if branch_name in branches:
        logger.info(f"Retrieving {branch_name}")
        git_new_branch = subprocess.run(
            ["git", "checkout", branch_name], cwd=Path(WORKING_DIR, repo_dir), capture_output=True
        )
        logger(git_new_branch.stdout.decode("utf-8").strip("\n").replace("\n", " "))

    else:
        logger.info(f"Creating {branch_name}")
        git_new_branch = subprocess.run(
            ["git", "checkout", "-b", branch_name], cwd=Path(WORKING_DIR, repo_dir), capture_output=True
        )

    if git_new_branch.returncode:
        logger.error(
            git_new_branch.stderr.decode("utf-8").strip("\n").replace("\n", " ")
        )


def pull_sfdc_code(
    new_files_list: str, sandbox_alias: str, repo_dir: str, metadata_items: List[str] = ["ApexClass"]
):
    """
    Pulls the metadata items from the sandbox
    :param new_files_list:
    :param metadata_items:
    :return:
    """
    # Now Pulling Code

    metadata = ""
    for item in metadata_items:
        metadata += item + ","
    metadata = metadata[:-1]

    with open(new_files_list, "w") as pulled_files:
        count = 0
        for line in execute(
            ["sfdx", "force:source:retrieve", "-u", sandbox_alias, "-m", metadata],
            cwd=Path(os.getcwd(), WORKING_DIR, repo_dir),
        ):
            pulled_files.write(line + "\n")
            count += 1

        logger.info(
            f"retrieved {count} files. File list saved to {Path(os.getcwd(), new_files_list)}"
        )

    git_add_changes = subprocess.run(
        ["git", "add", "."], cwd=Path(os.getcwd(), WORKING_DIR, repo_dir), capture_output=True
    )

    if git_add_changes.returncode:
        logger.error(
            git_add_changes.stderr.decode("utf-8").strip("\n").replace("\n", " ")
        )


def commit_changes(branch_name: str, commit_message: str = None):
    # Checkout Master
    git_commit = subprocess.run(
        [
            "git",
            "commit",
            "-m",
            (
                commit_message
                if commit_message is not None
                else f'"added files from sandbox {branch_name}"'
            ),
        ],
        cwd=Path(WORKING_DIR, dir_name),
        capture_output=True,
    )
    if git_commit.returncode:
        logger.error(git_commit.stderr.decode("utf-8").strip("\n").replace("\n", " "))


def get_changed_files(target_branch: str, dir_name: str) -> List[str]:
    # Checkout Master
    git_diff = subprocess.run(
        ["git", "diff", target_branch, "--name-only"], cwd=Path(WORKING_DIR, dir_name), capture_output=True
    )

    logger.info(git_diff.stdout.decode("utf-8").strip("\n").replace("\n", " "))

    changed_files = str(
        git_diff.stdout.decode("utf-8").strip("\n").replace("\n", " ")
    ).split()

    if len(changed_files) == 0:
        print("There are no Files to migrate.")
        sys.exit()

    return changed_files


def copy_changed_files_and_get_tests(changed_files: List[str], dir_name: str):

    test_classes = []
    for file in changed_files:
        new_path = Path(os.getcwd(), "mdapi", os.path.split(file)[0])
        new_path.mkdir(parents=True, exist_ok=True)

        if file.endswith("-meta.xml"):
            continue
        if (
            file.lower()[0:-4].endswith("test")
            or file.lower()[0:-4].endswith("tc")
            and file.endswith(".cls")
        ):
            # It is a test Class
            test_classes.append(os.path.split(file)[1][0:-4])
        shutil.copy(Path(os.getcwd(), dir_name, file), new_path)
        shutil.copy(Path(os.getcwd(), dir_name, file + "-meta.xml"), new_path)

    if len(test_classes) == 0:
        logger.error("No Test Classes were found. Aborting migration.")
        sys.exit(1)

    logger.info(f"{len(test_classes)} test classes located.")
    return test_classes


def convert_project_to_mdapi():
    # Change CLI to mdapi
    convert_to_metadata = subprocess.run(
        ["sfdx", "force:source:convert", "-r", "force-app", "-d", "mdapi"],
        cwd=Path(WORKING_DIR, "mdapi"),
        capture_output=True,
        shell=True,
    )

    if convert_to_metadata.returncode:
        logger.error(
            convert_to_metadata.stderr.decode("utf-8").strip("\n").replace("\n", " ")
        )


if __name__ == "__main__":
    print("Let's Start!")

    github_url = "https://github.com/Rehket/Errors-In-SalesForce.git"

    dir_name = pull_git_repo(github_url)

    checkout_branch("master", dir_name)

    my_branches = get_branches(dir_name)

    my_branch_name = "DevBox"

    checkout_or_create_branch(my_branch_name, my_branches, dir_name)

    files_list = "new_files_list.txt"

    pull_sfdc_code(files_list, my_branch_name, dir_name, ["ApexClass", "ApexTrigger"])

    # Checkout Master
    commit_changes(my_branch_name)

    target_branch = "master"

    changed_files = get_changed_files(target_branch, dir_name)

    cwd = os.getcwd()
    if Path(cwd, "mdapi").exists():
        shutil.rmtree(Path(cwd, "mdapi"))
    Path(cwd, "mdapi").mkdir(parents=True, exist_ok=True)

    shutil.copy(dir_name + "/sfdx-project.json", Path(cwd, "mdapi"))

    my_test_classes = copy_changed_files_and_get_tests(changed_files, dir_name)

    convert_project_to_mdapi()

    test_class_string = ""
    for test_class in my_test_classes:
        test_class_string += test_class + ","

    test_class_string = test_class_string[0:-1]
    print(test_class_string)

    if len(test_class_string) > 200:

        logger.error(
            "Woah... You are trying to run a bunch of tests... Try making a smaller deployment."
        )
    else:
        for line in execute(
            [
                "sfdx",
                "force:mdapi:deploy",
                "-d",
                "src",
                "-c",
                "-u",
                my_branch_name,
                "-w",
                "10",
                "-l",
                "RunSpecifiedTests",
                "-r",
                test_class_string,
            ],
            cwd="mdapi",
        ):
            logger.info(line)
