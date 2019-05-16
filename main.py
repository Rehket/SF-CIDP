
from prefect import Flow as PrefectFlow, Parameter
from prefect.core import Edge

from gob import git_commands, sfdx_commands


create_sfdx_project = sfdx_commands.create_sfdx_project
pull_sfdc_code = sfdx_commands.pull_sfdc_code
git_init = git_commands.git_init
git_add = git_commands.git_add

username = Parameter("username")
my_project_name = Parameter("project_name")
metadata_items = Parameter("metadata_items")


# Flow Entry Point
flow = PrefectFlow("My SFDC Project Init")

# Create the SFDX Project
flow.add_task(create_sfdx_project)
create_sfdx_project.bind(project_name=my_project_name, flow=flow)

# Pull the sfdx code from the org.
flow.add_task(pull_sfdc_code)
pull_sfdc_code.set_upstream(create_sfdx_project, flow=flow)
pull_sfdc_code.bind(
    username=username,
    dest_dir=my_project_name,
    metadata_items=metadata_items,
    flow=flow,
)

# Initialize a git project.
flow.add_task(git_init)
git_init.set_upstream(pull_sfdc_code, flow=flow)
git_init.bind(project_dir=my_project_name, flow=flow)

# Add SFDX files to the project.
flow.add_task(git_add)
git_add.set_upstream(git_init, flow=flow)
git_add.bind(project_dir=my_project_name, flow=flow)

# TODO: use an edge to link the return values of one task to the input of another :D

# changed_files = sfdx_commands.copy_changed_files_and_get_tests
# flow.add_task(changed_files)
# flow.add_edge(pull_sfdc_code, changed_files, key="pull_result")






# Push them to remote



if __name__ == "__main__":
    flow.run(
        username="adam@aalbright.com",
        project_name="SFDX_Project",
        metadata_items=["ApexClass"],
    )
