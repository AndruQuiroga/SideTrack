"""The four ADR 0004 models. Revisions are pinned Hugging Face commits (2026-10-26)."""

from __future__ import annotations

from typing import Any

import numpy as np

from .torch_base import TorchAdapter, require


class MuQAdapter(TorchAdapter):
    name = "muq"
    checkpoint = "OpenMuQ/MuQ-large-msd-iter"
    revision = "0562a57814f6f8bbd9fdea0a25921a2fce1a841a"
    license = "CC-BY-NC-4.0"
    pooling = "mean over time of the final hidden state"
    sample_rate = 24000
    expected_dim = 1024

    def _load_model(self) -> None:
        muq = require("muq")
        model = muq.MuQ.from_pretrained(self.checkpoint, revision=self.revision)
        self._model = model.to(self._device).eval()

    def _forward(self, batch: list[np.ndarray]) -> Any:
        output = self._model(self._tensor(batch), output_hidden_states=True)
        return output.last_hidden_state.mean(dim=1)


class MuQMuLanAdapter(TorchAdapter):
    name = "muq-mulan"
    checkpoint = "OpenMuQ/MuQ-MuLan-large"
    revision = "2e01c796b71dca71b45251384c04cd7b237c9020"
    license = "CC-BY-NC-4.0"
    pooling = "MuLan audio projection embedding"
    sample_rate = 24000
    expected_dim = 512

    def _load_model(self) -> None:
        muq = require("muq")
        model = muq.MuQMuLan.from_pretrained(self.checkpoint, revision=self.revision)
        self._model = model.to(self._device).eval()

    def _forward(self, batch: list[np.ndarray]) -> Any:
        return self._model(wavs=self._tensor(batch))


class MERTAdapter(TorchAdapter):
    name = "mert"
    checkpoint = "m-a-p/MERT-v1-95M"
    revision = "12af15fef9d0ac838c3f475bfbbf26d2060dd4f5"
    license = "CC-BY-NC-4.0"
    pooling = "mean over time of the average of all hidden layers"
    sample_rate = 24000
    expected_dim = 768

    def _load_model(self) -> None:
        transformers = require("transformers")
        self._processor = transformers.Wav2Vec2FeatureExtractor.from_pretrained(
            self.checkpoint, revision=self.revision, trust_remote_code=True
        )
        self.sample_rate = int(self._processor.sampling_rate)
        model = transformers.AutoModel.from_pretrained(
            self.checkpoint, revision=self.revision, trust_remote_code=True
        )
        self._model = model.to(self._device).eval()

    def _forward(self, batch: list[np.ndarray]) -> Any:
        inputs = self._processor(batch, sampling_rate=self.sample_rate, return_tensors="pt")
        values = inputs["input_values"].to(self._device)
        output = self._model(values, output_hidden_states=True)
        layers = self._torch.stack(output.hidden_states)  # (layers, batch, time, dim)
        return layers.mean(dim=0).mean(dim=1)


class CLAPAdapter(TorchAdapter):
    name = "clap"
    checkpoint = "laion/larger_clap_music"
    revision = "a0b4534a14f58e20944452dff00a22a06ce629d1"
    license = "Apache-2.0"
    pooling = "CLAP audio projection embedding"
    sample_rate = 48000
    expected_dim = 512

    def _load_model(self) -> None:
        transformers = require("transformers")
        self._processor = transformers.ClapProcessor.from_pretrained(
            self.checkpoint, revision=self.revision
        )
        self.sample_rate = int(self._processor.feature_extractor.sampling_rate)
        model = transformers.ClapModel.from_pretrained(self.checkpoint, revision=self.revision)
        self._model = model.to(self._device).eval()

    def _forward(self, batch: list[np.ndarray]) -> Any:
        extractor = self._processor.feature_extractor
        inputs = extractor(batch, sampling_rate=self.sample_rate, return_tensors="pt")
        inputs = {k: v.to(self._device) for k, v in inputs.items()}
        return self._model.get_audio_features(**inputs)
