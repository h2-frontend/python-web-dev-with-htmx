import re

SQB = '['
AGB = '<'
BAR = '|'
AGB_BAR = '<|'
TAG_TOOL = '[Tool]'
TAG_TOOL_PACKAGE = '[Tool]track_package[Tool][Input]0123456789012[/Input]'
TAG_TOOL_BOOKING = '[Tool]find_reservation[Tool][Input]0123456789012[/Input]'
# Regex for extracting the Tool and Input
RE_TOOL = r'\s*(\[Tool\])\s*(\w+)\s*(\[/Tool\])\s*(\[Input\])\s*(\w+)\s*(\[/Input\])'

class StreamParser:
    START = 0
    TOOLING = 1
    CONTROL = 2 
    END = 3
    TOOLCALL = 11

    def __init__(self):
        self.reset()

    def __str__(self):
        return self.s

    def reset(self):
        self.s = ''
        self.state = self.START

    def check_pass(self, s):
        if not re.search(r'^[|<[]', s): # ^ means anchor to the start of the string
            return True
        return False

    def check_tooling(self, s):
        if len(s)<len(TAG_TOOL) or s.startswith(TAG_TOOL):
            return True
        return False

    def parse_toolcall(self, s):
        m = re.search(RE_TOOL, s)
        g = m.groups()
        if len(g) != 6:
            return None
        return (g[1], g[4])

    def parse_stream(self, s):
        if not s:
            return (self.state, '')
        elif self.state == self.START:
            if self.check_pass(s):
                return (self.state, s)
            else:
                if re.search(r'^\s*\[', s):
                    self.state = self.TOOLING
                    self.s += s.strip()
                    return (self.state, '')
                elif re.search(r'^\s*<', s):
                    self.state = self.CONTROL
                    self.s += s
                    return (self.state, '')
                else:
                    self.state = self.END
                    return (self.state, '')
        elif self.state == self.TOOLING:
            self.s += s
            if not self.check_tooling(self.s):
                temp = self.s
                self.reset()
                return (self.state, temp)
            else:
                if re.search(r'\[/Input\]\s*$', self.s):
                    m = self.parse_toolcall(self.s)
                    if not m:
                        temp = self.s
                        self.reset()
                        return (self.state, temp)
                    self.state = self.END
                    return (self.TOOLCALL, m)
                else:
                    return (self.state, '')
        elif self.state == self.CONTROL:
            self.s += s
            if re.search(r'^\s*<|', s):
                self.state = self.END
                return (self.state, '')
            else:
                temp = self.s
                self.reset()
                return (self.state, temp)
        else:
            return (self.state, '')