from pathlib import Path
from typing import List
from prefect import task as prefect_task
from loguru import logger
import os
import subprocess
import sys

working_dir = os.environ.get("WORKING_DIR", "working_dir")


@prefect_task
def pull_git_repo(repo_url: str) -> str:
    """
    Pulls the repo of the provided URL
    :param repo_url: The URL for the repo.
    :return: The name of the directory where the git repo was vreated.
    """
    dir_name = os.path.split(repo_url)[1][0:-4]

    #  If the directory already exists, delete it.
    if Path(os.getcwd(), working_dir, dir_name).exists():
        logger.info(f"Found {dir_name} in working directory. Deleting it.")
        os.rename(Path(os.getcwd(), dir_name), Path(os.getcwd(), dir_name + "_Copy"))

    logger.info(f"Pulling repo for {repo_url}")

    git_clone = subprocess.run(
        ["git", "clone", repo_url], cwd=Path(working_dir), capture_output=True
    )

    if git_clone.returncode:
        err_msg = git_clone.stderr.decode("utf-8").strip("\n").replace("\n", " ")
        logger.error(err_msg)
        raise RuntimeError(err_msg)

    return dir_name


@prefect_task
def checkout_branch(branch: str, repo_dir: str):
    """
    Check out the branch from git
    :param branch: What branch do you want to check out?
    :param repo_dir: What directory contains the repo?
    :return:
    """

    git_branch = subprocess.run(
        ["git", "checkout", branch],
        cwd=Path(working_dir, repo_dir),
        capture_output=True,
    )
    if git_branch.returncode:
        err_msg = git_branch.stderr.decode("utf-8").strip("\n").replace("\n", " ")
        logger.error(err_msg)
        raise RuntimeError(err_msg)

    else:
        logger.info(git_branch.stdout.decode("utf-8").strip("\n").replace("\n", " "))


@prefect_task
def get_branches(repo_dir: str) -> List:
    """
    Get the branches in the repo.
    :param repo_dir: The repo directory.
    :return: A list of the branches.
    """
    git_branch = subprocess.run(
        ["git", "branch"], cwd=Path(working_dir, repo_dir), capture_output=True
    )

    if git_branch.returncode:
        err_msg = git_branch.stderr.decode("utf-8").strip("\n").replace("\n", " ")
        logger.error(err_msg)
        raise RuntimeError(err_msg)

    logger.info(git_branch.stdout.decode("utf-8").strip("\n").replace("\n", " "))
    branches = [
        x
        for x in str(
            git_branch.stdout.decode("utf-8").strip("\n").replace("\n", " ")
        ).split()
    ]
    return branches


# Throw exceptions rather than exit?
@prefect_task
def create_branch(branch_name: str, repo_dir: str):
    """
    Create a branch in the repo.
    :param branch_name: The branch to create
    :param repo_dir: The directory of the repo
    :return:
    """

    logger.info(f"Creating {branch_name}")
    git_new_branch = subprocess.run(
        ["git", "checkout", "-b", branch_name],
        cwd=Path(working_dir, repo_dir),
        capture_output=True,
    )
    logger(git_new_branch.stdout.decode("utf-8").strip("\n").replace("\n", " "))

    # If error, write it out.
    if git_new_branch.returncode:
        err_msg = git_new_branch.stderr.decode("utf-8").strip("\n").replace("\n", " ")
        logger.error(err_msg)
        raise RuntimeError(err_msg)

    else:
        logger.info(
            git_new_branch.stdout.decode("utf-8").strip("\n").replace("\n", " ")
        )


@prefect_task
def stage_files(repo_dir: str):

    """
    Stage the modified files in the repo.
    :param repo_dir: The directory of the repo.
    :return:
    """
    git_add_changes = subprocess.run(
        ["git", "add", "."],
        cwd=Path(os.getcwd(), working_dir, repo_dir),
        capture_output=True,
    )

    if git_add_changes.returncode:
        err_msg = git_add_changes.stderr.decode("utf-8").strip("\n").replace("\n", " ")
        logger.error(err_msg)
        raise RuntimeError(err_msg)

    logger.info(git_add_changes.stdout.decode("utf-8").strip("\n").replace("\n", " "))


@prefect_task
def commit_changes(dir_name: str, commit_message: str = None):

    """
    Commit changed files in the repo.
    :param dir_name: The directory of the repo.
    :param commit_message: The commit message.
    :return:
    """
    git_commit = subprocess.run(
        [
            "git",
            "commit",
            "-m",
            (commit_message if commit_message is not None else f'"commited files"'),
        ],
        cwd=Path(working_dir, dir_name),
        capture_output=True,
    )

    if git_commit.returncode:
        err_msg = git_commit.stderr.decode("utf-8").strip("\n").replace("\n", " ")
        logger.error(err_msg)
        raise RuntimeError(err_msg)

    logger.info(git_commit.stdout.decode("utf-8").strip("\n").replace("\n", " "))


@prefect_task
def get_changed_files(
    target_branch: str,
    dir_name: str,
    diff_filter: str = "ADM",
    source_branch: str = None,
) -> List[str]:

    if source_branch is None:
        git_diff = subprocess.run(
            [
                "git",
                "diff",
                target_branch,
                "--name-only",
                f"--diff-filter={diff_filter}",
            ],
            cwd=Path(working_dir, dir_name),
            capture_output=True,
        )

    else:
        git_diff = subprocess.run(
            [
                "git",
                "diff",
                "--name-only",
                f"--diff-filter={diff_filter}",
                source_branch,
                target_branch,
            ],
            cwd=Path(working_dir, dir_name),
            capture_output=True,
        )

    if git_diff.returncode:
        err_msg = git_diff.stderr.decode("utf-8").strip("\n").replace("\n", " ")
        logger.error(err_msg)
        raise RuntimeError(err_msg)

    diff_result = git_diff.stdout.decode("utf-8").strip("\n").replace("\n", " ")
    logger.info(diff_result)

    changed_files = str(diff_result).split()

    if len(changed_files) == 0:
        logger.info(f"There are no changed according to filter {diff_filter}")

    return changed_files


@prefect_task
def git_init(project_dir: str):

    init_git = subprocess.run(
        ["git", "init"],
        cwd=Path(working_dir, project_dir),
        capture_output=True,
        shell=True,
    )

    if init_git.returncode:
        err_msg = init_git.stderr.decode("utf-8").strip("\n").replace("\n", " ")
        logger.error(err_msg)
        raise RuntimeError(err_msg)

    else:
        logger.warning(init_git.stdout.decode("utf-8").strip("\n").replace("\n", " "))


@prefect_task
def git_add(project_dir: str, target_str: str = "."):

    #  Add the items to the repo.
    add_files = subprocess.run(
        ["git", "add", f"{target_str}"],
        cwd=Path(working_dir, project_dir),
        capture_output=True,
        shell=True,
    )

    if add_files.returncode:
        err_msg = add_files.stderr.decode("utf-8").strip("\n").replace("\n", " ")
        logger.error(err_msg)
        raise RuntimeError(err_msg)

    logger.info(add_files.stdout.decode("utf-8").strip("\n").replace("\n", " "))


@prefect_task
def git_set_remote(project_dir: str, remote_url: str):

    #  Add the items to the repo.
    set_remote = subprocess.run(
        ["git", "remote", "add", "origin", f"{remote_url}"],
        cwd=Path(working_dir, project_dir),
        capture_output=True,
        shell=True,
    )

    if set_remote.returncode:
        err_msg = set_remote.stderr.decode("utf-8").strip("\n").replace("\n", " ")
        logger.error(err_msg)
        raise RuntimeError(err_msg)

    logger.info(set_remote.stdout.decode("utf-8").strip("\n").replace("\n", " "))

