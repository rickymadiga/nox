from pydantic import BaseModel
from typing import Dict

class GeneratedProject(BaseModel):
    files: Dict[str, str]