"""setup.py"""

from setuptools import setup

with open("README.md", encoding="utf-8") as f:
    README = f.read()

setup(
    author="Beau Barker",
    author_email="beau@explodinglabs.com",
    classifiers=[
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
    ],
    description="Process JSON-RPC requests",
    extras_require={
        "examples": [
            "aiohttp",
            "aiozmq",
            "flask",
            "flask-socketio",
            "gmqtt",
            "pyzmq",
            "tornado",
            "websockets",
            "werkzeug",
        ],
        "test": [
            "pytest",
            "pytest-cov",
            "tox",
        ],
    },
    include_package_data=True,
    install_requires=["jsonschema<5", "oslash<1"],
    license="MIT",
    long_description=README,
    long_description_content_type="text/markdown",
    name="jsonrpcserver",
    packages=["jsonrpcserver"],
    url="https://github.com/explodinglabs/jsonrpcserver",
    version="5.0.9",
    # Be PEP 561 compliant
    # https://mypy.readthedocs.io/en/stable/installed_packages.html#making-pep-561-compatible-packages
    zip_safe=False,
)
