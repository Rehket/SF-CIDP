import push
from prefect import Flow as PrefectFlow, Parameter


create_sfdx_project = push.create_sfdx_project
pull_sfdc_code = push.pull_sfdc_code
initialize_git = push.initialize_git
git_add = push.git_add

username = Parameter("username")
my_project_name = Parameter("project_name")
metadata_items = Parameter("metadata_items")
generate_metadata_list = Parameter("generate_metadata_list")


# Flow Entry Point
flow = PrefectFlow("My SFDC Project Build")

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
    generate_metadata_list=generate_metadata_list,
    flow=flow,
)

# Initialize a git project.
flow.add_task(initialize_git)
initialize_git.set_upstream(pull_sfdc_code, flow=flow)
initialize_git.bind(project_dir=my_project_name, flow=flow)

# Add SFDX files to the project.
flow.add_task(git_add)
git_add.set_upstream(initialize_git, flow=flow)
git_add.bind(project_dir=my_project_name, flow=flow)

# Commit The Files


# Push them to remote


if __name__ == "__main__":
    flow.run(
        username="SFDC_USEREmail",
        project_name="SFDX_Project",
        metadata_items=["ApexClass", "ApexTrigger"],
        generate_metadata_list=False,
    )
