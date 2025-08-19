from setuptools import setup, find_packages

setup(
    name='x22_fleet',
    version='0.1.0',
    description='X22 Management Utility Library and testing',
    author='Benjamin Habegger',
    author_email='benjamin.habegger@axiamo.com',
    url='https://gitlab.com/AxiamoGitlab/x22_testing',  # Replace with your repo link
    packages=find_packages(),  # Automatically find and include all packages
    install_requires=[
        'PySide6', 
        'paho-mqtt',
        'pandas',
        'crcmod',
        'paramiko',
        'grpcio',
        'grpcio-tools',
        'dash'
    ],
    include_package_data=True,
    entry_points={
        'console_scripts': [
            'x22_commander=x22_fleet.CommanderGui.CommanderGui:main', 
            'x22_status=x22_fleet.Library.StatusListener.StatusListener:main', 
            'x22_distributor=x22_fleet.Library.Distributor:main',             
            'x22_aws_transfer=x22_fleet.Library.AwsTransfer:main',             
            'power_relais=x22_fleet.Testing.PowerRelais:main'
        ],
    },
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'Programming Language :: Python :: 3',
        'License :: To be defined',  # Adjust license accordingly
    ],
    python_requires='>=3.7',  
)
