"""
Source: https://github.com/LonamiWebs/Telethon/blob/v1/telethon/extensions/html.py

Simple HTML -> entity parser.
"""
import html
import struct
import traceback
from collections import deque
from dataclasses import dataclass, field
from html.parser import HTMLParser

import mistletoe

from .attribute_types import AttributeConnector
from typing import Union, Optional


@dataclass
class MessageEntity:
    offset: int
    length: int
    _attribute_connector: Optional[AttributeConnector] = field(default=None)
    # _attribute_connector: AttributeConnector = None

    @property
    def attribute_connector(self) -> AttributeConnector:
        if self._attribute_connector is None:
            self._attribute_connector = AttributeConnector()
        return self._attribute_connector


@dataclass
class MessageEntityFont(MessageEntity):
    color: Union[str, list] = field(default_factory=lambda: [255, 255, 255, 255])
    size: Union[int, None] = None


class MessageEntityBold(MessageEntity): ...


class MessageEntityItalic(MessageEntity): ...


class MessageEntityStrike(MessageEntity): ...


class MessageEntityUnderline(MessageEntity): ...


class MessageEntitySpoiler(MessageEntity): ...  # TODO


@dataclass
class MessageEntityBlockquote(MessageEntity):  # noqa
    depth: int = field(default=10)


class MessageEntityCode(MessageEntity): ...


@dataclass
class MessageEntityPre(MessageEntity):  # noqa
    language: str = field(default="")


@dataclass
class MessageEntityTextUrl(MessageEntity):  # noqa
    url: str = field(default="")


class MessageEntityUrl(MessageEntityTextUrl): ...  # TODO


class MessageEntityEmail(MessageEntity): ...  # TODO


@dataclass
class MessageEntityList(MessageEntity):  # noqa
    depth: int = field(default=0)
    task: bool = False
    task_done: bool = False


@dataclass
class MessageEntityUnorderedList(MessageEntityList):  ...  # noqa


@dataclass
class MessageEntityOrderedList(MessageEntityList):  # noqa
    index: int = field(default=0)


class MessageEntitySeparator(MessageEntity): ...


class MessageEntityH1(MessageEntity): ...


class MessageEntityH2(MessageEntity): ...


class MessageEntityH3(MessageEntity): ...


class MessageEntityH4(MessageEntity): ...


class MessageEntityH5(MessageEntity): ...


class MessageEntityH6(MessageEntity): ...


def _strip_text(text, entities):
    """
    Strips whitespace from the given text modifying the provided entities.
    This assumes that there are no overlapping entities, that their length
    is greater or equal to one, and that their length is not out of bounds.
    """
    if not entities:
        return text.strip()
    while text and text[-1].isspace():
        e = entities[-1]
        if e.offset + e.length == len(text):
            if e.length == 1:
                del entities[-1]
                if not entities:
                    return text.strip()
            else:
                e.length -= 1
        text = text[:-1]

    while text and text[0].isspace():
        for i in reversed(range(len(entities))):
            e = entities[i]
            if e.offset != 0:
                e.offset -= 1
                continue

            if e.length == 1:
                del entities[0]
                if not entities:
                    return text.lstrip()
            else:
                e.length -= 1

        text = text[1:]

    return text


def _add_surrogate(text):
    return ''.join(
        ''.join(chr(y) for y in struct.unpack('<HH', x.encode('utf-16le')))
        if (0x10000 <= ord(x) <= 0x10FFFF) else x for x in text
    )


def _del_surrogate(text):
    return text.encode('utf-16', 'surrogatepass').decode('utf-16')


class _HTMLToParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.text = ''
        self.entities = []
        self._building_entities = {}
        self._open_tags = deque()
        self._open_tags_meta = deque()

        self.blockquote_depth = 0

        self.li_open_count = 0
        self.opened_list_depth = []
        self.ordered_list_index_by_depth = {}

    def handle_starttag(self, tag, attrs):
        self._open_tags.appendleft(tag)
        self._open_tags_meta.appendleft(None)

        attrs = dict(attrs)
        EntityType = None
        args = {}
        if tag in ["strong", "b"]:
            EntityType = MessageEntityBold
        elif tag in ["em", "i"]:
            EntityType = MessageEntityItalic
        elif tag == "u":
            EntityType = MessageEntityUnderline
        elif tag in ["del", "s"]:
            EntityType = MessageEntityStrike
        elif tag == "spoiler":
            EntityType = MessageEntitySpoiler
        elif tag == "blockquote":
            EntityType = MessageEntityBlockquote
            self.blockquote_depth += 1
            args["depth"] = self.blockquote_depth
            tag = f'{tag}_{self.blockquote_depth}'
        elif tag == "code":
            try:
                pre = self._building_entities['pre']
                try:
                    pre.language = attrs['class'][len('language-'):]
                except KeyError:
                    pass
            except KeyError:
                EntityType = MessageEntityCode
        elif tag == "pre":
            EntityType = MessageEntityPre
            args['language'] = ''
        elif tag == "a":
            url = attrs.get("href", None)
            if not url:
                return
            if url.startswith('mailto:'):
                url = url[len('mailto:'):]  # Use slicing for older Python versions
                EntityType = MessageEntityEmail
            else:
                if self.get_starttag_text() == url:
                    EntityType = MessageEntityUrl
                else:
                    EntityType = MessageEntityTextUrl
                    args['url'] = url
                    url = None
            self._open_tags_meta.popleft()
            self._open_tags_meta.appendleft(url)
        elif tag in ["font", "span"]:
            EntityType = MessageEntityFont
            color = attrs.get("color", None)
            size = attrs.get("size", None)
            style_string = attrs.get("style", None)
            if style_string:
                try:
                    style_dict = {}
                    for style in style_string.split(";"):
                        key_value = style.split(":", 1)
                        if len(key_value) == 2:
                            style_dict[key_value[0]] = key_value[1].strip()
                    color = style_dict.get("color", None)
                    if color:
                        color = color.replace("rgb", "").replace("a", "")
                except Exception:
                    traceback.print_exc()

            if color:
                args["color"] = color
            if size:
                args["size"] = size
        elif tag == "ol":
            self.opened_list_depth.append(MessageEntityOrderedList)
            ordered_list_index = attrs.get("start", 1)
            try:
                ordered_list_index = int(ordered_list_index)
            except Exception:
                ordered_list_index = 1
                traceback.print_exc()
            finally:
                self.ordered_list_index_by_depth[len(self.opened_list_depth)] = ordered_list_index
        elif tag == "ul":
            self.opened_list_depth.append(MessageEntityUnorderedList)
        elif tag == "li":
            self.li_open_count += 1
            tag = f"{tag}_{self.li_open_count}"
            if 'task' in attrs:
                args['task'] = True
            elif 'task-done' in attrs:
                args['task'] = True
                args['task_done'] = True

            EntityType = self.opened_list_depth[-1]
            args["depth"] = len(self.opened_list_depth)
            if EntityType is MessageEntityOrderedList:
                args["index"] = self.ordered_list_index_by_depth[len(self.opened_list_depth)]
                self.ordered_list_index_by_depth[len(self.opened_list_depth)] += 1
        elif tag == "hr":
            EntityType = MessageEntitySeparator
        elif tag == "h1":
            EntityType = MessageEntityH1
        elif tag == "h2":
            EntityType = MessageEntityH2
        elif tag == "h3":
            EntityType = MessageEntityH3
        elif tag == "h4":
            EntityType = MessageEntityH4
        elif tag == "h5":
            EntityType = MessageEntityH5
        elif tag == "h6":
            EntityType = MessageEntityH6

        if EntityType is not None and tag not in self._building_entities:
            self._building_entities[tag] = EntityType(
                offset=len(self.text),
                # The length will be determined when closing the tag.
                length=0,
                **args)

    def handle_data(self, text):
        previous_tag = self._open_tags[0] if len(self._open_tags) > 0 else ''
        if previous_tag == 'a':
            url = self._open_tags_meta[0]
            if url:
                text = url

        text = html.unescape(text)
        for tag, entity in self._building_entities.items():
            entity.length += len(text)

        self.text += text

    def handle_endtag(self, tag):
        try:
            self._open_tags.popleft()
            self._open_tags_meta.popleft()
        except IndexError:
            pass
        if tag == "blockquote":
                tag = f"{tag}_{self.blockquote_depth}"
                self.blockquote_depth -= 1
        elif tag == "ol":
                self.ordered_list_index_by_depth[len(self.opened_list_depth)] = 1
                del self.opened_list_depth[-1]
        elif tag == "ul":
                del self.opened_list_depth[-1]
        elif tag == "li":
                tag = f"{tag}_{self.li_open_count}"
                self.li_open_count += -1
        entity = self._building_entities.pop(tag, None)
        if not entity:
            return

        self.entities.append(entity)


try:
    import pygments
    from pygments import highlight
    from pygments.formatters.html import HtmlFormatter
    from pygments.lexers import get_lexer_by_name as get_lexer, guess_lexer


    class _PygmentsRenderer(mistletoe.HTMLRenderer):
        formatter = HtmlFormatter(style='monokai')
        formatter.noclasses = True

        def __init__(self, *extras):
            super().__init__(*extras)

        def render_block_code(self, token):
            code = token.children[0].content
            try:
                lexer = get_lexer(token.language) if token.language else guess_lexer(code)
            except pygments.util.ClassNotFound:  # noqa
                return f"<pre>{code}</pre>"
            return highlight(code, lexer, self.formatter)
except ModuleNotFoundError:
    class _PygmentsRenderer(mistletoe.HTMLRenderer):
        ...


def parse(html_text: str) -> [str, list]:
    """
    Parses the given HTML message and returns its stripped representation
    plus a list of the MessageEntity's that were found.

    :param html: the message with HTML to be parsed.
    :return: a tuple consisting of (clean message, [message entities]).
    """
    if not html_text:
        return html_text, []
    # html_text = html.unescape(_MarkdownIt.render(html_text))
    html_text = mistletoe.markdown(html_text, renderer=_PygmentsRenderer)

    html_text = html_text.replace('<blockquote>\n', '<blockquote>').replace('\n</blockquote>', '</blockquote>')
    html_text = html_text.replace('<li>\n', '<li>').replace('\n</li>', '</li>')
    html_text = html_text.replace('<ul>\n', '<ul>').replace('\n</ul>', '</ul>')
    html_text = html_text.replace('<ol>\n', '<ol>').replace('\n</ol>', '</ol>')
    html_text = html_text.replace('\n<ol start="', '<ol start="')

    html_text = html_text.replace('\n</pre>', '</pre>')

    html_text = html_text.replace('\n</br>', '\n')
    html_text = html_text.replace('</br>', '\n')
    # task list support
    html_text = html_text.replace("<li>[x] ", "<li>[X] ")
    html_text = html_text.replace("<li>[X] ", "<li task-done>")
    html_text = html_text.replace("<li>[ ] ", "<li task>")

    # html_text = html_text.replace("<hr /> ", "<hr />\n")

    parser = _HTMLToParser()
    parser.feed(_add_surrogate(html_text))
    text = _strip_text(parser.text, parser.entities)
    return _del_surrogate(text), parser.entities
