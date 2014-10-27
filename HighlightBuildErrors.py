import sublime, sublime_plugin
import importlib
import re
import os

REGION_KEY = "build_errors"
REGION_SCOPE = "invalid"

try:
    defaultExec = importlib.import_module("Better Build System").BetterBuidSystem
except:
    defaultExec = importlib.import_module("Default.exec")

global_errors = {}

def normalize_path(file_name):
    return os.path.normcase(os.path.abspath(file_name))

def update_errors_in_view(view):
    file_name = view.file_name()
    if file_name != None:
        file_name = normalize_path(file_name)
        regions = [e.get_region(view) for e in global_errors if e.file_name == file_name]
        view.add_regions(REGION_KEY, regions, REGION_SCOPE)

def remove_errors_in_view(view):
    view.erase_regions(REGION_KEY)

class ViewEventListener(sublime_plugin.EventListener):
    def on_load_async(self, view):
        update_errors_in_view(view)

    def on_activated_async(self, view):
        update_errors_in_view(view)

class ErrorLine:
    def __init__(self, matchObject):
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

    def get_region(self, view):
        if self.line == None:
            return None;
        if self.column == None:
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

    def parse(self, text):
        return [ErrorLine(m) for m in self.regex.finditer(text)]

class ExecCommand(defaultExec.ExecCommand):

    def finish(self, proc):

        super(ExecCommand, self).finish(proc)

        output = self.output_view.substr(sublime.Region(0, self.output_view.size()))
        error_pattern = self.output_view.settings().get("result_file_regex")
        error_parser = ErrorParser(error_pattern)

        global global_errors
        global_errors = error_parser.parse(output)

        for view in self.window.views():
            update_errors_in_view(view)