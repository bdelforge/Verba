import os

from setuptools import setup


def readme():
    """
    Utility function to read the README file.
    Used for the long_description.  It's nice, because now 1) we have a top
    level README file and 2) it's easier to type in the README file than to put
    a raw string in below ...
    :return: String
    """
    return open(os.path.join(os.path.dirname(__file__), "README.md")).read()


def requirements():
    """
    Parse requirements.txt to array of packages to have installed, so we
    maintain dependencies in requirements.txt and make setup.py use it
    :return: list of requirements
    """
    with open(os.path.join(os.path.dirname(__file__), "requirements.txt")) as f:
        return f.read().splitlines()


setup(
    name="verba_utils",
    version="0.0.1",
    description="Verba utils",
    author="Bastien DELFORGE [w112409]",
    author_email="bastien.delforge@worldline.com",
    python_requires=">=3.10",
    long_description=readme(),
    install_requires=requirements(),
    packages=["verba_utils"],
)
