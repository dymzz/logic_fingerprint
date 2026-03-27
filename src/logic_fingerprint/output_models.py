from pydantic import BaseModel

class SumNumbersOutput(BaseModel):
    sum: int
