from yaml import safe_load
import os
import logging

from ladino.common import LadinoError, languages

class Dictionary():
    def __init__(self, config):
        self.words = []
        self.all_examples = []
        self.all_words = []
        self.lists = {lst:[] for lst in config['listas'] }
        self.categories = {cat:[] for cat in config['kategorias'] }
        self.verbs = []

        self.count = {}
        self.word_mapping = {}
        self.pages = {}

def load_config(path_to_repo):
    with open(os.path.join(path_to_repo, 'config.yaml')) as fh:
        return safe_load(fh)

def check_and_collect_grammar(config, data, dictionary, filename):
    if 'grammar' not in data:
        raise LadinoError(f"The 'grammar' field is missing from file '{filename}'")

    grammar = data['grammar']

    if grammar not in config['gramatika']:
        raise LadinoError(f"Invalid grammar '{grammar}' in file '{filename}'")

    if grammar == 'verb' and 'conjugations' not in data:
        raise LadinoError(f"Grammar is 'verb', but there is NO 'conjugations' field in '{filename}'")
    if grammar != 'verb' and 'conjugations' in data:
        raise LadinoError(f"Grammar is NOT a 'verb', but there are conjugations in '{filename}'")

    if grammar in ['noun']: # 'adjective',
        for version in data['versions']:
            gender = version.get('gender')
            if gender is None:
                raise LadinoError(f"The 'gender' field is None in '{filename}' version {version}")
            if gender not in config['gender']:
                raise LadinoError(f"Invalid value '{gender}' in 'gender' field in '{filename}' version {version}")
            number = version.get('number')
            if number is None:
                raise LadinoError(f"The 'number' field is None in '{filename}' version {version}")
            if number not in config['numero']:
                raise LadinoError(f"The 'number' field is '{number}' in '{filename}' version {version}")

    if grammar == 'verb':
        dictionary.verbs.append(data)


def check_origen(config, data, filename):
    if 'origen' not in data:
        raise LadinoError(f"The 'origen' field is missing from file '{filename}'")
    origen  = data['origen']
    if origen not in config['origenes']:
        raise LadinoError(f"Invalid origen '{origen}' in file '{filename}'")

def check_and_collect_categories(config, data, filename, dictionary):
    if 'kategorias' not in data:
        return
    for cat in data['kategorias']:
        if cat not in config['kategorias']:
            raise LadinoError(f"Invalid category '{cat}' in file '{filename}'")
        dictionary.categories[cat].append(data)

def make_them_list(translations, filename):
    for language in languages:
        if language not in translations:
            continue
        translations[language] = make_it_list(translations, language, filename)

def make_it_list(translations, language, filename):
    target_words = translations[language]
    if target_words.__class__.__name__ == 'str':
        if target_words == '':
            return []
        else:
            return [target_words]
    elif target_words.__class__.__name__ == 'list':
        return target_words
    else:
        raise LadinoError(f"bad type {target_words.__class__.__name__} for {language} in {translations} in '{filename}'")

def check_and_collect_lists(config, data, dictionary):
    for lst, listed_words in config['listas'].items():
        #print(data['versions'][0]['ladino'])
        #print(listed_words)
        if 'versions' in data and 'ladino' in data['versions'][0] and data['versions'][0]['ladino'] in listed_words:
            dictionary.lists[lst].append(data)
        # TODO: include also words from the lists that don't appear in our dictionaries (without a link)
        # TODO: add these words to the list of missing words


def load_dictionary(config, path_to_dictionary):
    logging.info(f"Path to dictionary: '{path_to_dictionary}'")
    dictionary = Dictionary(config)

    files = os.listdir(path_to_dictionary)
    for filename in files:
        path = os.path.join(path_to_dictionary, filename)
        logging.info(path)
        with open(path) as fh:
            data = safe_load(fh)

        dictionary.all_words.append(data)

        check_and_collect_grammar(config, data, dictionary, filename)
        check_origen(config, data, filename)
        check_and_collect_categories(config, data, filename, dictionary)
        check_and_collect_lists(config, data, dictionary)

        if 'versions' not in data:
            raise LadinoError(f"The 'versions' field is missing from file '{filename}'")


        if 'examples' not in data:
            raise LadinoError(f"The 'examples' field is missing in '{filename}'")
        examples = data['examples']
        if examples == []:
            examples = None
        comments = data.get('comments')
        if comments == []:
            comments = None

        for version in data['versions']:
            if 'ladino' not in version:
                raise LadinoError(f"The ladino 'version' is missing from file '{filename}'")
            version['source'] = filename

            if 'translations' in version:
                make_them_list(version['translations'], filename)

            # Add examples and comments to the first version of the word.
            if examples is not None:
                version['examples'] = examples
                for example in examples:
                    if example.__class__.__name__ == 'str':
                        raise LadinoError(f"The example '{example}' is a string instead of a dictionary in '{filename}'")
                    for language in example.keys():
                        if language not in ['ladino', 'bozes'] and language not in languages:
                            raise LadinoError(f"Incorrect language '{language}' in example in '{filename}'")
                    dictionary.all_examples.append({
                        'example': example,
                        'word': version['ladino'].lower(),
                        'source':  filename,
                    })
                examples = None
            if comments is not None:
                version['comments'] = comments
                comments = None
            dictionary.words.append(version)

        conjugations = config['tiempos']
        pronouns = config['pronombres']
        if 'conjugations' in data:
            for verb_time, conjugation in data['conjugations'].items():
                if verb_time not in conjugations:
                    raise LadinoError(f"Verb conjugation time '{verb_time}' is no recogrnized in '{filename}'")
                #print(conjugation)
                for pronoun, version in conjugation.items():
                    if pronoun not in pronouns:
                        raise LadinoError(f"Incorrect pronoun '{pronoun}' in verb time '{verb_time}' in '{filename}'")
                    if 'ladino' not in version:
                        raise LadinoError(f"The field 'ladino' is missing from verb time: '{verb_time}' pronoun '{pronoun}' in file '{filename}'")
                    version['source'] = filename
                    if 'translations' in version:
                        make_them_list(version['translations'], filename)
                    dictionary.words.append(version)
    #print(dictionary.words)
    #print(dictionary.all_examples[0])
    for cat in dictionary.categories.keys():
        dictionary.categories[cat].sort(key=lambda word: (word['versions'][0]['ladino'], word['versions'][0]['translations']['english']))
    for lst in dictionary.lists.keys():
        lookup = {word:ix for ix, word in enumerate(config['listas'][lst])}
        dictionary.lists[lst].sort(key=lambda word: lookup[word['versions'][0]['ladino']])

    return dictionary

def load_examples(path_to_examples):
    extra_examples = []
    if os.path.exists(path_to_examples):
        for filename in os.listdir(path_to_examples):
            with open(os.path.join(path_to_examples, filename)) as fh:
                examples = safe_load(fh)
            #print(examples)
            for example in examples['examples']:
                extra_examples.append({
                    "example": example,
                    "source" : filename,
                })
    #print(extra_examples)
    return extra_examples


