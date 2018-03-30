from .gitinfo import __gitVersion__, __gitPath__

def getgitinfo():
    """gitignored file that contains specific AWSM version and path

    Input:
        - none
    Output:
        - path to base AWSM directory
        - git version from 'git describe'
    """
    # return git describe if in git tracked SMRF
    if len(__gitVersion__) > 1:
        return __gitVersion__

    # return overarching version if not in git tracked SMRF
    else:
        version = 'v'+__version__
        return version
