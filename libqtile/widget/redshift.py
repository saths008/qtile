import subprocess

from libqtile.command.base import expose_command
from libqtile.log_utils import logger
from libqtile.widget import base
from libqtile.widget.base import _TextBox

# each with a slider like PulseVolume?
#
# * Fix text resizing when pressing button (imagine user uses different messages)
# * Fix parameters
# * Make icons larger
# * Add comments and docs
# *


class GammaGroup:
    """
    Helper class to store redshift gamma settings
    """

    def __init__(self, red, green, blue):
        self.red = red
        self.green = green
        self.blue = blue

    def _redshift_fmt(self) -> str:
        return f"{self.red}:{self.green}:{self.blue}"

    def __repr__(self) -> str:
        return f"Gamma: {self._redshift_fmt()}"

    def __str__(self) -> str:
        return f"GammaGroup(red={self.red}, green={self.green}, blue={self.blue})"


class RedshiftDriver:
    # returns 1 on success, 0 on error
    def enable(self, temperature, gamma: GammaGroup, brightness) -> int:
        success_code = 1
        try:
            command = subprocess.run(
                [
                    "redshift",
                    "-P",
                    "-O",
                    str(temperature),
                    "-b",
                    str(brightness),
                    "-g",
                    gamma._redshift_fmt(),
                ],
                check=True,
            )
            logger.debug(command.args)
        except Exception:
            success_code = 0
            logger.exception(
                f"Exception trying to set redshift, temperature:{temperature}, gamma: {gamma}, brightness: {brightness}"
            )
        finally:
            return success_code

    # returns 1 on success, 0 on error
    def reset(self) -> int:
        success_code = 1
        try:
            subprocess.run(["redshift", "-x"], check=True)
        except Exception:
            success_code = 0
            logger.exception("Exception trying to reset redshift temperature")
        finally:
            return success_code


class Redshift(_TextBox, base.PaddingMixin):
    redshift_driver = RedshiftDriver()
    orientations = base.ORIENTATION_HORIZONTAL

    defaults = [
        ("brightness", 1.0, "Redshift brightness"),
        ("disabled_txt", "󱠃", "Redshift disabled text"),
        ("enabled_txt", "󰛨", "Redshift enabled text"),
        ("gamma_red", 1.0, "Redshift gamma red"),
        ("gamma_blue", 1.0, "Redshift gamma blue"),
        ("gamma_green", 1.0, "Redshift gamma green"),
        ("font", "sans", "Default font"),
        ("fontsize", 20, "Font size"),
        ("foreground", "ffffff", "Font colour for information text"),
        ("temperature", 1700, "Redshift temperature to set when enabled"),
    ]

    _dependencies = ["redshift"]

    def __init__(self, **config):
        """
        Note that disabled_txt and enabled_txt use nerd icons, ensure that a nerd font is installed else you
        probably want to change those values.
        """
        _TextBox.__init__(self, **config)
        self.add_defaults(Redshift.defaults)
        self.add_defaults(base.PaddingMixin.defaults)
        self.is_enabled = False
        self._line_index = 0
        self._lines = []
        self.add_callbacks(
            {
                "Button1": self.click,
                "Button4": self.scroll_up,
                "Button5": self.scroll_down,
            }
        )

    def _configure(self, qtile, bar):
        _TextBox._configure(self, qtile, bar)
        # reset, so we know it is in some known in
        # initial state
        self.reset_redshift()
        self._set_lines()
        self._set_text()

    def draw(self):
        self.drawer.clear(self.background or self.bar.background)
        self._set_text()
        _TextBox.draw(self)

    def format_object(self, obj):
        """Takes the given object and returns a formatted string representing the object."""
        if isinstance(obj, GammaGroup):
            return repr(obj)
        elif isinstance(obj, str):
            return obj
        else:
            logger.warning(
                "redshift: format_object: obj didn't match any of the instance types, returning empty string"
            )
            return ""

    @expose_command
    def scroll_up(self):
        """Scroll up to next item."""
        self._scroll(1)

    @expose_command
    def scroll_down(self):
        """Scroll down to next item."""
        self._scroll(-1)

    def show_line(self):
        """Formats the text of the current menu item."""
        if not self._lines:
            return

        obj = self._lines[self._line_index]

        self.update(self.format_object(obj))

    @expose_command
    def enable_redshift(self):
        gamma_val = GammaGroup(self.gamma_red, self.gamma_green, self.gamma_blue)
        success_code = self.redshift_driver.enable(self.temperature, gamma_val, self.brightness)
        if not success_code:
            self._render_error_text()

    @expose_command
    def click(self):
        # Only allow clicking
        # for the first index ie. the default text
        if self._line_index != 0:
            return
        if self.is_enabled:
            self.reset_redshift()
        else:
            self.enable_redshift()
        self.is_enabled = not self.is_enabled
        self._set_text()
        self.bar.draw()

    def _render_error_text(self):
        self.text = "Redshift widget error"
        self.bar.draw()

    @expose_command
    def reset_redshift(self):
        success_code = self.redshift_driver.reset()
        if not success_code:
            self._render_error_text()

    def _scroll(self, step):
        self._set_lines()
        self._line_index = (self._line_index + step) % len(self._lines)
        self.show_line()

    def _set_lines(self):
        first_text = ""
        if self.is_enabled:
            first_text = self.enabled_txt
        else:
            first_text = self.disabled_txt

        first_text = self._format_first_text(str(first_text))

        self._lines = [
            first_text,
            f"Brightness: {self.brightness}",
            f"Temperature: {self.temperature}",
            GammaGroup(self.gamma_red, self.gamma_green, self.gamma_blue),
        ]

    # controls what happens when the widget is pressed
    def _set_text(self):
        if self._line_index == 0:
            if self.is_enabled:
                self.text = self._format_first_text(str(self.enabled_txt))
            else:
                self.text = self._format_first_text(str(self.disabled_txt))
        else:
            self.text = self.format_object(self._lines[self._line_index])

    # format text with the parameters allowed
    def _format_first_text(self, txt: str) -> str:
        return txt.format(
            brightness=self.brightness,
            temperature=self.temperature,
            gamma_red=self.gamma_red,
            gamma_green=self.gamma_green,
            gamma_blue=self.gamma_blue,
            is_enabled=self.is_enabled,
        )
