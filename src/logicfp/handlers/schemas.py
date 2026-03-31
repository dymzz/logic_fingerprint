from pydantic import BaseModel, Field


class SumNumbersInput(BaseModel):
    numbers: list[int] = Field(default_factory=list)


class SumNumbersOutput(BaseModel):
    sum: int
