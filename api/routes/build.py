from fastapi import APIRouter
from pydantic import BaseModel
from nox.runtime.engine_runtime import engine

router = APIRouter()


class PromptRequest(BaseModel):
    prompt: str


@router.post("/build")
async def build(req: PromptRequest):

    result = await engine.handle_prompt(req.prompt)

    return {
        "status": "success",
        "engine_result": result
    }