from setuptools import setup, find_packages

if __name__ == "__main__":
    setup(
        name="fbxloader",
        version="0.0.1",
        description="utility to read fbx file",
        long_description=open("README.md", encoding="utf-8").read(),
        long_description_content_type="text/markdown",
        url="https://github.com/ashawkey/fbxloader",
        author="kiui",
        author_email="ashawkey1999@gmail.com",
        packages=find_packages(),
        classifiers=[
            "Programming Language :: Python :: 3 ",
        ],
        keywords="fbx",
        install_requires=[
            "numpy",
            "scipy",
            "trimesh",
        ],
    )