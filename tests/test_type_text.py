"""TypeText must not depend on the active keyboard layout."""

import pytest

from macos_mcp.ax import core


@pytest.mark.unit
class TestTypeText:
    @pytest.fixture
    def calls(self, mocker):
        mocker.patch.object(core.time, "sleep")
        mocker.patch.object(core, "_release_modifiers")
        key_press = mocker.patch.object(core, "KeyPress")
        unicode_char = mocker.patch.object(core, "_type_unicode_char")
        return key_press, unicode_char

    def test_letters_digits_and_punctuation_are_sent_as_unicode(self, calls):
        """Their US key codes type other characters on AZERTY or Dvorak."""
        key_press, unicode_char = calls
        core.TypeText("aA1,;")
        key_press.assert_not_called()
        assert [c.args[0] for c in unicode_char.call_args_list] == list("aA1,;")

    def test_space_return_and_tab_stay_real_key_presses(self, calls):
        key_press, unicode_char = calls
        core.TypeText(" \n\t")
        assert [c.args[0] for c in key_press.call_args_list] == [
            core.KeyCode.Space,
            core.KeyCode.Return,
            core.KeyCode.Tab,
        ]
        unicode_char.assert_not_called()

    def test_non_ascii_is_sent_as_unicode(self, calls):
        _, unicode_char = calls
        core.TypeText("é你")
        assert [c.args[0] for c in unicode_char.call_args_list] == ["é", "你"]
