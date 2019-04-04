# Pylint doesn't play well with fixtures and dependency injection from pytest
# pylint: disable=redefined-outer-name

import os
import textwrap
import pytest
from buildstream import _yaml
from buildstream._exceptions import ErrorDomain, LoadErrorReason
from buildstream.plugintestutils import cli  # pylint: disable=unused-import

from tests.testutils import generate_junction, create_repo


# Project directory
DATA_DIR = os.path.join(
    os.path.dirname(os.path.realpath(__file__)),
    'include'
)


@pytest.mark.datafiles(DATA_DIR)
def test_include_project_file(cli, datafiles):
    project = os.path.join(str(datafiles), 'file')
    result = cli.run(project=project, args=[
        'show',
        '--deps', 'none',
        '--format', '%{vars}',
        'element.bst'])
    result.assert_success()
    loaded = _yaml.load_data(result.output)
    assert _yaml.node_get(loaded, bool, 'included')


def test_include_missing_file(cli, tmpdir):
    tmpdir.join('project.conf').write('{"name": "test"}')
    element = tmpdir.join('include_missing_file.bst')

    # Normally we would use dicts and _yaml.dump to write such things, but here
    # we want to be sure of a stable line and column number.
    element.write(textwrap.dedent("""
        kind: manual

        "(@)":
          - nosuch.yaml
    """).strip())

    result = cli.run(project=str(tmpdir), args=['show', str(element.basename)])
    result.assert_main_error(ErrorDomain.LOAD, LoadErrorReason.MISSING_FILE)
    # Make sure the root cause provenance is in the output.
    assert 'line 4 column 2' in result.stderr


def test_include_dir(cli, tmpdir):
    tmpdir.join('project.conf').write('{"name": "test"}')
    tmpdir.mkdir('subdir')
    element = tmpdir.join('include_dir.bst')

    # Normally we would use dicts and _yaml.dump to write such things, but here
    # we want to be sure of a stable line and column number.
    element.write(textwrap.dedent("""
        kind: manual

        "(@)":
          - subdir/
    """).strip())

    result = cli.run(project=str(tmpdir), args=['show', str(element.basename)])
    result.assert_main_error(
        ErrorDomain.LOAD, LoadErrorReason.LOADING_DIRECTORY)
    # Make sure the root cause provenance is in the output.
    assert 'line 4 column 2' in result.stderr


@pytest.mark.datafiles(DATA_DIR)
def test_include_junction_file(cli, tmpdir, datafiles):
    project = os.path.join(str(datafiles), 'junction')

    generate_junction(tmpdir,
                      os.path.join(project, 'subproject'),
                      os.path.join(project, 'junction.bst'),
                      store_ref=True)

    result = cli.run(project=project, args=[
        'show',
        '--deps', 'none',
        '--format', '%{vars}',
        'element.bst'])
    result.assert_success()
    loaded = _yaml.load_data(result.output)
    assert _yaml.node_get(loaded, bool, 'included')


@pytest.mark.datafiles(DATA_DIR)
def test_include_junction_options(cli, datafiles):
    project = os.path.join(str(datafiles), 'options')

    result = cli.run(project=project, args=[
        '-o', 'build_arch', 'x86_64',
        'show',
        '--deps', 'none',
        '--format', '%{vars}',
        'element.bst'])
    result.assert_success()
    loaded = _yaml.load_data(result.output)
    assert _yaml.node_get(loaded, str, 'build_arch') == 'x86_64'


@pytest.mark.datafiles(DATA_DIR)
def test_junction_element_partial_project_project(cli, tmpdir, datafiles):
    """
    Junction elements never depend on fully include processed project.
    """

    project = os.path.join(str(datafiles), 'junction')

    subproject_path = os.path.join(project, 'subproject')
    junction_path = os.path.join(project, 'junction.bst')

    repo = create_repo('git', str(tmpdir))

    ref = repo.create(subproject_path)

    element = {
        'kind': 'junction',
        'sources': [
            repo.source_config(ref=ref)
        ]
    }
    _yaml.dump(element, junction_path)

    result = cli.run(project=project, args=[
        'show',
        '--deps', 'none',
        '--format', '%{vars}',
        'junction.bst'])
    result.assert_success()
    loaded = _yaml.load_data(result.output)
    assert _yaml.node_get(loaded, str, 'included', default_value=None) is None


@pytest.mark.datafiles(DATA_DIR)
def test_junction_element_not_partial_project_file(cli, tmpdir, datafiles):
    """
    Junction elements never depend on fully include processed project.
    """

    project = os.path.join(str(datafiles), 'file_with_subproject')

    subproject_path = os.path.join(project, 'subproject')
    junction_path = os.path.join(project, 'junction.bst')

    repo = create_repo('git', str(tmpdir))

    ref = repo.create(subproject_path)

    element = {
        'kind': 'junction',
        'sources': [
            repo.source_config(ref=ref)
        ]
    }
    _yaml.dump(element, junction_path)

    result = cli.run(project=project, args=[
        'show',
        '--deps', 'none',
        '--format', '%{vars}',
        'junction.bst'])
    result.assert_success()
    loaded = _yaml.load_data(result.output)
    assert _yaml.node_get(loaded, str, 'included', default_value=None) is not None


@pytest.mark.datafiles(DATA_DIR)
def test_include_element_overrides(cli, datafiles):
    project = os.path.join(str(datafiles), 'overrides')

    result = cli.run(project=project, args=[
        'show',
        '--deps', 'none',
        '--format', '%{vars}',
        'element.bst'])
    result.assert_success()
    loaded = _yaml.load_data(result.output)
    assert _yaml.node_get(loaded, str, 'manual_main_override', default_value=None) is not None
    assert _yaml.node_get(loaded, str, 'manual_included_override', default_value=None) is not None


@pytest.mark.datafiles(DATA_DIR)
def test_include_element_overrides_composition(cli, datafiles):
    project = os.path.join(str(datafiles), 'overrides')

    result = cli.run(project=project, args=[
        'show',
        '--deps', 'none',
        '--format', '%{config}',
        'element.bst'])
    result.assert_success()
    loaded = _yaml.load_data(result.output)
    assert _yaml.node_get(loaded, list, 'build-commands') == ['first', 'second']


@pytest.mark.datafiles(DATA_DIR)
def test_list_overide_does_not_fail_upon_first_composition(cli, datafiles):
    project = os.path.join(str(datafiles), 'eventual_overrides')

    result = cli.run(project=project, args=[
        'show',
        '--deps', 'none',
        '--format', '%{public}',
        'element.bst'])
    result.assert_success()
    loaded = _yaml.load_data(result.output)

    # Assert that the explicitly overwritten public data is present
    bst = _yaml.node_get(loaded, dict, 'bst')
    assert 'foo-commands' in bst
    assert _yaml.node_get(bst, list, 'foo-commands') == ['need', 'this']


@pytest.mark.datafiles(DATA_DIR)
def test_include_element_overrides_sub_include(cli, datafiles):
    project = os.path.join(str(datafiles), 'sub-include')

    result = cli.run(project=project, args=[
        'show',
        '--deps', 'none',
        '--format', '%{vars}',
        'element.bst'])
    result.assert_success()
    loaded = _yaml.load_data(result.output)
    assert _yaml.node_get(loaded, str, 'included', default_value=None) is not None


@pytest.mark.datafiles(DATA_DIR)
def test_junction_do_not_use_included_overrides(cli, tmpdir, datafiles):
    project = os.path.join(str(datafiles), 'overrides-junction')

    generate_junction(tmpdir,
                      os.path.join(project, 'subproject'),
                      os.path.join(project, 'junction.bst'),
                      store_ref=True)

    result = cli.run(project=project, args=[
        'show',
        '--deps', 'none',
        '--format', '%{vars}',
        'junction.bst'])
    result.assert_success()
    loaded = _yaml.load_data(result.output)
    assert _yaml.node_get(loaded, str, 'main_override', default_value=None) is not None
    assert _yaml.node_get(loaded, str, 'included_override', default_value=None) is None


@pytest.mark.datafiles(DATA_DIR)
def test_conditional_in_fragment(cli, datafiles):
    project = os.path.join(str(datafiles), 'conditional')

    result = cli.run(project=project, args=[
        '-o', 'build_arch', 'x86_64',
        'show',
        '--deps', 'none',
        '--format', '%{vars}',
        'element.bst'])
    result.assert_success()
    loaded = _yaml.load_data(result.output)
    assert _yaml.node_get(loaded, str, 'size') == '8'


@pytest.mark.datafiles(DATA_DIR)
def test_inner(cli, datafiles):
    project = os.path.join(str(datafiles), 'inner')
    result = cli.run(project=project, args=[
        '-o', 'build_arch', 'x86_64',
        'show',
        '--deps', 'none',
        '--format', '%{vars}',
        'element.bst'])
    result.assert_success()
    loaded = _yaml.load_data(result.output)
    assert _yaml.node_get(loaded, str, 'build_arch') == 'x86_64'


@pytest.mark.datafiles(DATA_DIR)
def test_recursive_include(cli, datafiles):
    project = os.path.join(str(datafiles), 'recursive')

    result = cli.run(project=project, args=[
        'show',
        '--deps', 'none',
        '--format', '%{vars}',
        'element.bst'])
    result.assert_main_error(ErrorDomain.LOAD, LoadErrorReason.RECURSIVE_INCLUDE)
    assert 'line 2 column 2' in result.stderr


@pytest.mark.datafiles(DATA_DIR)
def test_local_to_junction(cli, tmpdir, datafiles):
    project = os.path.join(str(datafiles), 'local_to_junction')

    generate_junction(tmpdir,
                      os.path.join(project, 'subproject'),
                      os.path.join(project, 'junction.bst'),
                      store_ref=True)

    result = cli.run(project=project, args=[
        'show',
        '--deps', 'none',
        '--format', '%{vars}',
        'element.bst'])
    result.assert_success()
    loaded = _yaml.load_data(result.output)
    assert _yaml.node_get(loaded, bool, 'included')
