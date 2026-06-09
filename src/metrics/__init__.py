"""Forensic finance metrics: Beneish, Altman, Sloan, Piotroski."""

from .beneish import BeneishInputs, BeneishResult, calculate as beneish_score
from .altman import AltmanInputs, AltmanResult, calculate as altman_score
from .sloan import SloanInputs, SloanResult, calculate as sloan_score
from .piotroski import PiotroskiInputs, PiotroskiResult, calculate as piotroski_score

__all__ = [
    "BeneishInputs", "BeneishResult", "beneish_score",
    "AltmanInputs", "AltmanResult", "altman_score",
    "SloanInputs", "SloanResult", "sloan_score",
    "PiotroskiInputs", "PiotroskiResult", "piotroski_score",
]
