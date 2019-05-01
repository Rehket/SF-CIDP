from pydantic import BaseModel


WORKING_DIR = "working_dir"


class SalesForceInstance(BaseModel):
    url: str
    alias: str
    stage_label: str
    user: str
    client_id: str
    test_level: str

