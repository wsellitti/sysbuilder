A simple script to practice my python while I automate image building for my
homelab.


# Development

## Features

- [x] Read from a config file
- [x] Create virtual storage file
- [x] Activate virtual storage file as virtual disk
- [ ] Install partitions to virtual disk
- [ ] Install filesystems to partitions
- [ ] Install os to filesystem
    - [ ] customizable with packages
    - [ ] customizable with extra files

## To Dos

- [ ] Split "shell commands" into their own module
- [ ] Split "shell commands" into their own classes


# Testing

  - sample_config_correct.json: A sample configuration complete with all
    defaults.
  - sample_config_good.json: A valid configuration.
  - sample_config_bad_*.json: Bad configurations, names must start with
    "sample_config_bad_" and should be brief but describe what's bad in the
    configuration. A function should be appended to BadCfgTests for all
    configurations.
