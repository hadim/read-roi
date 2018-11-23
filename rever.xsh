$PROJECT = 'read-roi'

$ACTIVITIES = ['version_bump', 'tag', 'push_tag', 'pypi', 'ghrelease', 'conda_forge',]

$VERSION_BUMP_PATTERNS = [('read_roi/_version.py', '__version__\s*=.*', "__version__ = '$VERSION'"),
                          ('setup.py', 'version\s*=.*,', "version='$VERSION',")
                          ]

$PUSH_TAG_REMOTE = 'git@github.com:hadim/read-roi.git'
$GITHUB_ORG = 'hadim'
$GITHUB_REPO = 'read-roi'

$CONDA_FORGE_FEEDSTOCK = 'read-roi-feedstock'
$CONDA_FORGE_SOURCE_URL = 'https://pypi.io/packages/source/r/read-roi/read-roi-$VERSION.tar.gz'
