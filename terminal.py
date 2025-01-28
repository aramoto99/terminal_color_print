import sys
import os
from enum import Enum
from typing import Optional, Union, List, Callable
from functools import wraps
from contextlib import contextmanager
import builtins


class Style(Enum):
    """Text style codes."""

    BOLD = "\033[1m"
    DIM = "\033[2m"
    ITALIC = "\033[3m"
    UNDERLINE = "\033[4m"
    BLINK = "\033[5m"
    REVERSE = "\033[7m"
    HIDDEN = "\033[8m"
    STRIKE = "\033[9m"


class TerminalColor(Enum):
    """Terminal color codes."""

    BLACK = "\033[30m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    LIGHT_GRAY = "\033[37m"
    DEFAULT = "\033[39m"
    DARK_GRAY = "\033[90m"
    LIGHT_RED = "\033[91m"
    LIGHT_GREEN = "\033[92m"
    LIGHT_YELLOW = "\033[93m"
    LIGHT_BLUE = "\033[94m"
    LIGHT_MAGENTA = "\033[95m"
    LIGHT_CYAN = "\033[96m"
    WHITE = "\033[97m"
    RESET = "\033[0m"


class BackgroundColor(Enum):
    """Background color codes."""

    BLACK = "\033[40m"
    RED = "\033[41m"
    GREEN = "\033[42m"
    YELLOW = "\033[43m"
    BLUE = "\033[44m"
    MAGENTA = "\033[45m"
    CYAN = "\033[46m"
    LIGHT_GRAY = "\033[47m"
    DEFAULT = "\033[49m"
    DARK_GRAY = "\033[100m"
    LIGHT_RED = "\033[101m"
    LIGHT_GREEN = "\033[102m"
    LIGHT_YELLOW = "\033[103m"
    LIGHT_BLUE = "\033[104m"
    LIGHT_MAGENTA = "\033[105m"
    LIGHT_CYAN = "\033[106m"
    WHITE = "\033[107m"


def check_terminal_support(func):
    """
    Decorator to check if the terminal supports color output.

    This decorator wraps a function and checks if the terminal supports color output
    by evaluating the `_color_enabled` attribute of the instance (`self`). If color
    output is not supported, it prints the arguments without any color formatting.
    Otherwise, it proceeds to call the original function with the provided arguments.

    Args:
        func (callable): The function to be decorated.

    Returns:
        callable: The wrapped function that checks for color support before execution.
    """

    @wraps(func)
    def wrapper(self, *args, **kwargs):
        if not self._color_enabled:
            print(*args)
            return
        return func(self, *args, **kwargs)

    return wrapper


class ColoredStdout:
    """
    Custom stdout wrapper for handling color codes.

    Attributes:
        terminal (Terminal): The terminal instance that contains the original stdout.
        buffer (list): A list to buffer the text before writing to the original stdout.

    Methods:
        write(text: str) -> None:
            Buffer the text to be written.

        flush() -> None:
            Flush the buffer to the original stdout.
    """

    def __init__(self, terminal):
        self.terminal = terminal
        self.buffer = []

    def write(self, text: str) -> None:
        self.buffer.append(text)

    def flush(self) -> None:
        if self.buffer:
            text = "".join(self.buffer)
            self.terminal._original_stdout.write(text)
            self.terminal._original_stdout.flush()
            self.buffer = []


class Terminal:
    """
    A class to handle terminal printing with colors and styles.

    Attributes:
        _force_color (bool): Whether to force color output.
        _color_enabled (bool): Whether color output is enabled.
        _colors (dict): Mapping of color names to their ANSI codes.
        _backgrounds (dict): Mapping of background color names to their ANSI codes.
        _styles (dict): Mapping of style names to their ANSI codes.
        _original_print (Callable): Original built-in print function.
        _style_stack (list): Stack to keep track of nested styles.

    Methods:
        _get_style_codes(fg_color, bg_color, styles):
            Get the ANSI codes for the given colors and styles.

        _create_styled_print(style_codes):
            Create a styled print function with the given style codes.

        color_context(fg_color="default", bg_color=None, styles=None):
            Context manager to temporarily set the print function to use styles.

        _write_style_begin(fg_color, bg_color, styles):
            Write the beginning style codes to the terminal.

        _write_style_end():
            Write the reset code to the terminal to end styles.

        _format_message(message, prefix=None):
            Format a message with an optional prefix.

        _print_styled(message, prefix=None, fg_color="default", bg_color=None, styles=None):
            Print a styled message with optional prefix and colors.

        print_note(message, bg_color=None, styles=None):
            Print a note message in green.

        print_warning(message, bg_color=None, styles=None):
            Print a warning message in yellow.

        print_error(message, bg_color=None, styles=None):
            Print an error message in red.

        print_info(message, bg_color=None, styles=None):
            Print an info message in cyan.

        cprint(message, fg_color="default", bg_color=None, styles=None):
            Print a custom styled message.
    """

    def __init__(self, force_color: bool = False):
        self._force_color = force_color
        self._color_enabled = force_color or (
            hasattr(sys.stdout, "isatty")
            and sys.stdout.isatty()
            and not os.environ.get("NO_COLOR")
        )
        self._colors = {color.name.lower(): color.value for color in TerminalColor}
        self._backgrounds = {
            color.name.lower(): color.value for color in BackgroundColor
        }
        self._styles = {style.name.lower(): style.value for style in Style}
        self._original_print = builtins.print
        self._style_stack = []

    def _get_style_codes(
        self,
        fg_color: str,
        bg_color: Optional[str],
        styles: Optional[Union[str, List[str]]],
    ) -> str:
        codes = []

        if fg_color:
            try:
                codes.append(self._colors[fg_color.lower()])
            except KeyError:
                self.print_error(f"Invalid color: {fg_color}")
                return ""

        if bg_color:
            try:
                codes.append(self._backgrounds[bg_color.lower()])
            except KeyError:
                self.print_error(f"Invalid background color: {bg_color}")
                return ""

        if styles:
            style_list = [styles] if isinstance(styles, str) else styles
            for style in style_list:
                try:
                    codes.append(self._styles[style.lower()])
                except KeyError:
                    self.print_error(f"Invalid style: {style}")
                    return ""

        return "".join(codes)

    def _create_styled_print(self, style_codes: str) -> Callable:

        def styled_print(*args, **kwargs):
            # Get the separator and end values, or use defaults
            sep = kwargs.get("sep", " ")
            end = kwargs.get("end", "\n")

            # Remove sep and end from kwargs if present
            kwargs.pop("sep", None)
            kwargs.pop("end", None)

            # Convert all arguments to strings
            strings = [str(arg) for arg in args]

            # Join with separator
            message = sep.join(strings)

            # Write the style codes, message, and reset code
            sys.stdout.write(style_codes)
            sys.stdout.write(message)
            sys.stdout.write(TerminalColor.RESET.value)
            sys.stdout.write(end)
            sys.stdout.flush()

        return styled_print

    @contextmanager
    def color_context(
        self,
        fg_color: str = "default",
        bg_color: Optional[str] = None,
        styles: Optional[Union[str, List[str]]] = None,
    ):
        if not self._color_enabled:
            yield
            return

        style_codes = self._get_style_codes(fg_color, bg_color, styles)

        # Store the original print function
        original_print = builtins.print

        try:
            # Replace the built-in print with our styled version
            builtins.print = self._create_styled_print(style_codes)
            yield
        finally:
            # Restore the original print function
            builtins.print = original_print
            # Ensure we're back to normal
            sys.stdout.write(TerminalColor.RESET.value)
            sys.stdout.flush()

    def _write_style_begin(
        self,
        fg_color: str,
        bg_color: Optional[str],
        styles: Optional[Union[str, List[str]]],
    ) -> None:
        codes = []

        # Add color codes
        if fg_color:
            try:
                codes.append(self._colors[fg_color.lower()])
            except KeyError:
                self.print_error(f"Invalid color: {fg_color}")
                return

        if bg_color:
            try:
                codes.append(self._backgrounds[bg_color.lower()])
            except KeyError:
                self.print_error(f"Invalid background color: {bg_color}")
                return

        # Add style codes
        if styles:
            style_list = [styles] if isinstance(styles, str) else styles
            for style in style_list:
                try:
                    codes.append(self._styles[style.lower()])
                except KeyError:
                    self.print_error(f"Invalid style: {style}")
                    return

        if codes:
            self._original_stdout.write("".join(codes))
            self._original_stdout.flush()

    def _write_style_end(self) -> None:
        self._original_stdout.write(TerminalColor.RESET.value)
        self._original_stdout.flush()

    def _format_message(self, message: str, prefix: Optional[str] = None) -> str:
        if prefix:
            return f"[{prefix}] {message}"
        return message

    @check_terminal_support
    def _print_styled(
        self,
        message: str,
        prefix: Optional[str] = None,
        fg_color: str = "default",
        bg_color: Optional[str] = None,
        styles: Optional[Union[str, List[str]]] = None,
    ) -> None:
        formatted_message = self._format_message(message, prefix)
        with self.color_context(fg_color, bg_color, styles):
            print(formatted_message)

    def print_note(
        self,
        message: str,
        bg_color: Optional[str] = None,
        styles: Optional[Union[str, List[str]]] = None,
    ) -> None:
        self._print_styled(message, "NOTE", "green", bg_color, styles)

    def print_warning(
        self,
        message: str,
        bg_color: Optional[str] = None,
        styles: Optional[Union[str, List[str]]] = None,
    ) -> None:
        self._print_styled(message, "WARNING", "yellow", bg_color, styles)

    def print_error(
        self,
        message: str,
        bg_color: Optional[str] = None,
        styles: Optional[Union[str, List[str]]] = None,
    ) -> None:
        self._print_styled(message, "ERROR", "red", bg_color, styles)

    def print_info(
        self,
        message: str,
        bg_color: Optional[str] = None,
        styles: Optional[Union[str, List[str]]] = None,
    ) -> None:
        self._print_styled(message, "INFO", "cyan", bg_color, styles)

    def cprint(
        self,
        message: str,
        fg_color: str = "default",
        bg_color: Optional[str] = None,
        styles: Optional[Union[str, List[str]]] = None,
    ) -> None:
        self._print_styled(message, None, fg_color, bg_color, styles)


# Usage example:
if __name__ == "__main__":
    term = Terminal()

    # Basic usage
    term.print_note("This is a notification")
    term.print_warning("This is a warning")
    term.print_error("This is an error")
    term.print_info("This is an info message")

    # Custom styling
    term.cprint("Bold blue text on yellow background", "blue", "yellow", "bold")

    # Using context manager with normal print statements
    with term.color_context("red", "light_gray", ["bold", "underline"]):
        print("This text is red, bold and underlined with light gray background")
        print("Multiple lines with the same style")

    print("Back to normal text")

    # Multiple styles
    term.cprint("Special text", "magenta", styles=["bold", "italic", "underline"])

    # Error handling
    term.cprint("This will show an error message", "invalid_color")
