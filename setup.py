from setuptools import setup, find_packages

setup(
    name="idealitycli",
    version="1.0.0",
    description="Local CLI tool for scraping, storing, summarizing, and searching ideas.",
    python_requires=">=3.10",
    packages=find_packages(),
    py_modules=["main"],  # expose root main.py as an importable module
    install_requires=[
        "requests>=2.31.0",
        "beautifulsoup4>=4.12.0",
        "lxml>=5.0.0",
    ],
    entry_points={
        "console_scripts": [
            "ideality=main:main",
        ],
    },
)
