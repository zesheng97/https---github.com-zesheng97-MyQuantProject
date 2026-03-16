"""
Personal Quant Lab - 个人量化实验室
A Python-based mid-to-low frequency quantitative backtesting platform
"""

from setuptools import setup, find_packages
from pathlib import Path

# Read the contents of README file
this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text(encoding="utf-8")

setup(
    name="personal-quant-lab",
    version="2026.0.0",
    author="Quant Developer",
    author_email="your@email.com",
    description="A Python-based mid-to-low frequency quantitative backtesting platform with user-friendly GUI",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/personal-quant-lab",
    project_urls={
        "Bug Tracker": "https://github.com/yourusername/personal-quant-lab/issues",
        "Documentation": "https://github.com/yourusername/personal-quant-lab#readme",
        "Source Code": "https://github.com/yourusername/personal-quant-lab",
    },
    packages=find_packages(
        exclude=[
            "tests",
            "docs",
            "examples",
            ".github",
            "*.tests",
            "*.tests.*",
            "tests.*",
        ]
    ),
    classifiers=[
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Development Status :: 4 - Beta",
        "Intended Audience :: Financial and Insurance Industry",
        "Intended Audience :: Developers",
        "Topic :: Office/Business :: Financial :: Investment",
        "Topic :: Scientific/Engineering :: Information Analysis",
    ],
    python_requires=">=3.10",
    install_requires=[
        "pandas>=1.5.0",
        "numpy>=1.23.0",
        "yfinance>=0.2.0",
        "plotly>=5.0.0",
        "streamlit>=1.28.0",
        "dataclasses-json>=0.5.7",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0",
            "pytest-cov>=4.0",
            "black>=22.0",
            "flake8>=4.0",
            "mypy>=0.9",
        ],
        "docs": [
            "sphinx>=4.0",
            "sphinx-rtd-theme>=1.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "pql=run_gui:main",
        ],
    },
    include_package_data=True,
    zip_safe=False,
    keywords=[
        "quantitative trading",
        "backtesting",
        "fintech",
        "quant",
        "trading strategy",
        "technical analysis",
    ],
    license="MIT",
)
