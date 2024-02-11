import os
from os.path import isfile, join


class Directory:
    contents = []
    name = ""
    path = ""
    tag = ""  # Unique identifyer

    def __init__(self, path, name=None):
        self.path = path
        self.tag = f"dir_{path}"
        if name:
            self.name = name
        else:
            self.name = os.path.dirname(path)
        print(f"Found directory: {name}")
        self.crawl_contents(path)

    def crawl_contents(self, path):
        dirs = []
        files = []
        for item in os.listdir(path):
            if isfile(join(path, item)):
                files.append(File(join(path, item), name=item))
            else:
                dirs.append(Directory(join(path, item), name=item))
        self.contents = dirs + files

class File:
    name = ""
    path = ""
    tag = ""  # Unique identifyer

    def __init__(self, path, name=None):
        self.path = path
        self.tag = f"file_{path}"
        if name:
            self.name = name
        else:
            self.name = os.path.basename(path)
        print(f"Found file: {name}")
        self.what_am_i()

    def what_am_i(self):
        pass  # TODO: whats this file equivalent of evaluating itself.
