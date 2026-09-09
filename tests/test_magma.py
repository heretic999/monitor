"""Uji parser MAGMA: harus konservatif (tidak false-positive dari teks generik)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fetch_magma import _parse  # noqa: E402


def test_reads_level_near_krakatau():
    assert _parse("Gunung Anak Krakatau saat ini berada pada tingkat aktivitas Level III (Siaga).") == 3
    assert _parse("... KRAKATAU ... status dinaikkan menjadi Level IV") == 4


def test_reads_word_level_near_krakatau():
    assert _parse("Anak Krakatau: status SIAGA, radius bahaya 3 km") == 3
    assert _parse("krakatau — AWAS") == 4


def test_ignores_level_far_from_krakatau():
    txt = "Anak Krakatau meletus. " + "x" * 500 + " Level II diberlakukan untuk gunung lain."
    assert _parse(txt) is None


def test_ignores_generic_text_without_krakatau():
    assert _parse("Silakan login untuk melihat informasi level akun Anda. Level I member.") is None


def test_none_when_no_match():
    assert _parse("halaman tidak memuat data gunung") is None
