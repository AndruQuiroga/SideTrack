"""The registered demos. Adding one is a builder, a template and a line here."""

from __future__ import annotations

from ..site import Demo
from . import explorer, signature, timeline

DEMOS: list[Demo] = [timeline.demo(), signature.demo(), explorer.demo()]
