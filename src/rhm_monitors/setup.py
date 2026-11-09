from setuptools import find_packages, setup

setup(name='rhm_monitors', version='0.1.0', packages=find_packages(),
      data_files=[('share/ament_index/resource_index/packages', ['resource/rhm_monitors']),
                  ('share/rhm_monitors', ['package.xml']),
                  ('share/rhm_monitors/config', ['config/monitors.yaml'])],
      install_requires=['setuptools'], zip_safe=True,
      maintainer='RHM contributors', maintainer_email='maintainer@example.invalid',
      description='Lifecycle ROS diagnostic monitors', license='MIT',
      entry_points={'console_scripts': ['sensor_monitor = rhm_monitors.sensor_monitor:main']})
