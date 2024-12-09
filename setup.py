from setuptools import setup, find_packages

setup(
    name="ts1500_probe",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "PyQt6",
        "numpy",
        "pandas",
        "ntplib",
        "Pillow",
        "matplotlib",
    ],
    python_requires=">=3.6",
) 