import os
import pytest
import shutil
import subprocess

from .repo import Repo
from ..site import HAVE_GIT

GIT_ENV = {
    'GIT_AUTHOR_DATE': '1320966000 +0200',
    'GIT_AUTHOR_NAME': 'tomjon',
    'GIT_AUTHOR_EMAIL': 'tom@jon.com',
    'GIT_COMMITTER_DATE': '1320966000 +0200',
    'GIT_COMMITTER_NAME': 'tomjon',
    'GIT_COMMITTER_EMAIL': 'tom@jon.com'
}


class Git(Repo):

    def __init__(self, directory, subdir):
        if not HAVE_GIT:
            pytest.skip("git is not available")

        self.submodules = {}

        super(Git, self).__init__(directory, subdir)

    def _run_git(self, *args, **kwargs):
        argv = ['git']
        argv.extend(args)
        if 'env' not in kwargs:
            kwargs['env'] = dict(GIT_ENV, PWD=self.repo)
        kwargs.setdefault('cwd', self.repo)
        kwargs.setdefault('check', True)
        return subprocess.run(argv, **kwargs)

    def create(self, directory):
        self.copy_directory(directory, self.repo)
        self._run_git('init', '.')
        self._run_git('add', '.')
        self._run_git('commit', '-m', 'Initial commit')
        return self.latest_commit()

    def add_tag(self, tag):
        self._run_git('tag', tag)

    def add_annotated_tag(self, tag, message):
        self._run_git('tag', '-a', tag, '-m', message)

    def add_commit(self):
        self._run_git('commit', '--allow-empty', '-m', 'Additional commit')
        return self.latest_commit()

    def add_file(self, filename):
        shutil.copy(filename, self.repo)
        self._run_git('add', os.path.basename(filename))
        self._run_git('commit', '-m', 'Added {}'.format(os.path.basename(filename)))
        return self.latest_commit()

    def modify_file(self, new_file, path):
        shutil.copy(new_file, os.path.join(self.repo, path))
        subprocess.call([
            'git', 'commit', path, '-m', 'Modified {}'.format(os.path.basename(path))
        ], env=GIT_ENV, cwd=self.repo)
        return self.latest_commit()

    def add_submodule(self, subdir, url=None, checkout=None):
        submodule = {}
        if checkout is not None:
            submodule['checkout'] = checkout
        if url is not None:
            submodule['url'] = url
        self.submodules[subdir] = submodule
        self._run_git('submodule', 'add', url, subdir)
        self._run_git('commit', '-m', 'Added the submodule')
        return self.latest_commit()

    def source_config(self, ref=None, checkout_submodules=None):
        config = {
            'kind': 'git',
            'url': 'file://' + self.repo,
            'track': 'master'
        }
        if ref is not None:
            config['ref'] = ref
        if checkout_submodules is not None:
            config['checkout-submodules'] = checkout_submodules

        if self.submodules:
            config['submodules'] = dict(self.submodules)

        return config

    def latest_commit(self):
        output = self._run_git('rev-parse', 'master', stdout=subprocess.PIPE).stdout
        return output.decode('UTF-8').strip()

    def branch(self, branch_name):
        self._run_git('checkout', '-b', branch_name)

    def checkout(self, commit):
        self._run_git('checkout', commit)

    def merge(self, commit):
        self._run_git('merge', '-m', 'Merge', commit)
        return self.latest_commit()

    def rev_parse(self, rev):
        output = self._run_git('rev-parse', rev, stdout=subprocess.PIPE).stdout
        return output.decode('UTF-8').strip()
