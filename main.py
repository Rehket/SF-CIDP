import subprocess

import shutil
import os
import sys
import json
from pathlib import Path
from typing import List

from loguru import logger

import config
from config import SalesForceInstance

logger.add(
    sys.stdout, format="{time} {level} {message}", level="DEBUG"
)


def execute(cmd: List[str], cwd: str):
    """
    Execute commands in a shell and pipe them to stdout
    :param cmd: Commands to run in a list of strings
    :param cwd: the working diirectory to execute the commands in.
    :return:
    """
    logger.info(f"Executing {cmd} in shell.")
    popen = subprocess.Popen(
        cmd, cwd=Path(config.WORKING_DIR, cwd), stdout=subprocess.PIPE, universal_newlines=True, shell=True
    )
    for stdout_line in iter(popen.stdout.readline, ""):
        yield stdout_line.strip("\n")
    popen.stdout.close()
    return_code = popen.wait()
    if return_code:
        raise subprocess.CalledProcessError(return_code, cmd)


def pull_git_repo(repo_url: str) -> str:
    """
    Pulls the repo of the provided URL
    :param repo_url: The URL for the repo.
    :return: The name of the directory where the git repo was vreated.
    """
    dir_name = os.path.split(repo_url)[1][0:-4]

    #  If the directory already exists, delete it.
    if Path(os.getcwd(), config.WORKING_DIR, dir_name).exists():
        logger.info(f"Found {dir_name} in working directory. Deleting it.")
        os.rename(Path(os.getcwd(), dir_name), Path(os.getcwd(), dir_name + "_Copy"))

    logger.info(f"Pulling repo for {repo_url}")

    git_clone = subprocess.run(
        ["git", "clone", repo_url], cwd=Path(config.WORKING_DIR), capture_output=True
    )

    if git_clone.returncode:
        logger.error(git_clone.stderr.decode("utf-8").strip("\n").replace("\n", " "))
        sys.exit(git_clone.returncode)

    return dir_name


def checkout_branch(branch: str, repo_dir: str):
    """
    Check out the branch from git
    :param branch: What branch do you want to check out?
    :param repo_dir: What directory contains the repo?
    :return:
    """
    git_branch = subprocess.run(
        ["git", "checkout", branch], cwd=Path(config.WORKING_DIR, repo_dir), capture_output=True
    )
    if git_branch.returncode:
        logger.error(git_branch.stderr.decode("utf-8").strip("\n").replace("\n", " "))
        sys.exit(git_branch.returncode)

    else:
        logger.info(git_branch.stdout.decode("utf-8").strip("\n").replace("\n", " "))


def get_branches(repo_dir: str) -> List:
    """
    Get the branches in the repo.
    :param repo_dir: The repo directory.
    :return: A list of the branches.
    """
    git_branch = subprocess.run(["git", "branch"], cwd=Path(config.WORKING_DIR, repo_dir), capture_output=True)

    logger.info(git_branch.stdout.decode("utf-8").strip("\n").replace("\n", " "))
    branches = [
        x
        for x in str(
            git_branch.stdout.decode("utf-8").strip("\n").replace("\n", " ")
        ).split()
    ]
    return branches

def create_branch(branch_name: str, repo_dir: str):
    """
    Create a branch in the repo.
    :param branch_name: The branch to create
    :param repo_dir: The directory of the repo
    :return:
    """

    logger.info(f"Creating {branch_name}")
    git_new_branch = subprocess.run(
        ["git", "checkout", "-b", branch_name], cwd=Path(config.WORKING_DIR, repo_dir), capture_output=True
    )
    logger(git_new_branch.stdout.decode("utf-8").strip("\n").replace("\n", " "))
    ## If error, write it out.
    if git_new_branch.returncode:
        logger.error(git_new_branch.stderr.decode("utf-8").strip("\n").replace("\n", " "))
        sys.exit(git_new_branch.returncode)

    else:
        logger.info(git_new_branch.stdout.decode("utf-8").strip("\n").replace("\n", " "))

def pull_sfdc_code(
    username: str, dest_dir: str, metadata_items: List[str] = ["ApexClass"], generate_metadata_list: bool = False
):
    """
    Full code from the instance associated with the username.
    :param username: The username of the sfdc user.
    :param dest_dir: The directory to drop the files in.
    :param metadata_items: The list of metadata items to retrieve.
    :param generate_metadata_list: Do you want to generate a list of metadata items.
    :return:
    """

    # Now Pulling Code

    metadata = ""
    for item in metadata_items:
        metadata += item + ","
    metadata = metadata[:-1]

    pulled_files = []
    for line in execute(
        ["sfdx", "force:source:retrieve", "-u", username, "-m", metadata],
        cwd=Path(os.getcwd(), config.WORKING_DIR, dest_dir),
    ):
         pulled_files.append(line + "\n")

    if generate_metadata_list:
        with open("metadata_list.txt", "w") as out_file:
            out_file.writelines(pulled_files)

    logger.info(
        f"retrieved {len(pulled_files)} files. File list saved to {Path(os.getcwd(), 'metadata_list.txt')}"
    )

def stage_files(repo_dir: str):

    """
    Stage the modified files in the repo.
    :param repo_dir: The directory of the repo.
    :return:
    """
    git_add_changes = subprocess.run(
        ["git", "add", "."], cwd=Path(os.getcwd(), config.WORKING_DIR, repo_dir), capture_output=True
    )

    if git_add_changes.returncode:
        logger.error(
            git_add_changes.stderr.decode("utf-8").strip("\n").replace("\n", " ")
        )

    logger.info(git_add_changes.stdout.decode("utf-8").strip("\n").replace("\n", " "))



def commit_changes(dir_name: str, commit_message: str = None):

    """
    Commit changed files oin the repo.
    :param dir_name: The directory of the repo.
    :param commit_message: The commit message.
    :return:
    """
    git_commit = subprocess.run(
        [
            "git",
            "commit",
            "-m",
            (
                commit_message
                if commit_message is not None
                else f'"commited files"'
            ),
        ],
        cwd=Path(config.WORKING_DIR, dir_name),
        capture_output=True,
    )
    if git_commit.returncode:
        logger.error(git_commit.stderr.decode("utf-8").strip("\n").replace("\n", " "))

    logger.info(git_commit.stdout.decode("utf-8").strip("\n").replace("\n", " "))


def get_changed_files(target_branch: str, dir_name: str, diff_filter: str="ADM", source_branch: str = None) -> List[str]:

    if source_branch is None:
        git_diff = subprocess.run(
            ["git", "diff", target_branch, "--name-only", f"--diff-filter={diff_filter}"],
            cwd=Path(config.WORKING_DIR, dir_name), capture_output=True
        )


    else:
        git_diff = subprocess.run(
            ["git", "diff", "--name-only", f"--diff-filter={diff_filter}", source_branch, target_branch],
            cwd=Path(config.WORKING_DIR, dir_name), capture_output=True
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
        cwd=Path(config.WORKING_DIR, "mdapi"),
        capture_output=True,
        shell=True,
    )

    if convert_to_metadata.returncode:
        logger.error(
            convert_to_metadata.stderr.decode("utf-8").strip("\n").replace("\n", " ")
        )


def log_out_of_orgs(user_list=List[str]):
    # Change CLI to mdapi
    for user in user_list:
        log_out_of_org = subprocess.run(
            ["sfdx", "force:auth:logout", "-u", f"{user}", "-p"],
            cwd=".",
            capture_output=True,
            shell=True,
        )
        if log_out_of_org.returncode:
            logger.error(
                log_out_of_org.stderr.decode("utf-8").strip("\n").replace("\n", " ")
            )
        else:
            logger.warning(log_out_of_org.stdout.decode("utf-8").strip("\n").replace("\n", " "))


def get_active_orgs() -> dict:
    get_org_list = subprocess.run(
        ["sfdx", "force:org:list", "--json"],
        cwd=".",
        capture_output=True,
        shell=True,
    )

    if get_org_list.returncode:
        logger.error(
            get_org_list.stderr.decode("utf-8").strip("\n").replace("\n", " ")
        )
        return json.loads(get_org_list.stderr.decode("utf-8"))

    return json.loads(get_org_list.stdout.decode("utf-8"))


def log_out_of_staging_orgs():
    users = []

    for conf in config.instance_config_options:
        users.append(conf.user)

    my_orgs = get_active_orgs()

    users_to_log_out_of = []

    logger.info(f"orgId-username")
    for org in my_orgs["result"]["nonScratchOrgs"]:
        logger.info(f"{org['orgId']}-{org['username']}")
        if org["username"] in users:
            users_to_log_out_of.append(org["username"])

    if len(users_to_log_out_of) > 0:
        log_out_of_orgs(user_list=users_to_log_out_of)


def jwt_org_auth(sfdc_instance: SalesForceInstance):
    """
    Authorize with JWT
    :param sfdc_instance:
    :return:
    """

    log_into_org = subprocess.run(
        ["sfdx", "force:auth:jwt:grant", "-u", f"{sfdc_instance.user}", "-f", f"{sfdc_instance.cert}", "-i", f"{sfdc_instance.client_id}", "-a", f"{sfdc_instance.alias}"],
        cwd=".",
        capture_output=True,
        shell=True,
    )
    if log_into_org.returncode:
        logger.error(
            log_into_org.stderr.decode("utf-8").strip("\n").replace("\n", " ")
        )
    else:
        logger.warning(log_into_org.stdout.decode("utf-8").strip("\n").replace("\n", " "))




if __name__ == "__main__":
    pass