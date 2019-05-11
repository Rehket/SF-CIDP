from pathlib import Path
from typing import List
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
) -> List[dict]:
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

    pull_instance_metadata = subprocess.run(
        ["sfdx", "force:source:retrieve", "-u", username, "-m", metadata, "--json"],
        cwd=Path(os.getcwd(), working_dir, dest_dir),
    )
    if pull_instance_metadata.returncode:
        pull_result = json.loads(
            pull_instance_metadata.stderr.decode("utf-8").strip("\n").replace("\n", " ")
        )
        raise RuntimeError(pull_result)

    pull_result = json.loads(
        pull_instance_metadata.stdout.decode("utf-8").strip("\n").replace("\n", " ")
    )

    logger.info(
        f"Retrieved {len(pull_result['result']['inboundFiles'])} files. File list saved to {Path(os.getcwd(), 'metadata_list.txt')}"
    )
    return pull_result["result"]["inboundFiles"]


@prefect_task
def copy_changed_files_and_get_tests(changed_files: List[dict], source_dir: str):

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
        shutil.copy(Path(os.getcwd(), source_dir, file), new_path)
        shutil.copy(Path(os.getcwd(), source_dir, file + "-meta.xml"), new_path)

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


# @prefect_task
# def log_out_of_orgs(user_list=List[str]):
#     # Change CLI to mdapi
#     for user in user_list:
#         log_out_of_org = subprocess.run(
#             ["sfdx", "force:auth:logout", "-u", f"{user}", "-p"],
#             cwd=".",
#             capture_output=True,
#             shell=True,
#         )
#         if log_out_of_org.returncode:
#             logger.error(
#                 log_out_of_org.stderr.decode("utf-8").strip("\n").replace("\n", " ")
#             )
#         else:
#             logger.warning(
#                 log_out_of_org.stdout.decode("utf-8").strip("\n").replace("\n", " ")
#             )


@prefect_task
def get_active_orgs() -> dict:
    get_org_list = subprocess.run(
        ["sfdx", "force:org:list", "--json"], cwd=".", capture_output=True, shell=True
    )

    if get_org_list.returncode:
        logger.error(get_org_list.stderr.decode("utf-8").strip("\n").replace("\n", " "))
        return json.loads(get_org_list.stderr.decode("utf-8"))

    return json.loads(get_org_list.stdout.decode("utf-8"))


# Not quite sure this is needed.
# @prefect_task
# def log_out_of_staging_orgs():
#     users = []
#
#     for conf in config.instance_config_options:
#         users.append(conf.user)
#
#     my_orgs = get_active_orgs()
#
#     users_to_log_out_of = []
#
#     logger.info(f"orgId-username")
#     for org in my_orgs["result"]["nonScratchOrgs"]:
#         logger.info(f"{org['orgId']}-{org['username']}")
#         if org["username"] in users:
#             users_to_log_out_of.append(org["username"])
#
#     if len(users_to_log_out_of) > 0:
#         log_out_of_orgs(user_list=users_to_log_out_of)


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

