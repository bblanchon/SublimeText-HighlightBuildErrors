import sublime, sublime_plugin
import importlib
import re
import os

SETTINGS_FILE = "HighlightBuildErrors.sublime-settings"
REGION_KEY = "build_errors_"

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
g_error_color = "invalid"
g_error_colors = {"error" : {"regexp" : ".*", "color" : "invalid"}}

def plugin_loaded():    
    settings = sublime.load_settings(SETTINGS_FILE)
    settings.add_on_change("default_color", update_error_color)
    settings.add_on_change("colors", update_error_color)
    update_error_color()

def update_error_color():
    global g_error_colors, g_error_color
    settings = sublime.load_settings(SETTINGS_FILE)
    g_error_color = settings.get("default_color","invalid")
    g_error_colors = settings.get("colors", {"error" : {"regexp" : ".*", "color" : g_error_color}})

def normalize_path(file_name):
    return os.path.normcase(os.path.abspath(file_name))

def update_errors_in_view(view):
    file_name = view.file_name()
    if file_name is None:
        return
    if g_show_errors:
        file_name = normalize_path(file_name)
        regions = {}
        for e in g_errors:
            if e.file_name != file_name: continue
            if e.error_type not in regions:
                regions[e.error_type] = []
            regions[e.error_type].append(e.get_region(view))
        for reg in regions.keys():
            view.add_regions(REGION_KEY+reg, regions[reg], g_error_colors.get(reg,"error").get("color",g_error_color))
    else:
        for reg in g_error_colors.keys():
            view.erase_regions(REGION_KEY+reg)

def update_all_views(window):
    for view in window.views():
        update_errors_in_view(view)

def remove_errors_in_view(view):
    for reg in g_error_colors.keys():
        view.erase_regions(REGION_KEY+reg)

class ViewEventListener(sublime_plugin.EventListener):
    def on_load_async(self, view):
        update_errors_in_view(view)

    def on_activated_async(self, view):
        update_errors_in_view(view)

class ErrorLine:
    def __init__(self, matchObject):
        global g_error_colors
        # only keep last line (i've seen a bad regex that capture several lines)
        self.file_name = normalize_path(matchObject.group(1).splitlines()[-1])
        try:
            self.line = int(matchObject.group(2))
        except:
            self.line = None
        try:
            self.column = int(matchObject.group(3))
        except:
            self.column = None
        self.error_message = matchObject.group(4)
        try:
            for cc in g_error_colors.keys():
                if re.search(g_error_colors.get(cc).get("regexp",cc), matchObject.group(4)):
                    self.error_type = cc
                    break
        except:
            self.error_type = "error"

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
