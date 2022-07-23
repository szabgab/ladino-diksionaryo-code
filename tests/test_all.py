from ladino.generate import main
import sys
import os
from conftest import repo_path


def test_all(tmpdir):
    print(tmpdir)
    sys.argv = [sys.argv[0], '--all', '--html',  str(tmpdir), '--dictionary', repo_path()]
    main()
    os.environ["LADINO_DIR"] = str(tmpdir)
    assert os.system("node tests/test_verbs.js") == 0
