from setuptools import setup, find_packages

setup(
    name="f1-ers-simulator",
    version="1.0.0",
    packages=find_packages(),
    py_modules=["app", "cli"],
    install_requires=[
        "numpy>=1.20.0",
    ],
    entry_points={
        "console_scripts": [
            "f1-ers=cli:main",
        ],
    },
)
