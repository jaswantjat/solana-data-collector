from setuptools import setup, find_packages

setup(
    name="solana_data_collector",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "aiohttp",
        "pytest",
        "pytest-asyncio",
        "pytest-mock"
    ]
)
