"""Tests for saving learner progress."""

from course.progress import Progress


def test_progress_round_trip(tmp_path):
    path = tmp_path / 'progress.json'
    progress = Progress(path)
    progress.completed.add('a::b')
    progress.set_draft('a::b', 'edited', 'original')
    progress.set_draft('a::c', 'same', 'same')
    progress.last = 'a::b'
    assert progress.save()

    loaded = Progress(path)
    assert loaded.completed == {'a::b'}
    assert loaded.drafts == {'a::b': 'edited'}
    assert loaded.last == 'a::b'


def test_damaged_progress_file_starts_fresh(tmp_path):
    path = tmp_path / 'progress.json'
    path.write_text('{not json', encoding='utf-8')
    progress = Progress(path)
    assert progress.completed == set()
    path.write_text('["a list"]', encoding='utf-8')
    assert Progress(path).drafts == {}
