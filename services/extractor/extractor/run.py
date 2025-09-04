from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Optional

import numpy as np
import typer
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column
from sqlalchemy import Integer, String, Text as SQLText, Float, ForeignKey

app = typer.Typer(add_completion=False)


class Base(DeclarativeBase):
    pass


class Track(Base):
    __tablename__ = "track"
    track_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(512))
    path_local: Mapped[Optional[str]] = mapped_column(SQLText, nullable=True)
    duration: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)


class Feature(Base):
    __tablename__ = "features"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    track_id: Mapped[int] = mapped_column(ForeignKey("track.track_id"))
    bpm: Mapped[Optional[float]] = mapped_column(Float)
    bpm_conf: Mapped[Optional[float]] = mapped_column(Float)
    key: Mapped[Optional[str]] = mapped_column(String(8))
    key_conf: Mapped[Optional[float]] = mapped_column(Float)
    # Minimal subset—DB has additional JSON fields
    percussive_harmonic_ratio: Mapped[Optional[float]] = mapped_column(Float)
    pumpiness: Mapped[Optional[float]] = mapped_column(Float)


def get_db_url() -> str:
    url = os.getenv("DATABASE_URL")
    if url:
        return url
    host = os.getenv("POSTGRES_HOST", "localhost")
    db = os.getenv("POSTGRES_DB", "vibescope")
    user = os.getenv("POSTGRES_USER", "vibe")
    pw = os.getenv("POSTGRES_PASSWORD", "vibe")
    port = os.getenv("POSTGRES_PORT", "5432")
    return f"postgresql+psycopg://{user}:{pw}@{host}:{port}/{db}"


def safe_load_audio(path: str, sr: int = 44100) -> tuple[np.ndarray, int]:
    import soundfile as sf
    import librosa as lb
    try:
        y, srate = sf.read(path, always_2d=False)
        if y.ndim > 1:
            y = np.mean(y, axis=1)
        if srate != sr:
            y = lb.resample(y, orig_sr=srate, target_sr=sr)
            srate = sr
        return y.astype(np.float32), srate
    except Exception:
        y, srate = lb.load(path, sr=sr, mono=True)
        return y, srate


def estimate_features(wav_path: str) -> dict:
    import librosa as lb
    y, sr = safe_load_audio(wav_path, sr=44100)
    if y.size == 0:
        raise RuntimeError("empty audio")

    # Onset strength for onset rate proxy
    onset_env = lb.onset.onset_strength(y=y, sr=sr)
    onset_rate = float(np.mean(onset_env))

    # Tempo
    tempo, beats = lb.beat.beat_track(y=y, sr=sr)
    bpm = float(tempo)
    bpm_conf = float(min(1.0, np.std(onset_env) / (np.mean(onset_env) + 1e-6)))

    # Percussive vs harmonic energy
    y_h, y_p = lb.effects.hpss(y)
    phr = float(np.mean(np.abs(y_p)) / (np.mean(np.abs(y_h)) + 1e-8))

    # Placeholder pumpiness: correlate percussive and inverted low-freq energy
    S = np.abs(lb.stft(y, n_fft=2048))
    low = np.mean(S[:20, :], axis=0)
    drum = np.mean(S[40:120, :], axis=0)
    if low.std() > 1e-6 and drum.std() > 1e-6:
        pump = float(np.corrcoef(drum, -low)[0, 1])
    else:
        pump = 0.0

    return {
        "bpm": bpm,
        "bpm_conf": bpm_conf,
        "percussive_harmonic_ratio": phr,
        "pumpiness": pump,
    }


def find_pending_tracks(db: Session, batch_size: int = 4) -> list[Track]:
    # Tracks with a local path and no features yet
    rows = db.execute(
        text(
            """
            SELECT t.track_id, t.title, t.path_local, t.duration
            FROM track t
            LEFT JOIN features f ON f.track_id = t.track_id
            WHERE t.path_local IS NOT NULL AND f.track_id IS NULL
            LIMIT :n
            """
        ),
        {"n": batch_size},
    ).all()
    out: list[Track] = []
    for tid, title, path_local, duration in rows:
        tr = Track()
        tr.track_id = tid
        tr.title = title
        tr.path_local = path_local
        tr.duration = duration
        out.append(tr)
    return out


def analyze_one(db: Session, tr: Track, audio_root: str) -> bool:
    if not tr.path_local:
        return False
    p = Path(tr.path_local)
    if not p.is_absolute():
        p = Path(audio_root) / p
    if not p.exists():
        return False
    feats = estimate_features(str(p))
    db.add(
        Feature(
            track_id=tr.track_id,
            bpm=feats.get("bpm"),
            bpm_conf=feats.get("bpm_conf"),
            key=None,
            key_conf=None,
            percussive_harmonic_ratio=feats.get("percussive_harmonic_ratio"),
            pumpiness=feats.get("pumpiness"),
        )
    )
    db.commit()
    return True


@app.command()
def main(
    schedule: str = typer.Option("@daily", help="Cron or preset schedule"),
    once: bool = typer.Option(False, help="Run one pass then exit"),
    batch_size: int = typer.Option(4, help="Tracks to process per pass"),
):
    audio_root = os.getenv("AUDIO_ROOT", "/audio")
    url = get_db_url()
    engine = create_engine(url, pool_pre_ping=True)
    typer.echo(f"[extractor] connected to DB: {url}")
    with Session(engine) as db:
        # quick ping
        try:
            db.execute(text("SELECT 1"))
        except Exception as e:
            typer.echo(f"[extractor] DB not ready: {e}")
            return

    try:
        while True:
            with Session(engine) as db:
                pending = find_pending_tracks(db, batch_size=batch_size)
                if not pending:
                    typer.echo("[extractor] no pending tracks; sleeping")
                for tr in pending:
                    ok = analyze_one(db, tr, audio_root)
                    typer.echo(f"[extractor] track {tr.track_id} analyzed: {ok}")
            if once:
                break
            time.sleep(10)
    except KeyboardInterrupt:
        typer.echo("[extractor] stopping")


if __name__ == "__main__":
    app()
