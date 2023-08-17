import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="manual_peak_labeler",
    version="2023.08.16",
    author="Cong Wang",
    author_email="wangimagine@gmail.com",
    description="An image labeler for X-ray diffraction images.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/carbonscott/manual-peak-labeler",
    keywords = ['X-ray', 'Labeler'],
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.6',
)
