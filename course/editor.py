"""A small Python code editor: line numbers, highlighting and friendly indentation."""

import keyword
import re
import tkinter as tk
from tkinter import ttk

INDENT = '    '
BUILTINS = (
    'abs all any bool bytes callable chr dict dir divmod enumerate filter float format '
    'frozenset getattr hasattr hash help hex id input int isinstance issubclass iter len '
    'list map max min next object oct open ord pow print range repr reversed round set '
    'setattr slice sorted str sum super tuple type vars zip'
).split()
TOKEN_RE = re.compile(
    r'(?P<comment>#[^\n]*)'
    r'|(?P<string>(?<!\w)(?i:[rbuf]{0,2})(?:"""[\s\S]*?(?:"""|\Z)|\'\'\'[\s\S]*?(?:\'\'\'|\Z)'
    r'|"(?:\\.|[^"\\\n])*"?|\'(?:\\.|[^\'\\\n])*\'?))'
    r'|(?P<keyword>\b(?:' + '|'.join(keyword.kwlist) + r')\b)'
    r'|(?P<builtin>\b(?:' + '|'.join(BUILTINS) + r')\b(?=\s*\())'
    r'|(?P<number>\b\d[\d_]*(?:\.\d*)?(?:[eE][+-]?\d+)?j?\b)'
)


class CodeEditor(ttk.Frame):
    """A Text widget for Python with a line-number gutter and a scrollbar."""

    def __init__(self, master, fonts, colors, on_run=None):
        super().__init__(master)
        self.colors = colors
        self.on_run = on_run
        self._highlight_job = None

        self.gutter = tk.Text(
            self, width=4, padx=6, pady=8, takefocus=0, borderwidth=0, highlightthickness=0,
            font=fonts['mono'], background=colors['gutter'], foreground=colors['muted'],
            state='disabled', cursor='arrow')
        self.text = tk.Text(
            self, wrap='none', undo=True, maxundo=-1, autoseparators=True, padx=8, pady=8,
            borderwidth=0, highlightthickness=0, font=fonts['mono'],
            background=colors['editor_bg'], foreground=colors['text'],
            insertbackground=colors['text'], selectbackground=colors['select'],
            tabs=(fonts['mono'].measure(INDENT),))
        self.yscroll = ttk.Scrollbar(self, orient='vertical', command=self._scroll_both)
        self.xscroll = ttk.Scrollbar(self, orient='horizontal', command=self.text.xview)
        self.text.configure(yscrollcommand=self._on_text_scroll,
                            xscrollcommand=self.xscroll.set)

        self.gutter.grid(row=0, column=0, sticky='ns')
        self.text.grid(row=0, column=1, sticky='nsew')
        self.yscroll.grid(row=0, column=2, sticky='ns')
        self.xscroll.grid(row=1, column=1, sticky='ew')
        self.rowconfigure(0, weight=1)
        self.columnconfigure(1, weight=1)

        for name, color in (('comment', 'syn_comment'), ('string', 'syn_string'),
                            ('keyword', 'syn_keyword'), ('builtin', 'syn_builtin'),
                            ('number', 'syn_number')):
            self.text.tag_configure(name, foreground=colors[color])
        self.text.tag_configure('keyword', font=fonts['mono_bold'])
        self.text.tag_configure('error_line', background=colors['error_bg'])
        self.text.tag_raise('sel')

        self.text.bind('<<Modified>>', self._on_modified)
        self.text.bind('<Tab>', self._indent)
        self.text.bind('<Shift-Tab>', self._dedent)
        try:
            self.text.bind('<ISO_Left_Tab>', self._dedent)  # Shift+Tab on Linux.
        except tk.TclError:
            pass
        self.text.bind('<Return>', self._newline)
        self.text.bind('<BackSpace>', self._backspace)
        for sequence in ('<Control-Return>', '<Command-Return>', '<F5>'):
            try:
                self.text.bind(sequence, self._run)
            except tk.TclError:
                pass
        self.gutter.bind('<MouseWheel>', lambda event: self.text.event_generate(
            '<MouseWheel>', delta=event.delta))

    # -- Public API -----------------------------------------------------------

    def get_code(self):
        """Return the code in the editor."""
        return self.text.get('1.0', 'end-1c')

    def set_code(self, code, editable=True):
        """Replace the editor's contents and reset its undo history."""
        self.text.configure(state='normal')
        self.text.delete('1.0', 'end')
        self.text.insert('1.0', code)
        self.text.edit_reset()
        self.text.edit_modified(False)
        self.text.mark_set('insert', '1.0')
        self.text.see('1.0')
        self.clear_error()
        self._update_gutter()
        self._highlight()
        if not editable:
            self.text.configure(state='disabled')

    def mark_error(self, line):
        """Highlight a line the runner reported a problem on."""
        self.clear_error()
        if line > 0:
            self.text.tag_add('error_line', f'{line}.0', f'{line}.0 lineend +1c')
            self.text.see(f'{line}.0')

    def clear_error(self):
        """Remove any error highlight."""
        self.text.tag_remove('error_line', '1.0', 'end')

    def focus(self):
        """Put the keyboard cursor in the editor."""
        self.text.focus_set()

    # -- Scrolling and gutter ------------------------------------------------

    def _scroll_both(self, *args):
        self.text.yview(*args)
        self.gutter.yview_moveto(self.text.yview()[0])

    def _on_text_scroll(self, first, last):
        self.yscroll.set(first, last)
        self.gutter.yview_moveto(first)

    def _update_gutter(self):
        count = int(self.text.index('end-1c').split('.')[0])
        numbers = '\n'.join(str(number) for number in range(1, count + 1))
        self.gutter.configure(state='normal', width=max(3, len(str(count))) + 1)
        self.gutter.delete('1.0', 'end')
        self.gutter.insert('1.0', numbers, 'right')
        self.gutter.tag_configure('right', justify='right')
        self.gutter.configure(state='disabled')
        self.gutter.yview_moveto(self.text.yview()[0])

    def _on_modified(self, _event=None):
        if not self.text.edit_modified():
            return
        self.text.edit_modified(False)
        self.clear_error()
        self._update_gutter()
        if self._highlight_job:
            self.after_cancel(self._highlight_job)
        self._highlight_job = self.after(150, self._highlight)

    # -- Highlighting ------------------------------------------------------------

    def _highlight(self):
        self._highlight_job = None
        code = self.get_code()
        for tag in ('comment', 'string', 'keyword', 'builtin', 'number'):
            self.text.tag_remove(tag, '1.0', 'end')
        line, column, position = 1, 0, 0
        for match in TOKEN_RE.finditer(code):
            # Convert character offsets into Tk "line.column" indexes incrementally.
            line, column = advance(code, position, match.start(), line, column)
            start = f'{line}.{column}'
            line, column = advance(code, match.start(), match.end(), line, column)
            position = match.end()
            self.text.tag_add(match.lastgroup, start, f'{line}.{column}')

    # -- Typing helpers ------------------------------------------------------------

    def _selected_lines(self):
        try:
            first = int(self.text.index('sel.first').split('.')[0])
            last_index = self.text.index('sel.last')
        except tk.TclError:
            return None
        last_line, last_col = (int(part) for part in last_index.split('.'))
        if last_col == 0 and last_line > first:
            last_line -= 1
        return first, last_line

    def _indent(self, _event=None):
        lines = self._selected_lines()
        self.text.edit_separator()
        if lines and lines[0] != lines[1]:
            for number in range(lines[0], lines[1] + 1):
                self.text.insert(f'{number}.0', INDENT)
        else:
            column = int(self.text.index('insert').split('.')[1])
            self.text.insert('insert', ' ' * (len(INDENT) - column % len(INDENT)))
        self.text.edit_separator()
        return 'break'

    def _dedent(self, _event=None):
        lines = self._selected_lines()
        if not lines:
            current = int(self.text.index('insert').split('.')[0])
            lines = (current, current)
        self.text.edit_separator()
        for number in range(lines[0], lines[1] + 1):
            text = self.text.get(f'{number}.0', f'{number}.{len(INDENT)}')
            spaces = len(text) - len(text.lstrip(' '))
            if spaces:
                self.text.delete(f'{number}.0', f'{number}.{spaces}')
        self.text.edit_separator()
        return 'break'

    def _newline(self, _event=None):
        line = self.text.get('insert linestart', 'insert')
        indent = line[:len(line) - len(line.lstrip(' '))]
        if line.rstrip().endswith(':'):
            indent += INDENT
        self.text.edit_separator()
        try:
            self.text.delete('sel.first', 'sel.last')
        except tk.TclError:
            pass
        self.text.insert('insert', '\n' + indent)
        self.text.see('insert')
        self.text.edit_separator()
        return 'break'

    def _backspace(self, _event=None):
        if self.text.tag_ranges('sel'):
            return None
        before = self.text.get('insert linestart', 'insert')
        if before and before.strip(' ') == '' and len(before) % len(INDENT) == 0:
            self.text.delete(f'insert-{len(INDENT)}c', 'insert')
            return 'break'
        return None

    def _run(self, _event=None):
        if self.on_run:
            self.on_run()
        return 'break'


def advance(text, start, end, line, column):
    """Move a (line, column) position from offset ``start`` to ``end`` in ``text``."""
    newlines = text.count('\n', start, end)
    if newlines:
        return line + newlines, end - text.rfind('\n', start, end) - 1
    return line, column + (end - start)
