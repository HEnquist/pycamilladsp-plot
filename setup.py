import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="camilladsp_plot",
    version="0.4.4",
    author="Henrik Enquist",
    author_email="henrik.enquist@gmail.com",
    description="A library for plotting configs and filters for CamillaDSP",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/HEnquist/pycamilladsp-plot",
    packages=setuptools.find_packages(),
    python_requires=">=3",
    install_requires=["PyYAML"],
    entry_points = {
        'console_scripts': ['plotcamillaconf=camilladsp_plot.plotcamillaconf:main'],
    }

)
