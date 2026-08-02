"""Tests for tab identification.

macOS has no "AXTab" role. An individual tab is reported as role
AXRadioButton carrying the AXTabButton subrole; AXTabGroup is the container.
`Role.Tab = "AXTab"` was therefore a value no application ever reports, so
`TabControl()` could never match and the factory mapped real tabs to
RadioButtonControl.

Confirmed against live browser tabs:

    before:  TabControl() -> None   CreateControl(tab) -> RadioButtonControl
    after :  TabControl() -> TabControl   CreateControl(tab) -> TabControl
"""

import pytest

from macos_mcp.ax import controls
from macos_mcp.ax.controls import (
    Control,
    CreateControl,
    RadioButtonControl,
    TabControl,
)
from macos_mcp.ax.enums import Attribute, Role, Subrole


@pytest.mark.unit
class TestTabRoleIsGone:
    def test_role_has_no_tab_constant(self):
        """AXTab is not a role macOS reports; keeping it invites reuse."""
        assert not hasattr(Role, "Tab")

    def test_tab_group_is_still_declared(self):
        assert Role.TabGroup == "AXTabGroup"

    def test_tab_button_subrole_is_the_replacement(self):
        assert Subrole.TabButton == "AXTabButton"


@pytest.mark.unit
class TestTabControlFinder:
    def test_searches_by_subrole_not_role(self, mocker):
        control = Control(element="<el>")
        find = mocker.patch.object(Control, "FindFirst", return_value=None)

        control.TabControl()

        kwargs = find.call_args.kwargs
        assert kwargs.get("subrole") == Subrole.TabButton
        assert "role" not in kwargs or kwargs["role"] is None


@pytest.mark.unit
class TestCreateControlSubroleMapping:
    @staticmethod
    def _attributes(mocker, role, subrole):
        def fake(_element, attribute):
            return {Attribute.Role: role, Attribute.Subrole: subrole}.get(attribute)

        mocker.patch.object(controls, "GetAttribute", side_effect=fake)

    def test_tab_button_becomes_a_tab_control(self, mocker):
        self._attributes(mocker, Role.RadioButton, Subrole.TabButton)
        assert isinstance(CreateControl("<el>"), TabControl)

    def test_plain_radio_button_is_unaffected(self, mocker):
        """The subrole check must not capture ordinary radio buttons."""
        self._attributes(mocker, Role.RadioButton, None)
        created = CreateControl("<el>")
        assert isinstance(created, RadioButtonControl)
        assert not isinstance(created, TabControl)

    def test_subrole_is_not_fetched_for_other_roles(self, mocker):
        """CreateControl runs for every element; an unconditional extra
        round-trip for the subrole would show up in traversal cost."""
        asked = []

        def fake(_element, attribute):
            asked.append(attribute)
            return Role.Button if attribute == Attribute.Role else None

        mocker.patch.object(controls, "GetAttribute", side_effect=fake)
        CreateControl("<el>")

        assert Attribute.Subrole not in asked
