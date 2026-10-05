"""The Learn Python desktop app: lessons on the left, reading and coding on the right."""

import queue
import threading
import tkinter as tk
import tkinter.font as tkfont
from pathlib import Path
from tkinter import messagebox, ttk

from .catalog import count_checks, has_setup_code, load_catalog
from .editor import CodeEditor
from .progress import Progress
from .reading import ReadingPane
from .runner import RunResult, run_code

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRATCH_CODE = (
    '# This page is for reading, but you can try Python here too.\n'
    '# Change the code and press Run.\n'
    'print("Hello, World!")\n'
)

COLORS = {
    'window': '#f3f4f6',
    'paper': '#ffffff',
    'text': '#1f2328',
    'heading': '#1a3d6d',
    'muted': '#6a737d',
    'link': '#0b62c4',
    'code_bg': '#f2f4f7',
    'editor_bg': '#fcfcfd',
    'gutter': '#eef0f3',
    'select': '#cfe3ff',
    'error_bg': '#ffe1e1',
    'syn_comment': '#7c828c',
    'syn_string': '#2e7d32',
    'syn_keyword': '#7a3e9d',
    'syn_builtin': '#0b62c4',
    'syn_number': '#b35900',
    'pass_bg': '#e3f4e8', 'pass_fg': '#1e6b34',
    'fail_bg': '#fde8e7', 'fail_fg': '#b3261e',
    'error_bg_banner': '#fff4e0', 'error_fg': '#8a4b00',
    'idle_bg': '#eef0f3', 'idle_fg': '#3d434b',
    'done': '#1e6b34',
}
BASE_SIZE = 12


class Stop:
    """One place in the course: a section of a lesson, or a reading-only page."""

    def __init__(self, category, lesson, section=None):
        self.category = category
        self.lesson = lesson
        self.section = section
        self.id = section.id if section else lesson.id

    @property
    def original_code(self):
        """The lesson's own code for this stop."""
        return self.section.code if self.section else SCRATCH_CODE


class CourseApp:
    """Builds the window and wires the course together."""

    def __init__(self, root, categories, progress):
        self.root = root
        self.categories = categories
        self.progress = progress
        self.stops = [Stop(category, lesson, section)
                      for category in categories for lesson in category.lessons
                      for section in (lesson.sections or [None])]
        self.index_of = {stop.id: index for index, stop in enumerate(self.stops)}
        self.current = None
        self.results = queue.Queue()
        self.running = False
        self._syncing_tree = False
        self.zoom = 0

        self.fonts = self._make_fonts()
        self._style()
        self._build()
        self._fill_tree()

        start = self.index_of.get(progress.last, 0)
        self.go_to(start)
        root.protocol('WM_DELETE_WINDOW', self.quit)

    # -- Setup ---------------------------------------------------------------

    def _make_fonts(self):
        family = tkfont.nametofont('TkDefaultFont').actual('family')
        mono = tkfont.nametofont('TkFixedFont').actual('family')
        specs = {
            'body': (family, 0, 'normal'),
            'bold': (family, 0, 'bold'),
            'small': (family, -1, 'normal'),
            'title': (family, 8, 'bold'),
            'h1': (family, 4, 'bold'),
            'h2': (family, 1, 'bold'),
            'mono': (mono, 0, 'normal'),
            'mono_bold': (mono, 0, 'bold'),
        }
        self._font_offsets = {name: offset for name, (_, offset, _) in specs.items()}
        return {name: tkfont.Font(self.root, family=fam, size=BASE_SIZE + offset, weight=weight)
                for name, (fam, offset, weight) in specs.items()}

    def _style(self):
        self.root.configure(background=COLORS['window'])
        style = ttk.Style(self.root)
        if 'clam' in style.theme_names():
            style.theme_use('clam')
        style.configure('.', font=self.fonts['body'], background=COLORS['window'])
        style.configure('Treeview', font=self.fonts['body'], background=COLORS['paper'],
                        fieldbackground=COLORS['paper'], borderwidth=0,
                        rowheight=self.fonts['body'].metrics('linespace') + 8)
        style.map('Treeview', background=[('selected', COLORS['select'])],
                  foreground=[('selected', COLORS['text'])])
        style.configure('Sidebar.TFrame', background=COLORS['window'])
        style.configure('Header.TLabel', font=self.fonts['h1'], foreground=COLORS['heading'])
        style.configure('Crumb.TLabel', font=self.fonts['small'], foreground=COLORS['muted'])
        style.configure('Muted.TLabel', font=self.fonts['small'], foreground=COLORS['muted'])
        style.configure('Run.TButton', font=self.fonts['bold'], padding=(14, 4))
        style.configure('TButton', padding=(10, 4))
        style.configure('done.Horizontal.TProgressbar', background=COLORS['done'])

    def _build(self):
        root = self.root
        root.title('Learn Python')
        root.geometry('1280x820')
        root.minsize(900, 600)
        self._build_menu()

        outer = self.outer = ttk.Panedwindow(root, orient='horizontal')
        outer.pack(fill='both', expand=True, padx=8, pady=8)

        # Sidebar: the list of topics and overall progress.
        sidebar = ttk.Frame(outer, style='Sidebar.TFrame', padding=(0, 0, 6, 0))
        ttk.Label(sidebar, text='Topics', style='Header.TLabel').pack(anchor='w', pady=(0, 6))
        tree_frame = ttk.Frame(sidebar)
        tree_frame.pack(fill='both', expand=True)
        self.tree = ttk.Treeview(tree_frame, show='tree', selectmode='browse')
        self.tree.column('#0', width=250, stretch=True)
        tree_scroll = ttk.Scrollbar(tree_frame, orient='vertical', command=self.tree.yview)
        self.tree.configure(yscrollcommand=tree_scroll.set)
        self.tree.pack(side='left', fill='both', expand=True)
        tree_scroll.pack(side='right', fill='y')
        self.tree.tag_configure('done', foreground=COLORS['done'])
        self.tree.tag_configure('category', font=self.fonts['bold'])
        self.tree.bind('<<TreeviewSelect>>', self._on_tree_select)
        self.progress_label = ttk.Label(sidebar, style='Muted.TLabel')
        self.progress_label.pack(anchor='w', pady=(8, 2))
        self.progress_bar = ttk.Progressbar(sidebar, style='done.Horizontal.TProgressbar',
                                            maximum=max(1, len(self.stops)))
        self.progress_bar.pack(fill='x')
        outer.add(sidebar, weight=1)

        # Main area: header, reading pane, then editor and results side by side.
        main_area = ttk.Frame(outer, padding=(6, 0, 0, 0))
        outer.add(main_area, weight=4)

        header = ttk.Frame(main_area)
        header.pack(fill='x', pady=(0, 6))
        titles = ttk.Frame(header)
        titles.pack(side='left', fill='x', expand=True)
        self.crumb = ttk.Label(titles, style='Crumb.TLabel')
        self.crumb.pack(anchor='w')
        self.heading = ttk.Label(titles, style='Header.TLabel')
        self.heading.pack(anchor='w')
        self.next_button = ttk.Button(header, text='Next  ▶', command=self.next)
        self.next_button.pack(side='right')
        self.prev_button = ttk.Button(header, text='◀  Previous', command=self.previous)
        self.prev_button.pack(side='right', padx=(0, 6))

        vertical = self.vertical = ttk.Panedwindow(main_area, orient='vertical')
        vertical.pack(fill='both', expand=True)

        reading_frame = ttk.Frame(vertical)
        self.reading = ReadingPane(reading_frame, self.fonts, COLORS)
        reading_scroll = ttk.Scrollbar(reading_frame, orient='vertical',
                                       command=self.reading.yview)
        self.reading.configure(yscrollcommand=reading_scroll.set)
        self.reading.pack(side='left', fill='both', expand=True)
        reading_scroll.pack(side='right', fill='y')
        vertical.add(reading_frame, weight=2)

        work = self.work = ttk.Panedwindow(vertical, orient='horizontal')
        vertical.add(work, weight=3)

        editor_frame = ttk.Frame(work, padding=(0, 8, 6, 0))
        toolbar = ttk.Frame(editor_frame)
        toolbar.pack(fill='x', pady=(0, 6))
        self.run_button = ttk.Button(toolbar, text='▶  Run', style='Run.TButton',
                                     command=self.run)
        self.run_button.pack(side='left')
        ttk.Button(toolbar, text='Reset code', command=self.reset_code).pack(
            side='left', padx=(6, 0))
        ttk.Label(toolbar, text='Ctrl+Enter or F5 runs your code', style='Muted.TLabel').pack(
            side='right')
        self.editor = CodeEditor(editor_frame, self.fonts, COLORS, on_run=self.run)
        self.editor.pack(fill='both', expand=True)
        work.add(editor_frame, weight=3)

        result_frame = ttk.Frame(work, padding=(6, 8, 0, 0))
        self.banner = tk.Label(result_frame, anchor='w', justify='left', padx=10, pady=8,
                               font=self.fonts['bold'], wraplength=360)
        self.banner.pack(fill='x')
        result_frame.bind('<Configure>', lambda event: self.banner.configure(
            wraplength=max(200, event.width - 30)))
        input_frame = ttk.Frame(result_frame)
        input_frame.pack(side='bottom', fill='x')
        ttk.Label(input_frame, text='Program input (one line for each input() call)',
                  style='Muted.TLabel').pack(anchor='w', pady=(8, 2))
        self.stdin = tk.Text(input_frame, height=2, padx=8, pady=4, borderwidth=0,
                             highlightthickness=1, highlightbackground=COLORS['gutter'],
                             font=self.fonts['mono'], background=COLORS['paper'],
                             foreground=COLORS['text'], insertbackground=COLORS['text'])
        self.stdin.pack(fill='x')
        ttk.Label(result_frame, text='Output', style='Muted.TLabel').pack(
            anchor='w', pady=(8, 2))
        output_frame = ttk.Frame(result_frame)
        output_frame.pack(fill='both', expand=True)
        self.output = tk.Text(output_frame, wrap='word', height=4, padx=8, pady=6,
                              borderwidth=0, highlightthickness=0, font=self.fonts['mono'],
                              background=COLORS['paper'], foreground=COLORS['text'],
                              state='disabled')
        output_scroll = ttk.Scrollbar(output_frame, orient='vertical',
                                      command=self.output.yview)
        self.output.configure(yscrollcommand=output_scroll.set)
        self.output.pack(side='left', fill='both', expand=True)
        output_scroll.pack(side='right', fill='y')
        self.output.tag_configure('muted', foreground=COLORS['muted'])
        self.output.tag_configure('problem', foreground=COLORS['fail_fg'])
        work.add(result_frame, weight=2)

        for sequence, handler in (('<Alt-Right>', self.next), ('<Alt-Left>', self.previous),
                                  ('<Control-plus>', self.zoom_in),
                                  ('<Control-equal>', self.zoom_in),
                                  ('<Control-minus>', self.zoom_out),
                                  ('<Control-0>', self.zoom_reset)):
            root.bind_all(sequence, lambda _event, call=handler: call())
        root.after_idle(self._initial_layout)

    def _initial_layout(self, attempts=40):
        """Give the sidebar, reading pane and editor sensible starting sizes."""
        self.root.update_idletasks()
        width = self.outer.winfo_width()
        height = self.vertical.winfo_height()
        if (width < 600 or height < 300) and attempts:
            # The window is not on screen yet; try again shortly.
            self.root.after(50, self._initial_layout, attempts - 1)
            return
        self.outer.sashpos(0, min(300, max(220, width // 5)))
        self.root.update_idletasks()
        self.vertical.sashpos(0, int(self.vertical.winfo_height() * 0.42))
        self.work.sashpos(0, int(self.work.winfo_width() * 0.6))

    def _build_menu(self):
        menubar = tk.Menu(self.root)
        course_menu = tk.Menu(menubar, tearoff=False)
        course_menu.add_command(label='Previous section', accelerator='Alt+Left',
                                command=self.previous)
        course_menu.add_command(label='Next section', accelerator='Alt+Right',
                                command=self.next)
        course_menu.add_separator()
        course_menu.add_command(label='Reset all progress…', command=self.reset_progress)
        course_menu.add_separator()
        course_menu.add_command(label='Quit', command=self.quit)
        menubar.add_cascade(label='Course', menu=course_menu)
        view_menu = tk.Menu(menubar, tearoff=False)
        view_menu.add_command(label='Bigger text', accelerator='Ctrl++', command=self.zoom_in)
        view_menu.add_command(label='Smaller text', accelerator='Ctrl+-', command=self.zoom_out)
        view_menu.add_command(label='Normal size', accelerator='Ctrl+0', command=self.zoom_reset)
        menubar.add_cascade(label='View', menu=view_menu)
        help_menu = tk.Menu(menubar, tearoff=False)
        help_menu.add_command(label='How this course works', command=self.show_help)
        menubar.add_cascade(label='Help', menu=help_menu)
        self.root.configure(menu=menubar)

    def _fill_tree(self):
        for c_index, category in enumerate(self.categories):
            category_id = f'category-{c_index}'
            self.tree.insert('', 'end', iid=category_id, text=category.title,
                             open=False, tags=('category',))
            for lesson in category.lessons:
                lesson_id = f'lesson:{lesson.id}'
                self.tree.insert(category_id, 'end', iid=lesson_id, text=lesson.title)
                if len(lesson.sections) > 1:
                    for section in lesson.sections:
                        self.tree.insert(lesson_id, 'end', iid=f'section:{section.id}',
                                         text=section.title)
        self._refresh_marks()

    # -- Navigation -------------------------------------------------------------

    def go_to(self, index):
        """Show the stop at ``index`` in the course."""
        if not 0 <= index < len(self.stops):
            return
        self._save_draft()
        stop = self.current = self.stops[index]
        section = stop.section
        lesson = stop.lesson

        self.crumb.configure(text=stop.category.title)
        self.heading.configure(text=lesson.title)
        self.prev_button.state(['!disabled'] if index > 0 else ['disabled'])
        self.next_button.state(['!disabled'] if index < len(self.stops) - 1 else ['disabled'])

        self._render_reading(stop)
        self.editor.set_code(self.progress.drafts.get(stop.id, stop.original_code))
        self._set_output('')
        self.stdin.delete('1.0', 'end')
        if section is None:
            self._set_banner('idle', 'This page is for reading. Press Next when you are ready.')
            self._mark_complete(stop)
        elif section.checks:
            self._set_banner('idle', 'Read the code, change it if you like, then press Run. '
                             'Every assert is a check that must pass.')
        else:
            self._set_banner('idle', 'Press Run to try this code.')

        self.progress.last = stop.id
        self.progress.save()
        self._select_in_tree(stop)
        self.editor.focus()

    def next(self):
        """Go to the next stop."""
        if self.current:
            self.go_to(self.index_of[self.current.id] + 1)

    def previous(self):
        """Go to the previous stop."""
        if self.current:
            self.go_to(self.index_of[self.current.id] - 1)

    def _on_tree_select(self, _event=None):
        if self._syncing_tree:
            return
        selection = self.tree.selection()
        if not selection:
            return
        item = selection[0]
        target = None
        if item.startswith('section:'):
            target = item[len('section:'):]
        elif item.startswith('lesson:'):
            lesson_id = item[len('lesson:'):]
            target = next((stop.id for stop in self.stops if stop.lesson.id == lesson_id), None)
            self.tree.item(item, open=True)
        elif item.startswith('category-'):
            self.tree.item(item, open=True)
            children = self.tree.get_children(item)
            if children:
                lesson_id = children[0][len('lesson:'):]
                target = next((stop.id for stop in self.stops
                               if stop.lesson.id == lesson_id), None)
        if target and (not self.current or target != self.current.id):
            self.go_to(self.index_of[target])

    def _select_in_tree(self, stop):
        item = f'section:{stop.id}' if self.tree.exists(f'section:{stop.id}') \
            else f'lesson:{stop.lesson.id}'
        parent = self.tree.parent(item)
        while parent:
            self.tree.item(parent, open=True)
            parent = self.tree.parent(parent)
        self._syncing_tree = True
        try:
            self.tree.selection_set(item)
            self.tree.see(item)
        finally:
            self.root.after_idle(self._end_tree_sync)

    def _end_tree_sync(self):
        self._syncing_tree = False

    # -- Reading pane -------------------------------------------------------------

    def _render_reading(self, stop):
        lesson, section = stop.lesson, stop.section
        pane = self.reading
        pane.clear()
        if section is None:
            pane.markdown(lesson.markdown, skip_title=lesson.title)
            pane.finish()
            return

        sections = lesson.sections
        position = sections.index(section)
        if lesson.summary:
            pane.write_inline(lesson.summary, 'subtitle')
            pane.write('\n', 'subtitle')
        if position == 0 and lesson.intro:
            pane.docstring(lesson.intro)
        if len(sections) > 1:
            pane.write(f'Part {position + 1} of {len(sections)}\n', 'note')
        if len(sections) > 1 or section.title != lesson.title:
            pane.heading(section.title, level=1)
        if section.explanation:
            pane.docstring(section.explanation)
        if has_setup_code(section.setup):
            pane.heading('Code that runs before yours', level=2)
            pane.paragraph('This lesson defines a few things at the top of its file. '
                           'They are ready to use in the editor below.')
            pane.code_block(section.setup)
        if not section.explanation and position > 0:
            pane.paragraph('The explanation for this part is in the comments in the code below.')
        if lesson.links:
            pane.heading('Further reading', level=2)
            for url in lesson.links:
                pane.write('•  ', 'bullet')
                pane.write_link(url, url, 'bullet')
                pane.write('\n', 'bullet')
        pane.finish()

    # -- Running code -----------------------------------------------------------------

    def run(self):
        """Run the code in the editor in the background."""
        if self.running or not self.current:
            return
        stop = self.current
        code = self.editor.get_code()
        stdin = self.stdin.get('1.0', 'end-1c')
        section = stop.section
        self.running = True
        self.run_button.state(['disabled'])
        self.editor.clear_error()
        self._set_banner('idle', 'Running…')
        self._set_output('')

        def work():
            try:
                result = run_code(
                    code,
                    setup=section.setup if section else '',
                    wrap=section.wrap if section else False,
                    lesson_dir=stop.lesson.path.parent,
                    stdin=stdin,
                    root=REPO_ROOT,
                )
            except Exception as error:  # pylint: disable=broad-except
                result = RunResult('error', f'The course could not run your code: {error}')
            self.results.put((stop.id, code, result))

        threading.Thread(target=work, daemon=True).start()
        self.root.after(100, self._poll_results)

    def _poll_results(self):
        try:
            stop_id, code, result = self.results.get_nowait()
        except queue.Empty:
            self.root.after(100, self._poll_results)
            return
        self.running = False
        self.run_button.state(['!disabled'])
        if not self.current or stop_id != self.current.id:
            return  # The learner moved on while the code was running.
        self._show_result(code, result)

    def _show_result(self, code, result):
        stop = self.current
        self._set_output(result.output, result.details if not result.passed else '')
        if not result.passed:
            self._set_banner('fail' if result.status == 'failed' else 'error',
                             ('✗  ' if result.status == 'failed' else '⚠  ') + result.message)
            self.editor.mark_error(result.line)
            return

        expected = stop.section.checks if stop.section else 0
        kept = count_checks(code)
        message = '✓  ' + result.message
        if expected and not kept:
            self._set_banner('error', message + '\nYour code has no checks left, so this '
                             'section is not marked as done. Keep at least one assert.')
            return
        if expected and kept < expected:
            message += f' (The lesson had {expected} checks; you kept {kept}.)'
        if self.index_of[stop.id] < len(self.stops) - 1:
            message += '\nPress Next to continue.'
        else:
            message += '\nThat was the last section. Well done!'
        self._set_banner('pass', message)
        self._mark_complete(stop)
        self._save_draft()
        self.progress.save()

    def _set_output(self, output, problem=''):
        self.output.configure(state='normal')
        self.output.delete('1.0', 'end')
        if output:
            self.output.insert('end', output)
        if problem:
            if output and not output.endswith('\n'):
                self.output.insert('end', '\n')
            self.output.insert('end', ('\n' if output else '') + problem, 'problem')
        if not output and not problem:
            self.output.insert('end', 'Anything your code prints will appear here.', 'muted')
        self.output.configure(state='disabled')
        self.output.see('end' if problem else '1.0')

    def _set_banner(self, kind, text):
        background, foreground = {
            'pass': ('pass_bg', 'pass_fg'),
            'fail': ('fail_bg', 'fail_fg'),
            'error': ('error_bg_banner', 'error_fg'),
            'idle': ('idle_bg', 'idle_fg'),
        }[kind]
        self.banner.configure(text=text, background=COLORS[background],
                              foreground=COLORS[foreground])

    # -- Progress ------------------------------------------------------------

    def _mark_complete(self, stop):
        if stop.id not in self.progress.completed:
            self.progress.completed.add(stop.id)
            self.progress.save()
        self._refresh_marks()

    def _refresh_marks(self):
        done = self.progress.completed
        for category_index, category in enumerate(self.categories):
            category_done = True
            for lesson in category.lessons:
                ids = [section.id for section in lesson.sections] or [lesson.id]
                lesson_done = all(item in done for item in ids)
                category_done = category_done and lesson_done
                self._mark_item(f'lesson:{lesson.id}', lesson.title, lesson_done)
                if len(lesson.sections) > 1:
                    for section in lesson.sections:
                        self._mark_item(f'section:{section.id}', section.title,
                                        section.id in done)
            self._mark_item(f'category-{category_index}', category.title, category_done,
                            base_tags=('category',))
        count = sum(stop.id in done for stop in self.stops)
        self.progress_bar.configure(value=count)
        self.progress_label.configure(text=f'{count} of {len(self.stops)} sections done')

    def _mark_item(self, item, title, is_done, base_tags=()):
        if self.tree.exists(item):
            self.tree.item(item, text=('✓  ' if is_done else '') + title,
                           tags=base_tags + (('done',) if is_done else ()))

    def _save_draft(self):
        if self.current:
            self.progress.set_draft(self.current.id, self.editor.get_code(),
                                    self.current.original_code)

    def reset_code(self):
        """Put the lesson's original code back in the editor."""
        if not self.current:
            return
        if self.editor.get_code() == self.current.original_code:
            return
        if messagebox.askyesno('Reset code', "Put back this section's original code?\n\n"
                               'Your changes to this section will be lost.',
                               parent=self.root):
            self.editor.set_code(self.current.original_code)
            self.progress.drafts.pop(self.current.id, None)
            self.progress.save()
            self._set_output('')
            self._set_banner('idle', 'The original code is back. Press Run to try it.')

    def reset_progress(self):
        """Forget all completed sections and edited code."""
        if messagebox.askyesno('Reset all progress',
                               'Forget every finished section and all of your edited code?',
                               parent=self.root):
            self.progress.reset()
            self.progress.save()
            self.current = None
            self._refresh_marks()
            self.go_to(0)

    # -- Misc -------------------------------------------------------------------

    def _apply_zoom(self):
        for name, font in self.fonts.items():
            font.configure(size=max(8, BASE_SIZE + self.zoom + self._font_offsets[name]))
        ttk.Style(self.root).configure(
            'Treeview', rowheight=self.fonts['body'].metrics('linespace') + 8)
        self.editor.text.configure(tabs=(self.fonts['mono'].measure('    '),))

    def zoom_in(self):
        """Make all text bigger."""
        if self.zoom < 12:
            self.zoom += 1
            self._apply_zoom()

    def zoom_out(self):
        """Make all text smaller."""
        if self.zoom > -4:
            self.zoom -= 1
            self._apply_zoom()

    def zoom_reset(self):
        """Go back to the normal text size."""
        self.zoom = 0
        self._apply_zoom()

    def show_help(self):
        """Explain how the course works."""
        messagebox.showinfo('How this course works', (
            'Pick a topic on the left, or use Previous and Next to go through the course '
            'in order.\n\n'
            'Each section explains an idea and gives you code to run. The lines that start '
            'with "assert" are checks: each one says something that must be true. Press Run '
            '(or Ctrl+Enter) to run the code. If every check passes, the section is marked '
            'done.\n\n'
            'Change the code to experiment. If a check fails, the line is highlighted in red. '
            '"Reset code" brings back the original.\n\n'
            'Your progress and edits are saved automatically.'), parent=self.root)

    def quit(self):
        """Save and close the window."""
        self._save_draft()
        self.progress.save()
        self.root.destroy()


def main():
    """Start the app."""
    categories = load_catalog(REPO_ROOT)
    root = tk.Tk()
    if not categories:
        root.withdraw()
        messagebox.showerror('Learn Python', f'No lessons were found in {REPO_ROOT / "src"}.')
        root.destroy()
        return 1
    CourseApp(root, categories, Progress())
    root.mainloop()
    return 0
