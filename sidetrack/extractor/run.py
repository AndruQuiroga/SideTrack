"""Extractor CLI for computing audio features and embeddings.

Examples
--------
Run every 10 seconds (default interval)::

    python -m sidetrack.extractor.run --schedule 10

Run on a cron schedule (every 5 minutes)::

    python -m sidetrack.extractor.run --schedule "*/5 * * * *"

The ``--schedule`` option accepts either a floating-point interval in seconds or a
standard cron expression.  Cron expressions are validated before the extractor starts.
"""

from __future__ import annotations

import asyncio
import contextlib
import os
import signal
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import typer
from croniter import croniter
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from sidetrack.common.models import Embedding, Feature, Track

app = typer.Typer(add_completion=False)


def get_db_url() -> str:
    url = os.getenv("DATABASE_URL")
    if url:
        return url
    # Default to the docker-compose service name for Postgres
    host = os.getenv("POSTGRES_HOST", "db")
    db = os.getenv("POSTGRES_DB", "vibescope")
    user = os.getenv("POSTGRES_USER", "vibe")
    pw = os.getenv("POSTGRES_PASSWORD", "vibe")
    port = os.getenv("POSTGRES_PORT", "5432")
    return f"postgresql+psycopg://{user}:{pw}@{host}:{port}/{db}"


def safe_load_audio(path: str, sr: int = 44100, mono: bool = False) -> tuple[np.ndarray, int]:
    """Load an audio file with a bit of defensive coding.

    Parameters
    ----------
    path : str
        Location of the audio file.
    sr : int
        Target sampling rate.
    mono : bool
        If True, collapse to mono.  Otherwise returns shape (n, ch).

    Returns
    -------
    y : np.ndarray
        Audio array (float32).
    sr : int
        Sampling rate.
    """

    import librosa as lb
    import soundfile as sf

    try:
        y, srate = sf.read(path, always_2d=True)
        if srate != sr:
            y = lb.resample(y.T, orig_sr=srate, target_sr=sr).T
            srate = sr
    except Exception:
        y, srate = lb.load(path, sr=sr, mono=False)
        if y.ndim == 1:
            y = y[None, :]
        y = y.T
    if mono:
        y = np.mean(y, axis=1)
    return y.astype(np.float32), srate


def estimate_key(chroma: np.ndarray) -> tuple[str, float]:
    """Estimate musical key from a chromagram.

    Uses a simple template‑matching (Krumhansl-Schmuckler) approach
    returning key string and a rudimentary confidence value.
    """

    # Krumhansl major/minor profiles
    major = np.array([6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88])
    minor = np.array([6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17])
    chroma_mean = chroma.mean(axis=1)
    majors = np.array([np.roll(major, i) for i in range(12)])
    minors = np.array([np.roll(minor, i) for i in range(12)])
    scores_major = chroma_mean @ majors.T
    scores_minor = chroma_mean @ minors.T
    idx_major = int(np.argmax(scores_major))
    idx_minor = int(np.argmax(scores_minor))
    notes = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
    if scores_major[idx_major] >= scores_minor[idx_minor]:
        key = f"{notes[idx_major]}maj"
        score = scores_major[idx_major]
    else:
        key = f"{notes[idx_minor]}min"
        score = scores_minor[idx_minor]
    total = float(chroma_mean @ chroma_mean + 1e-6)
    conf = float(score / total)
    return key, conf


def compute_embeddings(wav_path: str, models: list[str]) -> dict[str, list[float]]:
    """Compute optional embeddings for the given audio file.

    Parameters
    ----------
    wav_path : str
        Path to audio file.
    models : list[str]
        Names of embedding backends to try (e.g. ``["openl3", "clap"]``).

    Returns
    -------
    dict
        Mapping of model name to embedding vector.
    """

    out: dict[str, list[float]] = {}
    if not models:
        return out

    # Load audio in mono for embeddings
    y, sr = safe_load_audio(wav_path, sr=48000, mono=True)

    for model in models:
        vec: np.ndarray | None = None
        name = model.lower()
        if name == "openl3":
            try:
                import openl3

                emb, _ = openl3.get_audio_embedding(y, sr, hop_size=0.0)
                vec = emb.mean(axis=0)
            except Exception:
                vec = None
        elif name == "clap":
            try:
                import laion_clap
                import torch

                clap = laion_clap.CLAP_Module(enable_fusion=False)
                audio = torch.tensor(y).unsqueeze(0)
                emb = clap.get_audio_embedding_from_data(audio, sr)
                vec = emb[0].numpy()
            except Exception:
                vec = None
        else:
            # Fallback lightweight embedding using MFCCs
            try:
                import librosa as lb

                mfcc = lb.feature.mfcc(y=y, sr=sr, n_mfcc=20)
                vec = mfcc.mean(axis=1)
                name = "mfcc"
            except Exception:
                vec = None
        if vec is not None:
            out[name] = vec.astype(float).tolist()
    return out


def estimate_features(wav_path: str) -> dict:
    import os
    import tempfile

    # Ensure numba has a writable cache directory to avoid RuntimeError during
    # librosa's lazy imports.
    os.environ.setdefault("NUMBA_CACHE_DIR", os.path.join(tempfile.gettempdir(), "numba-cache"))
    import librosa as lb

    y_st, sr = safe_load_audio(wav_path, sr=44100, mono=False)
    if y_st.size == 0:
        raise RuntimeError("empty audio")

    # Collapse to mono for most analyses
    y = np.mean(y_st, axis=1)

    # Chroma & key estimation
    chroma = lb.feature.chroma_cqt(y=y, sr=sr)
    chroma_mean = chroma.mean(axis=1)
    chroma_var = chroma.var(axis=1)
    key, key_conf = estimate_key(chroma)

    # Spectral stats
    centroid = lb.feature.spectral_centroid(y=y, sr=sr)[0]
    rolloff = lb.feature.spectral_rolloff(y=y, sr=sr)[0]
    flatness = lb.feature.spectral_flatness(y=y)[0]
    bandwidth = lb.feature.spectral_bandwidth(y=y, sr=sr)[0]
    spectral = {
        "centroid_mean": float(np.mean(centroid)),
        "centroid_var": float(np.var(centroid)),
        "rolloff_mean": float(np.mean(rolloff)),
        "rolloff_var": float(np.var(rolloff)),
        "flatness_mean": float(np.mean(flatness)),
        "flatness_var": float(np.var(flatness)),
        "bandwidth_mean": float(np.mean(bandwidth)),
        "bandwidth_var": float(np.var(bandwidth)),
    }

    # Dynamics
    rms = lb.feature.rms(y=y)[0]
    dyn_range = float(np.percentile(rms, 95) - np.percentile(rms, 5))
    dynamics = {
        "rms_mean": float(np.mean(rms)),
        "rms_var": float(np.var(rms)),
        "dynamic_range": dyn_range,
    }

    # Stereo width
    if y_st.ndim == 2 and y_st.shape[1] >= 2:
        left = y_st[:, 0]
        right = y_st[:, 1]
        mid = (left + right) / 2
        side = (left - right) / 2
        width = float(np.mean(np.abs(side)) / (np.mean(np.abs(mid)) + 1e-8))
        if left.std() > 1e-6 and right.std() > 1e-6:
            lr_corr = float(np.corrcoef(left, right)[0, 1])
        else:
            lr_corr = 1.0
    else:
        width = 0.0
        lr_corr = 1.0
    stereo = {"width": width, "lr_corr": lr_corr}

    # Onset strength for tempo confidence
    onset_env = lb.onset.onset_strength(y=y, sr=sr)

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
        "key": key,
        "key_conf": key_conf,
        "chroma_stats": {"mean": chroma_mean.tolist(), "var": chroma_var.tolist()},
        "spectral": spectral,
        "dynamics": dynamics,
        "stereo": stereo,
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
            key=feats.get("key"),
            key_conf=feats.get("key_conf"),
            chroma_stats=feats.get("chroma_stats"),
            spectral=feats.get("spectral"),
            dynamics=feats.get("dynamics"),
            stereo=feats.get("stereo"),
            percussive_harmonic_ratio=feats.get("percussive_harmonic_ratio"),
            pumpiness=feats.get("pumpiness"),
        )
    )
    models_env = os.getenv("EMBEDDING_MODEL")
    models = [m.strip() for m in models_env.split(",") if m.strip()] if models_env else []
    embeds = compute_embeddings(str(p), models)
    for name, vec in embeds.items():
        db.add(Embedding(track_id=tr.track_id, model=name, dim=len(vec), vector=vec))
    db.commit()
    return True


@app.command()
def main(
    interval: float = typer.Option(
        10.0,
        "--interval",
        help="Seconds between extraction passes",
        envvar="EXTRACTOR_INTERVAL",
    ),
    schedule: str | None = typer.Option(
        None,
        "--schedule",
        help="Cron expression or seconds between passes",
        envvar="EXTRACTOR_SCHEDULE",
    ),
    once: bool = typer.Option(False, help="Run one pass then exit"),
    batch_size: int = typer.Option(4, help="Tracks to process per pass"),
):
    if schedule is not None:
        try:
            interval = float(schedule)
            if interval <= 0:
                raise ValueError
            schedule = None
        except ValueError:
            if not croniter.is_valid(schedule):
                raise typer.BadParameter("Schedule must be seconds or a cron expression")
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

    asyncio.run(_run_loop(engine, audio_root, batch_size, interval, once, schedule))


async def _run_loop(
    engine: any,
    audio_root: str,
    batch_size: int,
    interval: float,
    once: bool,
    schedule: str | None,
) -> None:
    stop_event = asyncio.Event()

    def _stop(*_: object) -> None:
        stop_event.set()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, _stop)
        except NotImplementedError:
            # Windows may not support signal handlers in Proactor loop
            signal.signal(sig, lambda *_: stop_event.set())

    try:
        while not stop_event.is_set():
            with Session(engine) as db:
                pending = find_pending_tracks(db, batch_size=batch_size)
                if not pending:
                    typer.echo("[extractor] no pending tracks; sleeping")
                for tr in pending:
                    ok = analyze_one(db, tr, audio_root)
                    typer.echo(f"[extractor] track {tr.track_id} analyzed: {ok}")
            if once:
                break
            if schedule:
                now = datetime.now(timezone.utc)
                next_time = croniter(schedule, now).get_next(datetime)
                delay = (next_time - now).total_seconds()
            else:
                delay = interval
            sleep_task = asyncio.create_task(asyncio.sleep(delay))
            stop_task = asyncio.create_task(stop_event.wait())
            done, pending_tasks = await asyncio.wait(
                {sleep_task, stop_task}, return_when=asyncio.FIRST_COMPLETED
            )
            for task in pending_tasks:
                task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await task
    finally:
        typer.echo("[extractor] stopping")


if __name__ == "__main__":
    app()
