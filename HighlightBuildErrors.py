import sublime, sublime_plugin
import importlib
import re
import os

SETTINGS_FILE = "HighlightBuildErrors.sublime-settings"
REGION_KEY_PREFIX = "build_errors_color"
REGION_FLAGS = {
    "none": sublime.HIDDEN,
    "fill": 0,
    "outline": sublime.DRAW_NO_FILL,
    "solid_underline": sublime.DRAW_NO_FILL|sublime.DRAW_NO_OUTLINE|sublime.DRAW_SOLID_UNDERLINE,
    "stippled_underline":  sublime.DRAW_NO_FILL|sublime.DRAW_NO_OUTLINE|sublime.DRAW_STIPPLED_UNDERLINE,
    "squiggly_underline":  sublime.DRAW_NO_FILL|sublime.DRAW_NO_OUTLINE|sublime.DRAW_SQUIGGLY_UNDERLINE
}
STATUS_MESSAGE_KEY = "highlight_build_errors:message"

try:
    defaultExec = importlib.import_module("Better Build System").BetterBuidSystem
except:
    defaultExec = importlib.import_module("Default.exec")

try:
    ansiEscape = importlib.import_module("ANSIescape").ansi
except:
    pass

g_errors = {}
g_show_errors = True
g_auto_show_messages = True
g_color_configs = []
g_settings = sublime.load_settings(SETTINGS_FILE)

def plugin_loaded():
    settings = sublime.load_settings(SETTINGS_FILE)
    settings.add_on_change("colors", load_config)
    load_config()

def load_config():
    global g_color_configs, g_default_color, g_settings

    g_settings = settings = sublime.load_settings(SETTINGS_FILE)
    g_color_configs = settings.get("colors", [{"color": "sublimelinter.mark.error"}])

    for config in g_color_configs:
        if "regex" in config:
            config["compiled_regex"] = re.compile(config["regex"])

def normalize_path(file_name):
    return os.path.normcase(os.path.abspath(file_name))

def get_file_name_from_view(view):
    file_name = view.file_name()
    if file_name is None:
        return None
    return normalize_path(file_name)

def split_popup_message(message):
    # return [first_line, rest]
    # `rest` maybe an empty string, if `message` is single-line.
    #
    # Makes sure that both `first_line` and the `rest` are fully trimmed (no newlines at ends)
    return list(map(
        lambda x: x.strip(),
        (message.strip() + "\n").split('\n', 1)) # Make strip() return list[2] even when no trailing \n
    )

# displays popup with message for the error the selector is currently on
def show_error_popup(view):
    selected_error = get_selected_error(view)

    if selected_error is None:
        return

    message = split_popup_message(selected_error.message)

    if g_settings.get("popup_truncate", True):
        message = g_settings.get("popup_template", "$1") \
            .replace("$1", message[0])
    else:
        message = g_settings.get("popup_template_extended", "$1<br>$2") \
            .replace("$1", message[0]) \
            .replace("$2", message[1])

    view.set_status(STATUS_MESSAGE_KEY, message)
    view.show_popup(message, max_width = g_settings.get("popup_max_width", 320), \
                             max_height = g_settings.get("popup_max_height", 240))

def get_selected_error(view):
    file_name = get_file_name_from_view(view)
    return next((e for e in g_errors if e.file_name == file_name and e.get_region(view).contains(view.sel()[0])), None)

def update_errors_in_view(view):
    global g_color_configs, g_default_color
    file_name = get_file_name_from_view(view)
    if file_name is None:
        return

    for idx, config in enumerate(g_color_configs):
        region_key = REGION_KEY_PREFIX + str(idx)
        scope = config["scope"] if "scope" in config else "invalid"
        icon = config["icon"] if "icon" in config else ""
        default_display = "fill" if "scope" in config else "none"
        display = config["display"] if "display" in config else default_display
        if g_show_errors:
            regions = [e.get_region(view) for e in g_errors if e.file_name == file_name and e.color_index == idx]
            view.add_regions(region_key, regions, scope, icon, REGION_FLAGS[display])
        else:
            view.erase_regions(region_key)

def update_all_views(window):
    for view in window.views():
        update_errors_in_view(view)

def remove_errors_in_view(view):
    global g_color_configs
    for idx, val in enumerate(g_color_configs):
        view.erase_regions(REGION_KEY_PREFIX + str(idx))

class ViewEventListener(sublime_plugin.EventListener):
    def on_load_async(self, view):
        update_errors_in_view(view)

    def on_activated_async(self, view):
        update_errors_in_view(view)

    def on_selection_modified(self, view):
        view.erase_status(STATUS_MESSAGE_KEY)
        if g_auto_show_messages:
            show_error_popup(view)

def get_filename(matchObject):
    # only keep last line (i've seen a bad regex that capture several lines)
    return normalize_path(matchObject.group(1).splitlines()[-1])

def get_line(matchObject):
    if len(matchObject.groups()) < 3:
        return None
    try:
        return int(matchObject.group(2))
    except ValueError:
        return None

def get_column(matchObject):
    # column is optional, the last one is always the message
    if len(matchObject.groups()) < 4:
        return None
    try:
        return int(matchObject.group(3))
    except ValueError:
        return None

def get_message(matchObject):
    if len(matchObject.groups()) < 3:
        return None
    # column is optional, the last one is always the message
    return matchObject.group(len(matchObject.groups()))


class ErrorLine:
    def __init__(self, matchObject):
        global g_color_configs
        # only keep last line (i've seen a bad regex that capture several lines)
        self.file_name = get_filename(matchObject);
        self.line = get_line(matchObject);
        self.column = get_column(matchObject)
        self.message = get_message(matchObject)
        if self.message == None: return
        self.color_index = 0
        for config in g_color_configs:
            if not "compiled_regex" in config:
                break
            if config["compiled_regex"].search(self.message):
                break
            self.color_index = self.color_index+1;

    def get_region(self, view):
        if self.line is None:
            return None
        if self.column is None:
            point = view.text_point(self.line-1, 0)
            return view.full_line(point)
        point = view.text_point(self.line-1, self.column-1)
        point_class = view.classify(point)
        if point_class & (sublime.CLASS_WORD_START|sublime.CLASS_WORD_END):
            return view.word(point)
        else:
            return view.full_line(point)


class ErrorParser:
    def __init__(self, pattern):
        self.regex = re.compile(pattern, re.MULTILINE)
        if self.regex.groups < 3 or self.regex.groups > 4:
            raise AssertionError("regex must capture filename,line,[column,]message")

    def parse(self, text):
        return [ErrorLine(m) for m in self.regex.finditer(text)]

def doHighlighting(self):
    output = self.output_view.substr(sublime.Region(0, self.output_view.size()))
    error_pattern = self.output_view.settings().get("result_file_regex")
    error_parser = ErrorParser(error_pattern)

    global g_errors
    g_errors = error_parser.parse(output)

    update_all_views(self.window)


class ExecCommand(defaultExec.ExecCommand):

    def finish(self, proc):
        super(ExecCommand, self).finish(proc)
        doHighlighting(self)

try:
    class AnsiColorBuildCommand(ansiEscape.AnsiColorBuildCommand):

        def finish(self, proc):
            super(AnsiColorBuildCommand, self).finish(proc)
            doHighlighting(self)
except:
    pass


class HideBuildErrorsCommand(sublime_plugin.WindowCommand):

    def is_enabled(self):
        return g_show_errors

    def run(self):
        global g_show_errors
        g_show_errors = False
        update_all_views(self.window)


class ShowBuildErrorsCommand(sublime_plugin.WindowCommand):

    def is_enabled(self):
        return not g_show_errors

    def run(self):
        global g_show_errors
        g_show_errors = True
        update_all_views(self.window)


class DisableAutoShowMessagesCommand(sublime_plugin.WindowCommand):

    def is_enabled(self):
        return g_auto_show_messages

    def run(self):
        global g_auto_show_messages
        g_auto_show_messages = False


class EnableAutoShowMessagesCommand(sublime_plugin.WindowCommand):

    def is_enabled(self):
        return not g_auto_show_messages

    def run(self):
        global g_auto_show_messages
        g_auto_show_messages = True


class ShowErrorMessageCommand(sublime_plugin.WindowCommand):

    def is_visible(self):
        return not g_auto_show_messages and get_selected_error(self.window.active_view()) != None

    def run(self):
        show_error_popup(self.window.active_view())
