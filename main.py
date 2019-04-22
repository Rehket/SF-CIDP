import subprocess

import shutil
import os
import sys
from pathlib import Path


def execute(cmd, cwd):
    popen = subprocess.Popen(
        cmd, cwd=cwd, stdout=subprocess.PIPE, universal_newlines=True, shell=True
    )
    for stdout_line in iter(popen.stdout.readline, ""):
        yield stdout_line.strip("\n")
    popen.stdout.close()
    return_code = popen.wait()
    if return_code:
        raise subprocess.CalledProcessError(return_code, cmd)

    return popen


if __name__ == "__main__":
    print("Let's Start!")

    github_url = "https://github.com/Rehket/Errors-In-SalesForce.git"

    dir_name = os.path.split(github_url)[1][0:-4]
    print(dir_name)

    # Check Git Status
    git_clone = subprocess.run(
        ["git", "clone", github_url], cwd=".", capture_output=True
    )

    # Check Git Status
    git_status = subprocess.run(["git", "status"], cwd=dir_name, capture_output=True)
    if git_status.returncode != 0:
        raise RuntimeError(str(git_status))

    print(git_status.stdout.decode("utf-8").strip("\n").replace("\n", " "))

    # Checkout Master
    git_master_branch = subprocess.run(
        ["git", "checkout", "master"], cwd=dir_name, capture_output=True
    )

    print(git_master_branch)

    # Get Branches
    git_branch = subprocess.run(["git", "branch"], cwd=dir_name, capture_output=True)
    print(git_branch.stdout)
    print(git_branch.stdout.decode("utf-8").strip("\n").replace("\n", " "))
    branches = [
        x
        for x in str(
            git_branch.stdout.decode("utf-8").strip("\n").replace("\n", " ")
        ).split()
    ]

    print(branches)

    branch_name = "dev_box"

    if branch_name in branches:
        git_new_branch = subprocess.run(
            ["git", "checkout", branch_name], cwd=dir_name, capture_output=True
        )
    else:
        git_new_branch = subprocess.run(
            ["git", "branch", branch_name], cwd=dir_name, capture_output=True
        )

    print(git_new_branch)

    if git_new_branch.returncode != 0:
        raise RuntimeError(git_new_branch.stderr.decode("utf-8"))

    # Now Pulling Code

    for line in execute(
        ["sfdx", "force:source:retrieve", "-u", branch_name, "-m", "ApexClass"],
        cwd=dir_name
    ):
        print(line)

    git_add_changes = subprocess.run(
        ["git", "add", "."], cwd=dir_name, capture_output=True
    )
    print(git_add_changes)

    # Checkout Master
    git_commit = subprocess.run(
        ["git", "commit", "-m", f'"added files from sandbox {branch_name}"'],
        cwd="./SFDC/mywork",
        capture_output=True,
    )

    print(git_commit)

    target_branch = "master"

    # Checkout Master
    git_diff = subprocess.run(
        ["git", "diff", target_branch, "--name-only"], cwd=dir_name, capture_output=True
    )

    print(git_diff)

    changed_files = str(
        git_diff.stdout.decode("utf-8").strip("\n").replace("\n", " ")
    ).split()
    print(changed_files)

    if len(changed_files) == 0:
        print("There are no Files to migrate.")
        sys.exit()

    cwd = os.getcwd()
    if Path(cwd, "mdapi").exists():
        shutil.rmtree(Path(cwd, "mdapi"))
    Path(cwd, "mdapi").mkdir(parents=True, exist_ok=True)

    shutil.copy(dir_name + "/sfdx-project.json", Path(cwd, "mdapi"))

    test_classes = []

    for file in changed_files:
        new_path = Path(os.getcwd(), "mdapi", os.path.split(file)[0])
        new_path.mkdir(parents=True, exist_ok=True)

        if file.endswith("-meta.xml"):
            continue
        if "test" in file.lower() or "tc" in file.lower() and file.endswith(".cls"):
            # It is a test Class
            test_classes.append(os.path.split(file)[1][0:-4])

        shutil.copy(Path(os.getcwd(), dir_name, file), new_path)
        shutil.copy(Path(os.getcwd(), dir_name, file + "-meta.xml"), new_path)

    # Change CLI to mdapi
    convert_to_metadata = subprocess.run(
        ["sfdx", "force:source:convert", "-r", "force-app", "-d", "mdapi"],
        cwd="mdapi",
        capture_output=True,
        shell=True,
    )

    print(convert_to_metadata)
    test_class_string = ""
    for test_class in test_classes:
        test_class_string += test_class + ","
    test_class_string = test_class_string[0:-1]
    print(test_class_string)
    for line in execute(
        [
            "sfdx",
            "force:mdapi:deploy",
            "-d",
            "src",
            "-c",
            "-u",
            branch_name,
            "-w",
            "10",
            "-l",
            "RunSpecifiedTests",
            "-r",
            test_class_string,
        ],
        cwd="mdapi",
    ):
        print(line)
