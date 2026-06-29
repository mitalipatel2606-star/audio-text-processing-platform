from pydantic import BaseModel, Field
from typing import List

class UserInfo(BaseModel):
    name: str = Field(..., min_length=1)
    age: str = ""
    noise: str = ""

class TtsResponseItem(BaseModel):
    id: str
    voice: str
    naturalness: int = Field(..., ge=1, le=5)
    pronunciation: int = Field(..., ge=1, le=5)
    intonation: int = Field(..., ge=1, le=5)
    overall: int = Field(..., ge=1, le=5)

class SttResponseItem(BaseModel):
    id: str
    filename: str
    clarity: int = Field(..., ge=1, le=5)
    intelligibility: int = Field(..., ge=1, le=5)
    noise: int = Field(..., ge=1, le=5)
    overall: int = Field(..., ge=1, le=5)

class SurveySubmission(BaseModel):
    userInfo: UserInfo
    ttsResponses: List[TtsResponseItem]
    sttResponses: List[SttResponseItem]
    comments: str = ""
