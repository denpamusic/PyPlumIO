import setuptools

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

pkg_vars = {}
exec(open("pyplumio/version.py").read(), pkg_vars)

setuptools.setup(
    name="PyPlumIO",
    version=pkg_vars["__version__"],
    author="Denis Paavilainen",
    author_email="denpa@denpa.pro",
    description="PyPlumIO is a native ecoNET library for Plum ecoMAX controllers.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/denpamusic/PyPlumIO",
    project_urls={
        "Bug Tracker": "https://github.com/denpamusic/PyPlumIO/issues",
    },
    classifiers=[
        "Development Status :: 2 - Pre-Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Topic :: Software Development :: Libraries",
    ],
    packages=setuptools.find_packages(exclude=["tests", "tests.*"]),
    python_requires=">=3.8",
)
