import re

from qttranslationgenerator.qt_translation_file_generator import _ParsePythonFormat


def test(input, expected_output, reverse_input, expected_reverse_output):
    parser = _ParsePythonFormat(input)
    assert expected_output == parser.output


test(
    "foo",
    "foo",
    "{0} bar",
    "{0} bar",
)
test(
    "foo {0}",
    "foo {0}",
    "{0} bar",
    "{0} bar",
)
test(
    "{0} foo {1}",
    "{0} foo {1}",
    "{1} bar {0}",
    "{1} bar {0}",
)
test(
    "foo {1} {0}",
    "foo {0} {1}",
    "{0} bar {1}",
    "{1} bar {0}",
)

test(
    "This {person}'s {color} object.",
    "This {0}'s {1} object.",
    "Cet object {1} de {0}",
    "Cet object {color} de {person}",
)
