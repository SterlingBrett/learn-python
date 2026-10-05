"""Remember which sections a learner finished, their edited code and where they left off."""

import json
import os
from pathlib import Path


def default_path():
    """Where progress is saved: a small JSON file in the learner's home folder."""
    override = os.environ.get('LEARN_PYTHON_PROGRESS')
    return Path(override) if override else Path.home() / '.learn_python_course.json'


class Progress:
    """Completed sections, saved drafts and the last open section, kept on disk."""

    def __init__(self, path=None):
        self.path = Path(path) if path else default_path()
        self.completed = set()
        self.drafts = {}
        self.last = ''
        self.load()

    def load(self):
        """Read saved progress. A missing or damaged file just means a fresh start."""
        try:
            data = json.loads(self.path.read_text(encoding='utf-8'))
        except (OSError, ValueError):
            return
        if not isinstance(data, dict):
            return
        completed = data.get('completed', [])
        drafts = data.get('drafts', {})
        self.completed = {item for item in completed if isinstance(item, str)} \
            if isinstance(completed, list) else set()
        self.drafts = {key: value for key, value in drafts.items()
                       if isinstance(key, str) and isinstance(value, str)} \
            if isinstance(drafts, dict) else {}
        self.last = data.get('last', '') if isinstance(data.get('last'), str) else ''

    def save(self):
        """Write progress to disk. Returns False if it could not be saved."""
        data = {'completed': sorted(self.completed), 'drafts': self.drafts, 'last': self.last}
        try:
            temporary = self.path.with_name(self.path.name + '.tmp')
            temporary.write_text(json.dumps(data, indent=1), encoding='utf-8')
            temporary.replace(self.path)
        except OSError:
            return False
        return True

    def set_draft(self, section_id, code, original):
        """Remember edited code, or forget it when it matches the lesson again."""
        if code == original:
            self.drafts.pop(section_id, None)
        else:
            self.drafts[section_id] = code

    def reset(self):
        """Forget everything."""
        self.completed.clear()
        self.drafts.clear()
        self.last = ''
