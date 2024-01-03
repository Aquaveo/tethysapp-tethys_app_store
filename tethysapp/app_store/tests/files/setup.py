from setuptools import setup, find_namespace_packages
from setup_helper import find_all_resource_files

# -- Apps Definition -- #
namespace = 'tethysapp'
app_package = 'test_app'
release_package = 'tethysapp-' + app_package

# -- Python Dependencies -- #
dependencies = []

# -- Get Resource File -- #
resource_files = find_all_resource_files(app_package, namespace)


setup(
    False,
    name=release_package,
    version='0.0.1',
    description='example',
    long_description='This is just an example for testing',
    keywords='example,test',
    author='Tester',
    author_email='tester@email.com',
    url='',
    license='BSD-3',
    packages=find_namespace_packages(),
    package_data={'': resource_files},
    include_package_data=True,
    zip_safe=False,
    install_requires=dependencies,
)
