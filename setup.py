from setuptools import setup, find_packages

with open("README.md") as f:
    long_description = f.read()

setup(
    name="channel_app",
    version="0.0.135",
    packages=find_packages(),
    url="https://github.com/akinon/channel_app",
    description="Channel app for Sales Channels",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="akinonteam",
    python_requires=">=3.5",
    # We should pin the below to work with all the way from py27 to upto py39
    install_requires=["requests"],
    classifiers=[
        "Development Status :: 5 - Production/Stable",
    ],
)
