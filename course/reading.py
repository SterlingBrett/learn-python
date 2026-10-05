"""The reading pane: shows lesson text with headings, lists, code and links."""

import re
import tkinter as tk
import webbrowser

INLINE_RE = re.compile(
    r'(?P<code>`[^`\n]+`)'
    r'|(?P<bold>\*\*[^*\n]+\*\*)'
    r'|(?P<image>!\[[^\]]*\]\([^)\s]+\))'
    r'|(?P<link>\[[^\]]+\]\([^)\s]+\))'
    r'|(?P<url>https?://[^\s)>\]]+)'
)
BULLET_RE = re.compile(r'^(\s*)(?:[-*•]|\d+[.)])\s+(.*)$')
UNDERLINE_RE = re.compile(r'^\s*(-{3,}|={3,})\s*$')


class ReadingPane(tk.Text):
    """A read-only Text widget with a few helpers for writing formatted lessons."""

    def __init__(self, master, fonts, colors, **kwargs):
        super().__init__(
            master, wrap='word', padx=24, pady=16, borderwidth=0, highlightthickness=0,
            cursor='arrow', font=fonts['body'], background=colors['paper'],
            foreground=colors['text'], spacing1=2, spacing3=2, **kwargs)
        self._link_count = 0
        self.tag_configure('title', font=fonts['title'], foreground=colors['heading'],
                           spacing3=4)
        self.tag_configure('subtitle', foreground=colors['muted'], spacing3=10)
        self.tag_configure('h1', font=fonts['h1'], foreground=colors['heading'],
                           spacing1=14, spacing3=6)
        self.tag_configure('h2', font=fonts['h2'], foreground=colors['heading'],
                           spacing1=12, spacing3=4)
        self.tag_configure('para', spacing3=8)
        self.tag_configure('bullet', lmargin1=12, lmargin2=28, spacing3=3)
        self.tag_configure('bullet2', lmargin1=36, lmargin2=52, spacing3=3)
        self.tag_configure('code', font=fonts['mono'], background=colors['code_bg'])
        self.tag_configure('codeblock', font=fonts['mono'], background=colors['code_bg'],
                           lmargin1=12, lmargin2=12, rmargin=12, spacing1=0, spacing3=0)
        self.tag_configure('gap', font=fonts['small'])
        self.tag_configure('bold', font=fonts['bold'])
        self.tag_configure('note', foreground=colors['muted'])
        self.tag_configure('link', foreground=colors['link'], underline=True)
        self.tag_bind('link', '<Enter>', lambda _event: self.configure(cursor='hand2'))
        self.tag_bind('link', '<Leave>', lambda _event: self.configure(cursor='arrow'))
        self.configure(state='disabled')

    # -- Writing -----------------------------------------------------------

    def clear(self):
        """Empty the pane and forget old links."""
        self.configure(state='normal')
        self.delete('1.0', 'end')
        for tag in self.tag_names():
            if tag.startswith('link-'):
                self.tag_delete(tag)
        self._link_count = 0

    def finish(self):
        """Lock the pane again and scroll to the top."""
        self.configure(state='disabled')
        self.yview_moveto(0)

    def write(self, text, *tags):
        """Append plain text with the given tags."""
        self.insert('end', text, tags)

    def write_inline(self, text, *tags):
        """Append text, turning `code`, **bold**, [links](url) and bare URLs into styles."""
        position = 0
        for match in INLINE_RE.finditer(text):
            if match.start() > position:
                self.write(text[position:match.start()], *tags)
            kind = match.lastgroup
            token = match.group()
            if kind == 'code':
                self.write(token[1:-1], 'code', *tags)
            elif kind == 'bold':
                self.write(token[2:-2], 'bold', *tags)
            elif kind == 'image':
                alt = token[2:token.index(']')]
                if alt:
                    self.write(f'[image: {alt}]', 'note', *tags)
            elif kind == 'link':
                label, url = token[1:-1].split('](', 1)
                self.write_link(label, url, *tags)
            else:
                self.write_link(token, token, *tags)
            position = match.end()
        self.write(text[position:], *tags)

    def write_link(self, label, url, *tags):
        """Append a clickable link that opens in the web browser."""
        self._link_count += 1
        tag = f'link-{self._link_count}'
        self.write(label, 'link', tag, *tags)
        self.tag_bind(tag, '<Button-1>', lambda _event, address=url: open_url(address))

    def heading(self, text, level=1):
        """Append a heading."""
        self.write(text.strip() + '\n', 'h1' if level <= 1 else 'h2')

    def code_block(self, text):
        """Append a block of code in a monospaced box."""
        self.write(text.rstrip('\n') + '\n', 'codeblock')
        self.write('\n', 'gap')

    def bullet(self, text, depth=0):
        """Append one list item."""
        tag = 'bullet' if depth == 0 else 'bullet2'
        self.write('•  ' if depth == 0 else '◦  ', tag)
        self.write_inline(text.strip(), tag)
        self.write('\n', tag)

    def paragraph(self, text):
        """Append a paragraph of prose."""
        self.write_inline(' '.join(text.split()), 'para')
        self.write('\n', 'para')

    # -- Formats ------------------------------------------------------------

    def docstring(self, text):
        """Render the hard-wrapped plain text found in lesson docstrings."""
        for block in split_blocks(text):
            self._docstring_block(block)

    def _docstring_block(self, lines):
        if len(lines) == 2 and UNDERLINE_RE.match(lines[1]):
            self.heading(lines[0], level=2)
            return
        prose, code, item = [], [], None

        def flush():
            nonlocal item
            if prose:
                self.paragraph(' '.join(prose))
                prose.clear()
            if code:
                self.code_block('\n'.join(code))
                code.clear()
            if item:
                self.bullet(item[1], item[0])
                item = None

        for line in lines:
            stripped = line.strip()
            bullet = BULLET_RE.match(line)
            if stripped.startswith(('>>>', '...')) and not item:
                if not code:
                    flush()
                code.append(stripped)
            elif bullet:
                flush()
                item = [1 if len(bullet.group(1)) >= 2 else 0, bullet.group(2)]
            elif item:
                item[1] += ' ' + stripped
            elif line.startswith('    ') and not prose:
                if not code:
                    flush()
                code.append(line[4:])
            else:
                if code:
                    flush()
                prose.append(stripped)
        flush()

    def markdown(self, text, skip_title=''):
        """Render the small subset of Markdown used by the lesson .md files.

        A top heading equal to ``skip_title`` is left out, since the window shows it already.
        """
        lines = text.splitlines()
        index = 0
        prose = []

        def flush():
            if prose:
                self.paragraph(' '.join(prose))
                prose.clear()

        while index < len(lines):
            line = lines[index]
            stripped = line.strip()
            if stripped.startswith('```'):
                flush()
                block = []
                index += 1
                while index < len(lines) and not lines[index].strip().startswith('```'):
                    block.append(lines[index])
                    index += 1
                self.code_block('\n'.join(block))
            elif stripped.startswith('#'):
                flush()
                level = len(stripped) - len(stripped.lstrip('#'))
                title = stripped.lstrip('#').strip()
                if not (level == 1 and title == skip_title):
                    self.heading(title, level=level)
            elif BULLET_RE.match(line):
                flush()
                match = BULLET_RE.match(line)
                self.bullet(match.group(2), 1 if len(match.group(1)) >= 2 else 0)
            elif not stripped:
                flush()
            else:
                prose.append(stripped)
            index += 1
        flush()


def split_blocks(text):
    """Split text into blocks of lines separated by blank lines."""
    blocks, current = [], []
    for line in text.splitlines():
        if line.strip():
            current.append(line.rstrip())
        elif current:
            blocks.append(current)
            current = []
    if current:
        blocks.append(current)
    return blocks


def open_url(url):
    """Open a link in the learner's browser, ignoring failures."""
    try:
        webbrowser.open(url)
    except webbrowser.Error:
        pass
