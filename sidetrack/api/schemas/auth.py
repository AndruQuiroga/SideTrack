from pydantic import BaseModel, ConfigDict


class Credentials(BaseModel):
    username: str
    password: str


class GoogleToken(BaseModel):
    token: str


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    user_id: str


class MeOut(BaseModel):
    user_id: str
    lastfmUser: str | None = None
    lastfmConnected: bool = False
    spotifyUser: str | None = None
    spotifyConnected: bool = False
    listenbrainzUser: str | None = None
    listenbrainzConnected: bool = False
