#!/usr/bin/env python

import os
import sys
import configparser
import subprocess

try:
	import semver
except ImportError:
	print("Install semver. pip install semver")
	sys.exit(-1)

ret = os.system("nosetests -v -s")
if ret != 0:
	print("Tests didn't pass. Exiting.")
	sys.exit(-1)

setup_cfg_path = 'setup.cfg'
main_branch = 'master'

config = configparser.ConfigParser()
config.read(setup_cfg_path)

name = config['metadata']['name']

version_file_path = os.path.join(name.replace("-", "_"), "_version.py")

if not os.path.isfile(version_file_path):
	print("\"{}\" must exit.".format(version_file_path))
	sys.exit(-1)

try:
	current_version = config['metadata']['version']
except ValueError as err:
		print(err)
		print("Current version in {} must be valid".format(setup_cfg_path))
		sys.exit(-1)

print("* Releasing new version for the project \"{}\".".format(name))
print("Current Version is {}".format(current_version))

new_version = semver.bump_patch(current_version)

print("Bump to Version ? [{}] : ".format(new_version), end="")
user_input = input()

if user_input != "":
	try:
		semver.parse(user_input)
		new_version = user_input
	except ValueError as err:
		print(err)
		sys.exit(-1)

if semver.parse_version_info(new_version) <= semver.parse_version_info(current_version):
	print("New version ({}) must be greater than the current one ({}) according to the semver rules."\
		.format(new_version, current_version))
	sys.exit(-1)

print("New version is {}".format(new_version))

print("---")

print("* Check for clean Git repository")
ret = os.system("""git update-index -q --refresh &&
git diff-files --quiet --ignore-submodules &&
git diff-index --cached --quiet --ignore-submodules HEAD""")

if ret != 0:
	print("The Git repository is dirty. Please commit your changes first.")
	sys.exit(-1)

print("* Write new version to \"{}\"".format(setup_cfg_path))
config['metadata']['version'] = new_version
with open(setup_cfg_path, 'w') as configfile:
	config.write(configfile)

print("* Write new version to \"{}\"".format(version_file_path))
with open(version_file_path, 'w') as versionfile:
	versionfile.write("__version__ = \"{}\"".format(new_version))

print("* Check if current branch is the main one")
output = subprocess.check_output("git rev-parse --symbolic-full-name HEAD", shell=True).strip().decode()
if output != "refs/heads/{}".format(main_branch):
	print("Not on '{}' branch".format(main_branch))
	sys.exit(-1)

print("* Commit new version")
os.system("git commit -am \"Release {}-{}\"".format(name, new_version))

print("* Tag new version")
os.system("git tag \"{}-{}\"".format(name, new_version))

os.system("rm -fr dist/ && python setup.py sdist bdist_wheel")

print("* Bump to next development cycle")
dev_version = semver.bump_patch(new_version) + "-dev"

print("* Write dev version to \"{}\"".format(setup_cfg_path))
config['metadata']['version'] = dev_version
with open(setup_cfg_path, 'w') as configfile:
	config.write(configfile)

print("* Write dev version to \"{}\"".format(version_file_path))
with open(version_file_path, 'w') as versionfile:
	versionfile.write("__version__ = \"{}\"".format(dev_version))

os.system("git commit -am \"Bump to next development cycle\"")
