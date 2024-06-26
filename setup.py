from setuptools import setup, find_namespace_packages
import os


def find_resource_files(directory, relative_to=None):
    paths = []
    for path, _directories, filenames in os.walk(directory):
        for filename in filenames:
            if relative_to is not None:
                paths.append(os.path.join(os.path.relpath(path, relative_to), filename))
            else:
                paths.append(os.path.join("..", path, filename))
    return paths


# -- Apps Definition -- #
app_package = "app_store"
release_package = "tethysapp-" + app_package

# -- Get Resource File -- #
resource_files = find_resource_files(
    "tethysapp/" + app_package + "/templates", "tethysapp/" + app_package
)
resource_files += find_resource_files(
    "tethysapp/" + app_package + "/public", "tethysapp/" + app_package
)
resource_files += find_resource_files(
    "tethysapp/" + app_package + "/scripts", "tethysapp/" + app_package
)
resource_files += find_resource_files(
    "tethysapp/" + app_package + "/application_files", "tethysapp/" + app_package
)


# -- Python Dependencies -- #
dependencies = [
    "gitpython",
    "toml",
    "semver",
    "pygithub",
    "pytest",
    "pytest-cov",
    "pytest-django",
    "pytest-lazy-fixtures",
    "pytest-mock",
    "pytest-asyncio",
]

setup(
    name=release_package,
    version="1.0.13",
    description="Tethys App Store",
    long_description="This application allows you to discover, install, manage and configure Tethys Applications.",
    keywords="Tethys, Warehouse, Conda",
    author="Rohit Khattar",
    author_email="rohitkhattar11@gmail.com",
    url="https://github.com/BYU-Hydroinformatics/tethysapp-tethys_app_store",
    license="BSD 3-Clause License",
    packages=find_namespace_packages(),
    package_data={"": resource_files},
    include_package_data=True,
    zip_safe=False,
    install_requires=dependencies,
)
