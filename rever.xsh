$PROJECT = 'read-roi'

$ACTIVITIES = ['version_bump', 'tag', 'push_tag', 'pypi', 'conda_forge', 'ghrelease']

$VERSION_BUMP_PATTERNS = [('read_roi/_version.py', '__version__\s*=.*', "__version__ = '$VERSION'"),
                          ('setup.py', 'version\s*=.*,', "version='$VERSION',")
                          ]

$PUSH_TAG_REMOTE = 'git@github.com:hadim/read-roi.git'
$GITHUB_ORG = 'hadim'
$GITHUB_REPO = 'read-roi'

$CONDA_FORGE_FEEDSTOCK = 'read-roi-feedstock'
