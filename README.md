A simple script to practice my python while I automate image building for my
homelab.

# Development

## Features

  - [x] Read from a config file
  - [x] Create virtual storage file
  - [x] Activate virtual storage file as virtual disk
  - [x] Install partitions to virtual disk
  - [x] Install filesystems to partitions
  - [ ] Install os to filesystem
      - [ ] customizable with packages
      - [ ] customizable with extra files

## To Dos

  - [x] Split "shell commands" into their own module
  - [x] Split "shell commands" into their own classes

## Bug Fix

  - [x] Running `sync` on a BlockDevice object representing a partition (as a
    child of a BlockDevice object representing a disk device) does not update
    the list of children.
    Added a random sleep to stop what appears to be a race condition?


# Testing

  - sample_config_correct.json: A sample configuration complete with all
    defaults.
  - sample_config_good.json: A valid configuration.
  - sample_config_bad_*.json: Bad configurations, names must start with
    "sample_config_bad_" and should be brief but describe what's bad in the
    configuration. A function should be appended to BadCfgTests for all
    configurations.

# Issues

## VDI fails to unmount after being built

Unable to unmount filesystem after pacstrap. Pacstrap is called with `-K` to
use a clean keyring for the archlinux repositories, rather than the hosts
existing keyring; there seems to be a bug with this that prevents the spawned
gpgagent from being killed. The archived
[link](https://web.archive.org/web/20230719061359/https://github.com/archlinux/arch-install-scripts/issues/56)
(the original issue has been removed) indicates a line should be updated in
the pacstrap script (line #479):

```
diff --git a/pacstrap.in b/pacstrap.in
index 9466aa8..078909e 100644
--- a/pacstrap.in
+++ b/pacstrap.in
@@ -63,7 +63,7 @@ pacstrap() {
 
   if [[ ! -d $newroot/etc/pacman.d/gnupg ]]; then
     if (( initkeyring )); then
-      pacman-key --gpgdir "$newroot"/etc/pacman.d/gnupg --init
+      $pid_unshare pacman-key --gpgdir "$newroot"/etc/pacman.d/gnupg --init
     elif (( copykeyring )) && [[ -d /etc/pacman.d/gnupg ]]; then
       # if there's a keyring on the host, copy it into the new root
       cp -a --no-preserve=ownership /etc/pacman.d/gnupg "$newroot/etc/pacman.d/"
```

Updating the pacstrap script with the above does seem to resolve the issue.
This change will need to be maintained until it is merged upstream.
