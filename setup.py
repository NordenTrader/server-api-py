from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="ion-server-api-py",
    version="1.0.0",
    author="IonTrader",
    author_email="support@iontrader.com",
    description="Ultra-low latency Python TCP client for IonTrader platform",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/iontrader/server-api-py",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "Intended Audience :: Financial and Insurance Industry",
        "Topic :: Office/Business :: Financial",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
    python_requires=">=3.8",
    install_requires=[
        # No external dependencies - uses only Python stdlib
    ],
    keywords="iontrader ion trading forex tcp api realtime websocket market-data",
    project_urls={
        "Bug Reports": "https://github.com/iontrader/server-api-py/issues",
        "Documentation": "https://iontrader.com/tcp",
        "Source": "https://github.com/iontrader/server-api-py",
    },
)