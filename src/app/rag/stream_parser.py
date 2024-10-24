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
        #if not re.search(r'^[\|<[]', s): # ^ means anchor to the start of the string
        if not re.search(r'^[[]', s): # ^ means anchor to the start of the string
            return True
        return False

    def check_tooling(self, s):
        if len(s)<len(TAG_TOOL) or s.startswith(TAG_TOOL):
            return True
        return False

    def parse_toolcall(self, s):
        m = re.search(RE_TOOL, s)
        if m:
            g = m.groups()
            if len(g) != 6:
                return None
            return (g[1], g[4])
        return None

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
        else:
            return (self.state, '')

if __name__ == '__main__':
    stream_parser = StreamParser()
    s2 = "안녕하세요! 한진택배의 온라인 고객 상담원입니다. 택배 서비스에 관한 질문에 도움을 드리겠습니다. 다만 택배 서비스와 관련 없는 질문은 답변드릴 수 없다는 점을 이해해 주세요.\n\n운송장 번호를 제공해 주시면 배송 상태를 확인해 드리겠습니다. 운송장 번호를 알려주시면, 다음 형식을 사용하여 답변을 드리겠습니다:\n\n[Tool]track_package[/Tool] [Input]tracking_number[/Input]\n\n운송장 번호를 알려주시면 최선을 다해 도와드리겠습니다."
    s = "안녕하세요! 관련 없는 질문은 답변드릴 수 없다는 점을 이해해 주세요.\n\n운송장 번호를 알려주시면, 다음 형식을 사용하여 답변을 드리겠습니다:\n\n[Tool]track_package[/Tool] [Input]tracking_number[/Input]\n\n운송장 번호를 알려주시면 최선을 다해 도와드리겠습니다."

    res = ''
    valid_response = True
    for c in s:
        if valid_response:
            state, answer = stream_parser.parse_stream(c)
            if state==stream_parser.END:
                valid_response = False
            elif state==stream_parser.TOOLING:
                continue
            elif state==stream_parser.TOOLCALL:
                print(f"\n\n{'*'*50}\nToolcall: {answer}\n\n", flush=True)
                #output = call_api(*answer)
                res += f"Toolcall: {answer}\n"
                valid_response = False
            #elif state==stream_parser.CONTROL:
            #    continue
            elif state==stream_parser.START:
                res += answer
            print(f'\n=======\n{res}')