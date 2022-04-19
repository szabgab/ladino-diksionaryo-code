#!/usr/bin/env python

import argparse
import collections
import copy
import glob
import json
import logging
import os
import re
import shutil
import sys
import datetime
from yaml import safe_load

import markdown
from jinja2 import Environment, FileSystemLoader

class LadinoError(Exception):
    pass

languages = ['english', 'french', 'hebrew', 'spanish', 'turkish', 'portuguese']
start = datetime.datetime.now().replace(microsecond=0)

def render(template_file, html_file=None, **args):
    root = os.path.dirname(os.path.abspath(__file__))
    templates_dir = os.path.join(root, "templates")
    env = Environment(loader=FileSystemLoader(templates_dir), autoescape=True)
    env.filters["yaml2html"] = lambda path: re.sub(r"\.yaml$", ".html", path)
    template = env.get_template(template_file)
    html = template.render(**args)
    if html_file is not None:
        with open(html_file, "w") as fh:
            fh.write(html)
    return html

def link_words(sentence, words):
    return re.sub(r'(\w+)', lambda match:
        f'<a href="/words/ladino/{match.group(0).lower()}.html">{match.group(0)}</a>' if match.group(0).lower() in words else match.group(0), sentence)

def add_links(data, words):
    for entry in data:
        if 'examples' in entry:
            for example in entry['examples']:
                example['ladino_html'] = link_words(example['ladino'], words)
    return data

def export_dictionary_pages(pages, html_dir):
    logging.info("Export dictionary pages")
    words_dir = os.path.join(html_dir, 'words')
    os.makedirs(words_dir, exist_ok=True)
    #for language, words in pages.items():
    #if not words:
    #    continue
    language = 'ladino'
    words = pages['ladino']
    language_dir = os.path.join(words_dir, language)
    logging.info(f"Export dictionary pages of {language} to {language_dir}")
    os.makedirs(language_dir, exist_ok=True)
    for word, data in words.items():
        enhanced_data = add_links(copy.deepcopy(data), words)
        filename = f'{word}.html'
        logging.info(f"Export to {filename}")
        html = render(
            "word.html",
            os.path.join(words_dir, language, filename),
            data=enhanced_data,
            title=f"{word}",
            word=word,
        )
        export_json(data, os.path.join(words_dir, language, f'{word}.json'))

def export_dictionary_lists(pages, html_dir):
    words_dir = os.path.join(html_dir, 'words')
    language = 'ladino'
    words = pages['ladino']
    html = render(
        "words.html",
        os.path.join(words_dir, language, 'index.html'),
        title=f"{language}",
        words=sorted(words.keys()),
    )

    html = render(
        "dictionary_languages.html",
        os.path.join(words_dir, 'index.html'),
        title=f"Languages",
        languages=sorted(languages),
    )


def export_about_html_page(count, html_dir):
    logging.info("Export about html page")
    end = datetime.datetime.now().replace(microsecond=0)
    elapsed = (end-start).total_seconds()
    html = render(
        "about.html",
        os.path.join(html_dir, "about.html"),
        title=f"Ladino dictionary - about",
        page="about",
        count=count,
        start=str(start),
        elapsed=elapsed,
        languages=languages,
    )


def export_main_html_page(html_dir):
    logging.info("Export main html page")

    html = render(
        "index.html",
        os.path.join(html_dir, "index.html"),
        title=f"Ladino dictionary",
        page="index",
    )

def export_json(all_words, filename, pretty=False):
    with open(filename, "w") as fh:
        if pretty:
            json.dump(all_words, fh, indent=4, ensure_ascii=False, sort_keys=True)
        else:
            json.dump(all_words, fh, ensure_ascii=False, sort_keys=True)


def remove_previous_content_of(html_dir):
    for thing in glob.glob(os.path.join(html_dir, '*')):
        if os.path.isdir(thing):
            shutil.rmtree(thing) # TODO remove all the old content from html_dir
        else:
            os.remove(thing)

def generate_main_page(html_dir):
    root = os.path.dirname(os.path.abspath(__file__))

    for part in ["js", "css"]:
        source_dir = os.path.join(root, part)

        part_dir = os.path.join(html_dir, part)
        os.makedirs(part_dir, exist_ok=True)

        for filename in os.listdir(source_dir):
            shutil.copy(os.path.join(source_dir, filename), os.path.join(part_dir, filename))

    export_main_html_page(html_dir)

def export_to_html(dictionary, count, pages, html_dir, pretty=False):
    logging.info("Export to HTML")
    os.makedirs(html_dir, exist_ok=True)

    remove_previous_content_of(html_dir)

    export_json(dictionary, os.path.join(html_dir, "dictionary.json"), pretty=pretty)

    generate_main_page(html_dir)

    export_dictionary_pages(pages, html_dir)
    export_dictionary_lists(pages, html_dir)
    export_json(count, os.path.join(html_dir, "count.json"), pretty=pretty)
    export_about_html_page(count, html_dir)


def _make_it_list(translations, language, filename):
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


def _make_them_list(translations, filename):
    for language in languages:
        if language not in translations:
            continue
        translations[language] = _make_it_list(translations, language, filename)

def check_categories(config, data, filename):
    if 'categories' not in data:
        return
    for cat in data['categories']:
        if cat not in config['kategorias']:
            raise LadinoError(f"Invalid category '{cat}' in file '{filename}'")

def check_origen(config, data, filename):
    if 'origen' not in data:
        raise LadinoError(f"The 'origen' field is missing from file '{filename}'")
    origen  = data['origen']
    if origen not in config['origenes']:
        raise LadinoError(f"Invalid origen '{origen}' in file '{filename}'")

def check_grammar(config, data, filename):
    if 'grammar' not in data:
        raise LadinoError(f"The 'grammar' field is missing from file '{filename}'")
    grammar = data['grammar']
    if grammar not in config['gramatika']:
        raise LadinoError(f"Invalid grammar '{grammar}' in file '{filename}'")
    return grammar


def load_dictionary(config, path_to_dictionary):
    logging.info(f"Path to dictionary: '{path_to_dictionary}'")
    #if path_to_dictionary is None:
    #    return

    files = os.listdir(path_to_dictionary)
    words = []
    all_examples = []
    for filename in files:
        path = os.path.join(path_to_dictionary, filename)
        logging.info(path)
        with open(path) as fh:
            data = safe_load(fh)

        grammar = check_grammar(config, data, filename)
        check_origen(config, data, filename)
        check_categories(config, data, filename)

        if 'versions' not in data:
            raise LadinoError(f"The 'versions' field is missing from file '{filename}'")

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
                _make_them_list(version['translations'], filename)

            # Add examples and comments to the first version of the word.
            if examples is not None:
                version['examples'] = examples
                for example in examples:
                    all_examples.append({
                        'example': example,
                        'word': version['ladino'].lower(),
                        'source':  filename,
                    })
                examples = None
            if comments is not None:
                version['comments'] = comments
                comments = None
            words.append(version)

        conjugations = ['present indicative', 'pasado simple']
        pronouns = ['yo', 'tu', 'el', 'mozotros', 'vozotros', 'eyos']
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
                        _make_them_list(version['translations'], filename)
                    words.append(version)
    #print(words)
    return words, all_examples

def _add_word(dictionary, source_language, target_language, source_word, target_words):
    if target_language not in dictionary[source_language][source_word]:
        dictionary[source_language][source_word][target_language] = []
    dictionary[source_language][source_word][target_language].extend(target_words)
    dictionary[source_language][source_word][target_language] = sorted(set(dictionary[source_language][source_word][target_language]))

def _add_ladino_word(original_word, accented_word, dictionary, pages, entry, count):
    word = original_word.lower()
    logging.info(f"Add ladino word: '{original_word}' '{word}' '{accented_word}'")
    #print(entry)
    count['dictionary']['ladino']['words'] += 1

    for example in entry.get('examples', []):
        if 'ladino' in example:
            count['dictionary']['ladino']['examples'] += 1
    source_language = 'ladino'
    if word not in dictionary[source_language]:
        dictionary[source_language][word] = {}
    for target_language, target_words in entry['translations'].items():
        _add_word(dictionary, source_language, target_language, word, target_words)
    _add_word(dictionary, source_language, 'ladino', word, [original_word])

    if word not in pages[source_language]:
        pages[source_language][word] = []
    pages[source_language][word].append(entry)
    pages[source_language][word].sort(key=lambda x: (x['ladino'], x['translations']['english'][0]))

    if accented_word:
        _add_word(dictionary, source_language, target_language='accented', source_word=word, target_words=[accented_word])

def _add_translated_words(source_language, dictionary, pages, entry, count):
    translations = entry['translations'].get(source_language)
    #print(f"{source_language}: {translations}")
    if translations is None:
        return

    for word in translations:
        word = word.lower()
        if word not in dictionary[source_language]:
            dictionary[source_language][word] = []
        dictionary[source_language][word].append(entry['ladino'])
        dictionary[source_language][word] = sorted(set(dictionary[source_language][word]))
        count['dictionary'][source_language]['words'] += 1

        if word not in pages[source_language]:
            pages[source_language][word] = []
        pages[source_language][word].append(entry)
        pages[source_language][word].sort(key=lambda x: len(json.dumps(x, sort_keys=True)))


def collect_data(dictionary_source):
    logging.info("Collect more data")
    count = {}
    dictionary = {}
    #print(dictionary_source)
    count['dictionary'] = {}
    pages = {}
    for language in ['ladino'] + languages:
        count['dictionary'][language] = {
            'words': 0,
            'examples': 0,
        }
        dictionary[language] = {}
        pages[language] = {}

    for entry in dictionary_source:
        _add_ladino_word(entry['ladino'], entry.get('accented'), dictionary, pages, entry, count)

        if 'alternative-spelling' in entry:
            for alt_entry in entry['alternative-spelling']:
                _add_ladino_word(alt_entry['ladino'], alt_entry.get('accented'), dictionary, pages, entry, count)

        for language in languages:
            _add_translated_words(language, dictionary, pages, entry, count)

    return dictionary, count, pages

def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--dictionary", help="path to directory where we find the dictionary files",
    )
    parser.add_argument(
        "--html", help="path to directory where to generate html files",
    )
    parser.add_argument(
        "--whatsapp", help="path to whatsapp files",
    )
    action = parser.add_mutually_exclusive_group(required=False)
    action.add_argument("--main", action='store_true', help="Create the main page only")
    action.add_argument("--all",  action='store_true', help="Create all the pages")

    parser.add_argument("--log", action="store_true", help="Additional logging")
    parser.add_argument("--pretty", action="store_true", help="Pretty save json files")

    args = parser.parse_args()

    if args.all and not args.dictionary:
        print("\n* If --all is provided we also need --directory\n")
        parser.print_help()
        exit(1)

    if (args.main or args.all) and not args.html:
        print("\n* If either --main or --all are provided we also need --html\n")
        parser.print_help()
        exit(1)

    return args

def load_config(path_to_repo):
    with open(os.path.join(path_to_repo, 'config.yaml')) as fh:
        return safe_load(fh)

def export_markdown_pages(config, path_to_repo, html_dir):
    for source, target in config['pajinas'].items():
        with open(os.path.join(path_to_repo, 'pajinas', source)) as fh:
            text = fh.read()

        title = 'Pajina'
        match = re.search(r'^#\s+(.*?)\s*$', text, re.MULTILINE)
        if match:
            title = match.group(1)
        content = markdown.markdown(text)

        html = render(
            "page.html",
            os.path.join(html_dir, target),
            title=title,
            page=target.replace('.html', ''),
            content=content,
        )

def export_examples(examples, words, html_dir):
    if not examples:
        return
    examples.sort(key=lambda ex: ex['example']['ladino'])
    for example in examples:
        example['example']['ladino_html'] = link_words(example['example']['ladino'], words)
    #print(examples)
    target = 'egzempios.html'
    html = render(
        "examples.html",
        os.path.join(html_dir, target),
        title='Egzempios',
        page=target.replace('.html', ''),
        examples=examples,
    )

def export_whatsapp(messages, words, html_dir):
    whatsapp_dir = os.path.join(html_dir, 'whatsapeando')
    os.makedirs(whatsapp_dir, exist_ok=True)
    messages.sort(key=lambda message: message['pub'], reverse=True)
    html = render(
        "whatsapeando_list.html",
        os.path.join(whatsapp_dir, 'index.html'),
        title='Estamos Whatsapeando',
        messages=messages,
    )
    for idx, message in enumerate(messages):
        text = link_words(message['text'], words)
        text = text.replace("\n", "<br>")
        next_idx = idx+1 if idx+1 < len(messages) else 0
        print(next_idx)
        html = render(
            "whatsapeando_page.html",
            os.path.join(whatsapp_dir, f"{message['page']}.html"),
            title=message['titulo'],
            filename=message['filename'],
            text=text,
            title_links=link_words(message['titulo'], words),
            prev_message=messages[idx-1]['page'],
            next_message=messages[next_idx]['page'],
        )

def main():
    args = get_args()
    if args.log:
        logging.basicConfig(level=logging.INFO)
    logging.info("Start generating Ladino dictionary website")

    if args.main:
        generate_main_page(args.html)

    if args.dictionary:
        path_to_repo = args.dictionary
        config = load_config(path_to_repo)

        dictionary_source, all_examples = load_dictionary(config, os.path.join(path_to_repo, 'words'))
        dictionary, count, pages = collect_data(dictionary_source)
        logging.info(count)

    if args.all:
        export_to_html(dictionary, count, pages, args.html, pretty=args.pretty)
        export_examples(all_examples, pages['ladino'], args.html)
        export_markdown_pages(config, path_to_repo, args.html)
        if args.whatsapp:
            sys.path.insert(0, args.whatsapp)
            import ladino.whatsapeando as whatsapp
            messages = whatsapp.get_messages()
            #print(messages)
            export_whatsapp(messages, pages['ladino'], args.html)

    end = datetime.datetime.now().replace(microsecond=0)
    logging.info(f"Elapsed time: {(end-start).total_seconds()} sec")


if __name__ == "__main__":
    main()
