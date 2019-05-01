from pydantic import BaseModel
import json

WORKING_DIR = "working_dir"


class SalesForceInstance(BaseModel):
    url: str
    alias: str
    stage_label: str
    user: str
    client_id: str
    test_level: str
    cert: str


instance_config_options = []

with open("sfdc_config.json", "r") as sfdc_config_in:
    instance_configs = json.load(sfdc_config_in)

    for conf in instance_configs:
        inst = SalesForceInstance(**conf)
        instance_config_options.append(inst)



if __name__ == "__main__":
    print(instance_config_options)
