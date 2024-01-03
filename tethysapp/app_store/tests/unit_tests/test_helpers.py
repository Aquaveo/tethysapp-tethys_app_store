from tethysapp.app_store.helpers import (parse_setup_py)


def test_parse_setup_py(test_files_dir):
    setup_py = test_files_dir / "setup.py"

    parsed_data = parse_setup_py(setup_py)

    expected_data = {
        'name': 'release_package', 'version': '0.0.1', 'description': 'example',
        'long_description': 'This is just an example for testing', 'keywords': 'example,test',
        'author': 'Tester', 'author_email': 'tester@email.com', 'url': '', 'license': 'BSD-3'
    }
    assert parsed_data == expected_data
