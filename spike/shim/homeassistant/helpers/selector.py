"""GENERATED — do not edit by hand.

Produced by spike/generate_shim.py from Home Assistant 2026.8.1's own helpers/selector.py.
Regenerate rather than patching: the point of this module is that the constant
tail of the HA API costs a script run, not developer time.
"""

from typing import Any


class Selector:
    """Accept-anything stand-in for a config-flow selector.

    Real selectors validate form input and render a widget. Neither affects what
    the integration may do at runtime, so the shim keeps the name and the
    constructor signature and discards the schema.
    """

    def __init__(self, config: Any = None, **kwargs: Any) -> None:
        self.config = config if config is not None else kwargs

    def __call__(self, data: Any) -> Any:
        return data

    def serialize(self) -> dict[str, Any]:
        return {"selector": {type(self).__name__: self.config}}


class _SelectorConfig(dict):
    """Config dicts are TypedDicts upstream: plain dicts at runtime."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)


class ActionSelector(Selector):
    pass


class AddonSelector(Selector):
    pass


class AppSelector(Selector):
    pass


class AreaSelector(Selector):
    pass


class AssistPipelineSelector(Selector):
    pass


class AttributeSelector(Selector):
    pass


class AutomationBehaviorSelector(Selector):
    pass


class BackupLocationSelector(Selector):
    pass


class BooleanSelector(Selector):
    pass


class ChooseSelector(Selector):
    pass


class ColorRGBSelector(Selector):
    pass


class ColorTempSelector(Selector):
    pass


class ConditionSelector(Selector):
    pass


class ConfigEntrySelector(Selector):
    pass


class ConstantSelector(Selector):
    pass


class ConversationAgentSelector(Selector):
    pass


class CountrySelector(Selector):
    pass


class DateSelector(Selector):
    pass


class DateTimeSelector(Selector):
    pass


class DeviceSelector(Selector):
    pass


class DurationSelector(Selector):
    pass


class EntitySelector(Selector):
    pass


class FileSelector(Selector):
    pass


class FloorSelector(Selector):
    pass


class IconSelector(Selector):
    pass


class LabelSelector(Selector):
    pass


class LanguageSelector(Selector):
    pass


class LocationSelector(Selector):
    pass


class MediaSelector(Selector):
    pass


class NumberSelector(Selector):
    pass


class NumericThresholdSelector(Selector):
    pass


class ObjectSelector(Selector):
    pass


class QrCodeSelector(Selector):
    pass


class SelectSelector(Selector):
    pass


class SerialPortSelector(Selector):
    pass


class StateSelector(Selector):
    pass


class StatisticSelector(Selector):
    pass


class TargetSelector(Selector):
    pass


class TemplateSelector(Selector):
    pass


class TextSelector(Selector):
    pass


class ThemeSelector(Selector):
    pass


class TimeSelector(Selector):
    pass


class TriggerSelector(Selector):
    pass


class ActionSelectorConfig(_SelectorConfig):
    pass


class AppSelectorConfig(_SelectorConfig):
    pass


class AreaSelectorConfig(_SelectorConfig):
    pass


class AssistPipelineSelectorConfig(_SelectorConfig):
    pass


class AttributeSelectorConfig(_SelectorConfig):
    pass


class AutomationBehaviorConfig(_SelectorConfig):
    pass


class BackupLocationSelectorConfig(_SelectorConfig):
    pass


class BaseSelectorConfig(_SelectorConfig):
    pass


class BooleanSelectorConfig(_SelectorConfig):
    pass


class ChooseSelectorChoiceConfig(_SelectorConfig):
    pass


class ChooseSelectorConfig(_SelectorConfig):
    pass


class ColorRGBSelectorConfig(_SelectorConfig):
    pass


class ColorTempSelectorConfig(_SelectorConfig):
    pass


class ConditionSelectorConfig(_SelectorConfig):
    pass


class ConfigEntrySelectorConfig(_SelectorConfig):
    pass


class ConstantSelectorConfig(_SelectorConfig):
    pass


class ConversationAgentSelectorConfig(_SelectorConfig):
    pass


class CountrySelectorConfig(_SelectorConfig):
    pass


class DateSelectorConfig(_SelectorConfig):
    pass


class DateTimeSelectorConfig(_SelectorConfig):
    pass


class DeviceFilterSelectorConfig(_SelectorConfig):
    pass


class DeviceSelectorConfig(_SelectorConfig):
    pass


class DurationSelectorConfig(_SelectorConfig):
    pass


class EntityFilterSelectorConfig(_SelectorConfig):
    pass


class EntityWithDeviceFilterSelectorConfig(_SelectorConfig):
    pass


class FileSelectorConfig(_SelectorConfig):
    pass


class FloorSelectorConfig(_SelectorConfig):
    pass


class IconSelectorConfig(_SelectorConfig):
    pass


class LabelSelectorConfig(_SelectorConfig):
    pass


class LanguageSelectorConfig(_SelectorConfig):
    pass


class LocationSelectorConfig(_SelectorConfig):
    pass


class MediaSelectorConfig(_SelectorConfig):
    pass


class NumberSelectorConfig(_SelectorConfig):
    pass


class NumericThresholdSelectorConfig(_SelectorConfig):
    pass


class ObjectSelectorConfig(_SelectorConfig):
    pass


class ObjectSelectorField(_SelectorConfig):
    pass


class QrCodeSelectorConfig(_SelectorConfig):
    pass


class SelectOptionDict(_SelectorConfig):
    pass


class SelectSelectorConfig(_SelectorConfig):
    pass


class SerialPortSelectorConfig(_SelectorConfig):
    pass


class StateSelectorConfig(_SelectorConfig):
    pass


class StatisticSelectorConfig(_SelectorConfig):
    pass


class TargetSelectorConfig(_SelectorConfig):
    pass


class TemplateSelectorConfig(_SelectorConfig):
    pass


class TextSelectorConfig(_SelectorConfig):
    pass


class ThemeSelectorConfig(_SelectorConfig):
    pass


class TimeSelectorConfig(_SelectorConfig):
    pass


class TriggerSelectorConfig(_SelectorConfig):
    pass


def selector(config: Any) -> Selector:
    """Build a selector from its serialized form."""
    return Selector(config)
