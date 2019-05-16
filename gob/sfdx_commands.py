from pathlib import Path
from typing import List, Dict
from prefect import task as prefect_task, Flow
from loguru import logger
import json
import os
import subprocess
import shutil

working_dir = os.environ.get("WORKING_DIR", "working_dir")


@prefect_task
def pull_sfdc_code(
    username: str, dest_dir: str, metadata_items: List[str] = ["ApexClass"]
) -> Dict[str, object]:
    """
    Full code from the instance associated with the username.
    :param username: The username of the sfdc user.
    :param dest_dir: The directory to drop the files in.
    :param metadata_items: The list of metadata items to retrieve.
    :return: A list of the metadata items retrieved.
    """

    # Now Pulling Code

    metadata = ""
    for item in metadata_items:
        metadata += item + ","
    metadata = metadata[:-1]

    print(["sfdx", "force:source:retrieve", "-u", username, "-m", metadata, "--json"])

    pull_instance_metadata = subprocess.run(
        ["sfdx", "force:source:retrieve", "-u", username, "-m", metadata, "--json"],
        cwd=Path(working_dir, dest_dir),
        capture_output=True,
        shell=True,
        text=True,
    )

    if pull_instance_metadata.returncode:
        pull_result = json.loads(pull_instance_metadata.stderr)
        raise RuntimeError(pull_result)

    pull_result = json.loads(pull_instance_metadata.stdout)
    logger.info(f"Retrieved {len(pull_result['result']['inboundFiles'])} files.")
    print(pull_result["result"]["inboundFiles"])
    return {"files": pull_result["result"]["inboundFiles"], "project_dir": dest_dir}


@prefect_task
def copy_changed_files_and_get_tests(pull_result: Dict[str, object]):

    print(pull_result)

    test_classes = []
    for entry in pull_result["files"]:
        new_path = Path(working_dir, "mdapi", os.path.split(entry["filePath"])[0])
        new_path.mkdir(parents=True, exist_ok=True)

        if entry["fullName"].lower().endswith("test") or entry[
            "fullName"
        ].lower().endswith(
            "tc"
        ):  # It is a test Class
            test_classes.append(entry["filePath"])

        shutil.copy(
            Path(
                os.getcwd(), working_dir, pull_result["project_dir"], entry["filePath"]
            ),
            new_path,
        )
        shutil.copy(
            Path(
                os.getcwd(),
                working_dir,
                pull_result["project_dir"],
                entry["filePath"][0:-4] + "-meta.xml",
            ),
            new_path,
        )

    if len(test_classes) == 0:
        logger.error("No Test Classes were found. Aborting migration.")
        raise RuntimeError("No Test Classes were found. Aborting migration.")

    logger.info(f"{len(test_classes)} test classes located.")
    return test_classes


@prefect_task
def convert_project_to_mdapi():
    # Change CLI to mdapi
    convert_to_metadata = subprocess.run(
        ["sfdx", "force:source:convert", "-r", "force-app", "-d", "mdapi", "--json"],
        cwd=Path(working_dir, "mdapi"),
        capture_output=True,
        shell=True,
        text=True,
    )

    if convert_to_metadata.returncode:
        logger.error(convert_to_metadata.stderr)
        raise RuntimeError("Conversion to metadata project failed.")

    return json.loads(convert_to_metadata.stdout)["results"]


@prefect_task
def get_active_orgs() -> dict:
    get_org_list = subprocess.run(
        ["sfdx", "force:org:list", "--json"], cwd=".", capture_output=True, shell=True
    )

    if get_org_list.returncode:
        logger.error(get_org_list.stderr.decode("utf-8").strip("\n").replace("\n", " "))
        return json.loads(get_org_list.stderr.decode("utf-8"))

    return json.loads(get_org_list.stdout.decode("utf-8"))


@prefect_task
def sfdx_jwt_org_auth(user_name: str, key: str, client_id: str, alias: str) -> dict:
    """
    Authorize with JWT
    :param user_name: Username to use
    :param key: path to private key file
    :param client_id: client id for connected app
    :param alias: Alias for the sandbox.
    :return: a dictionary containing the orgId and instanceUrl
    """

    log_into_org = subprocess.run(
        [
            "sfdx",
            "force:auth:jwt:grant",
            "-u",
            f"{user_name}",
            "-f",
            f"{key}",
            "-i",
            f"{client_id}",
            "-a",
            f"{alias}",
            "--json",
        ],
        cwd=".",
        capture_output=True,
        shell=True,
        text=True,
    )
    if log_into_org.returncode:
        raise RuntimeError(log_into_org.stderr)

    result = json.loads(log_into_org.stdout)["result"]

    return {"orgId": result["orgId"], "instanceUrl": result["instanceUrl"]}


@prefect_task
def create_sfdx_project(project_name: str) -> int:

    create_project = subprocess.run(
        [
            "sfdx",
            "force:project:create",
            "--projectname",
            f"{project_name}",
            "--template",
            "standard",
            "--json",
        ],
        cwd=Path(working_dir),
        capture_output=True,
        shell=True,
    )

    output = json.loads(create_project.stdout.decode("utf-8"))
    status = output["status"]
    if status is not 0:
        logger.error(output["result"]["rawOutput"])
    else:
        logger.info(output["result"]["rawOutput"])

    return status


if __name__ == "__main__":
    print("Testing sfdx_commands")
    with open(Path(Path(os.getcwd()).parent, "sfdc_config.json"), "r") as config_in:

        config = json.load(config_in)[0]

    with Flow("A flow") as flow:
        foo = sfdx_jwt_org_auth(
            user_name=config["user"],
            key=Path(Path(os.getcwd()).parent, config["cert"]),
            client_id=config["client_id"],
            alias=config["alias"],
        )

        flow.run()
