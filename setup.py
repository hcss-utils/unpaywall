import os
from setuptools import setup, find_packages


VERSION = "0.1"


def get_long_description():
    with open(
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "README.md"),
        encoding="utf8",
    ) as fp:
        return fp.read()


setup(
    name="unpaywall",
    description="Scrape DOIs fulltexts using unpaywall API",
    long_description=get_long_description(),
    long_description_content_type="text/markdown",
    url="https://github.com/hcss-utils/unpaywall",
    license="MIT",
    version=VERSION,
    packages=find_packages(exclude=["tests", "tests.*"]),
    install_requires=["httpx"],
    python_requires=">=3.6",
)
