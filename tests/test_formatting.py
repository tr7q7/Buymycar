"""
Filet de sécurité — helpers de nettoyage d'affichage.
"""

import pytest

from app.utils.formatting import clean_model_label, clean_title


class TestCleanModelLabel:
    @pytest.mark.parametrize("raw", ["Autres", "autre", "AUTRES", "", "  ", "non renseigne"])
    def test_valeurs_generiques_masquees(self, raw):
        assert clean_model_label(raw) == ""

    @pytest.mark.parametrize("raw, expected", [
        ("RS3", "RS3"),
        ("  Clio  ", "Clio"),
        ("Serie 3", "Serie 3"),
    ])
    def test_valeurs_reelles_conservees(self, raw, expected):
        assert clean_model_label(raw) == expected


class TestCleanTitle:
    def test_espaces_compactes(self):
        assert clean_title("Audi   RS3\n  Berline ") == "Audi RS3 Berline"

    def test_vide(self):
        assert clean_title("") == ""
