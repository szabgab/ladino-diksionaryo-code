import sys
import json
import os
import shutil
import pytest
import glob

from ladino.generate import load_dictionary, LadinoError, load_config, main


real_repo_path = 'ladino-diksionaryo-data'
data_path  = os.path.join(real_repo_path, 'words')
root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
examples_path  = os.path.join(root, 'tests', 'files', 'good')

# Explanation why each word is included in the tests:
# andjinara: our first test word. noun. for now it does not have a plural.
# komer: verb
# komo: has several meanings
# biblia: word is capitalized
# klaro: has comments; has examples

def test_no_params():
    sys.argv = [sys.argv[0]]
    main()

@pytest.mark.parametrize("name", ['andjinara', 'komer', 'komo', 'biblia', 'klaro', 'all', 'minimal', 'capital_letters'])
def test_one_file(tmpdir, request, name):
    print(tmpdir)
    path_to_words = os.path.join(tmpdir, 'words')
    print(path_to_words)
    os.makedirs(path_to_words, exist_ok=True)

    shutil.copy(os.path.join('tests', 'config.yaml'), os.path.join(tmpdir, f'config.yaml'))
    example = os.path.join(examples_path, f"{name}.yaml")
    words = ['andjinara', 'komer', 'komo']
    if name == 'all':
        for word in words:
            shutil.copy(os.path.join(data_path, f'{word}.yaml'), os.path.join(tmpdir, 'words', f'{word}.yaml'))
    elif os.path.exists(example):
        shutil.copy(example, os.path.join(tmpdir, 'words', f'{name}.yaml'))
    else:
        shutil.copy(os.path.join(data_path, f'{name}.yaml'), os.path.join(tmpdir, 'words', f'{name}.yaml'))

    # export in case we would like to update the files in the tests/files/ directory
    save = request.config.getoption("--save")
    if save:
        html_dir = os.path.join(root, 'tests', 'files', name)
        os.makedirs(html_dir, exist_ok=True)
    else:
        html_dir = os.path.join(tmpdir, 'html')
    os.makedirs(html_dir, exist_ok=True)

    sys.argv = [sys.argv[0], '--all', '--html',  html_dir, '--dictionary', str(tmpdir), '--pretty']
    main()
    os.unlink(os.path.join(html_dir, 'about.html'))
    os.unlink(os.path.join(html_dir, 'lists.html'))
    os.unlink(os.path.join(html_dir, 'dictionaries.html'))
    os.unlink(os.path.join(html_dir, 'index.html'))
    for filepath in glob.glob(f'{html_dir}/*-*.html'):
        os.unlink(filepath)
    shutil.rmtree(os.path.join(html_dir, 'css'))
    shutil.rmtree(os.path.join(html_dir, 'js'))


    if not save:
        cmd = f"diff -r {os.path.join(root, 'tests', 'files', name)} {os.path.join(tmpdir, 'html')}"
        print(cmd)
        assert os.system(cmd) == 0

@pytest.mark.parametrize("name,expected", [
    ('no_grammar', "The 'grammar' field is missing from file 'no_grammar.yaml'"),
    ('bad_grammar', "Invalid grammar 'Strange' in file 'bad_grammar.yaml'"),
    ('no_origen', "The 'origen' field is missing from file 'no_origen.yaml'"),
    ('bad_origen', "Invalid origen 'Strange' in file 'bad_origen.yaml'"),
    ('no_versions', "The 'versions' field is missing from file 'no_versions.yaml'"),
    ('noun_no_gender', "The 'gender' field is None in 'noun_no_gender.yaml' version {'ladino': 'klaro'}"),
    ('noun_bad_gender', "Invalid value 'droid' in 'gender' field in 'noun_bad_gender.yaml' version {'ladino': 'klaro', 'gender': 'droid'}"),
    ('noun_no_number', "The 'number' field is None in 'noun_no_number.yaml' version {'ladino': 'klaro', 'gender': 'masculine'}"),
    ('noun_bad_number', "The 'number' field is 'countless' in 'noun_bad_number.yaml' version {'ladino': 'klaro', 'gender': 'masculine', 'number': 'countless'}"),
    ('verb_no_conjugation', "Grammar is 'verb', but there is NO 'conjugations' field in 'verb_no_conjugation.yaml'"),
    ('non_verb_with_conjugation', "Grammar is NOT a 'verb', but there are conjugations in 'non_verb_with_conjugation.yaml'"),
    ('no_examples', "The 'examples' field is missing in 'no_examples.yaml'"),
    ('version_without_ladino', "The ladino 'version' is missing from file 'version_without_ladino.yaml'"),
    ('verb_wrong_conjugation_time', "Verb conjugation time 'other' is no recogrnized in 'verb_wrong_conjugation_time.yaml'"),
    ('verb_wrong_pronoun', "Incorrect pronoun 'you' in verb time 'present indicative' in 'verb_wrong_pronoun.yaml'"),
    ('verb_conjugation_missing_ladino', "The field 'ladino' is missing from verb time: 'present indicative' pronoun 'yo' in file 'verb_conjugation_missing_ladino.yaml'"),
])
def test_bad(tmpdir, name, expected):
    shutil.copy(os.path.join(root, 'tests', 'files', 'bad', f'{name}.yaml'), os.path.join(tmpdir, f'{name}.yaml'))
    with pytest.raises(Exception) as err:
        dictionary_source, all_examples = load_dictionary(load_config(real_repo_path), tmpdir)
    assert err.type == LadinoError
    assert str(err.value) == expected


