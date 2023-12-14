from importlib.metadata import version as pkg_version
import os
import sys

sys.path.insert(0, os.path.abspath("../../"))


# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = "PyPlumIO"
copyright = "2023, Denis Paavilainen"
author = "Denis Paavilainen"
release = pkg_version("pyplumio")
version = ".".join(release.split(".")[:3])

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.autosummary",
    "sphinx.ext.githubpages",
    "sphinx.ext.autosectionlabel",
    "sphinx_rtd_theme",
    "sphinx_search.extension",
]
autosummary_generate = True

templates_path = ["_templates"]
exclude_patterns: list[str] = []


# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = "sphinx_rtd_theme"
html_theme_options = {
    "navigation_depth": 2,
}
