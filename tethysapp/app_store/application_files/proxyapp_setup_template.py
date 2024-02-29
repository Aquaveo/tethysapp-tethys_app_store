from setuptools import setup, find_packages

setup(
    name="$app_name",
    version="$app_version",
    packages=find_packages(),
    package_data={"": ["*.yml", "*.yaml"]},
    include_package_data=True,
    zip_safe=False,
)
