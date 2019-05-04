
import json

WORKING_DIR = "working_dir"

instance_config_options = []

with open("sfdc_config.json", "r") as sfdc_config_in:
    instance_configs = json.load(sfdc_config_in)

if __name__ == "__main__":
    print(instance_config_options)
