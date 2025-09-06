from pydantic import BaseModel, ConfigDict


class SettingsIn(BaseModel):
    listenBrainzUser: str | None = None
    listenBrainzToken: str | None = None
    useGpu: bool = False
    useStems: bool = False
    useExcerpts: bool = False


class SettingsOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    listenBrainzUser: str | None = None
    listenBrainzToken: str | None = None
    lastfmUser: str | None = None
    lastfmConnected: bool = False
    useGpu: bool = False
    useStems: bool = False
    useExcerpts: bool = False


class SettingsUpdateResponse(BaseModel):
    ok: bool
