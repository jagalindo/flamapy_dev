from setuptools import setup, find_packages

def parse_requirements(filename):
    """Parse a requirements file into a list of requirements."""
    with open(filename, 'r') as f:
        return [line.strip() for line in f if line.strip() and not line.startswith('#')]

setup(
    name='flamapy-dev',
    version='0.1',
    description='CLI tool for managing Git repositories and Python packages for the flamapy distribution',
    author='José A. Galindo',
    author_email='jagalindo@us.es',
    packages=find_packages(),  # Ensure this matches your package layout
    install_requires=parse_requirements('requirements.txt'),
    entry_points={
        'console_scripts': [
            'flamapy-dev = flamapy_dev:cli',
        ],
    },
    python_requires='>=3.6',
    py_modules=['flamapy_dev'],  # Treat flamapy_dev.py as a standalone script

)
