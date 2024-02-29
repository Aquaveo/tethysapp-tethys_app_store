from setuptools import setup, find_namespace_packages
from setup_helper import find_resource_files
from tethys_apps.base.app_base import TethysAppBase

# -- Apps Definition -- #
TethysAppBase.package_namespace = "tethysapp"
app_package = "test_app"
release_package = "tethysapp-" + app_package

# -- Python Dependencies -- #
dependencies = []

# -- Get Resource File -- #
resource_files = find_resource_files(app_package, TethysAppBase.package_namespace)
resource_files += find_resource_files(app_package, TethysAppBase.package_namespace)


setup(
    False,
    name=release_package,
    version="0.0.1",
    description="example",
    long_description="This is just an example for testing",
    keywords="example,test",
    author="Tester",
    author_email="tester@email.com",
    url="",
    license="BSD-3",
    packages=find_namespace_packages(),
    package_data={"": resource_files},
    include_package_data=True,
    zip_safe=False,
    install_requires=dependencies,
)
