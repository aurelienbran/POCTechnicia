from setuptools import setup, find_packages

setup(
    name="poc-technicia",
    version="1.0.0",
    packages=find_packages(),
    install_requires=[
        "fastapi",
        "uvicorn",
        "python-dotenv",
        "pydantic",
        "httpx",
        "pytest",
        "pytest-asyncio",
    ],
)
