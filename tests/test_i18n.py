"""Translation catalog consistency tests."""

from string import Formatter

from i18n import LANGUAGE_LABELS, TRANSLATIONS, translate


def placeholders(template: str) -> set[str]:
    return {
        field_name
        for _, field_name, _, _ in Formatter().parse(template)
        if field_name is not None
    }


def test_every_language_has_the_same_messages_and_placeholders() -> None:
    chinese = TRANSLATIONS["zh"]

    for language, messages in TRANSLATIONS.items():
        assert messages.keys() == chinese.keys(), language
        for key, template in messages.items():
            assert placeholders(template) == placeholders(chinese[key]), (
                language,
                key,
            )


def test_every_available_language_has_a_label() -> None:
    assert LANGUAGE_LABELS.keys() == TRANSLATIONS.keys()


def test_translate_formats_values() -> None:
    assert translate("en", "status.turn", side="Red") == "Red to move."
    assert translate("fr", "status.turn", side="Noirs") == "Aux Noirs de jouer."
