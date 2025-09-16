import numpy as np
import pytest
import soundfile as sf

from sidetrack.common.models import Feature
from sidetrack.config import ExtractionConfig
from sidetrack.extraction.pipeline import analyze_track
from tests.factories import TrackFactory
from sidetrack.db import session_scope

pytestmark = pytest.mark.integration


def test_analyze_track(tmp_path):
    wav = tmp_path / "a.wav"
    sf.write(wav, np.zeros(1024), 22050)
    with session_scope() as db:
        from sidetrack.common.models import Base

        Base.metadata.create_all(db.bind)
        tr = TrackFactory(path_local=str(wav))
        db.add(tr)
        db.flush()
        tid = tr.track_id
        db.commit()
    cfg = ExtractionConfig()
    cfg.set_seed(0)
    fid = analyze_track(tid, cfg)
    with session_scope() as db:
        feat = db.get(Feature, fid)
        assert feat and feat.track_id == tid
