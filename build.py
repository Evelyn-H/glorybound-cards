import os
import sys
import glob
import re
import itertools
import subprocess
import datetime
import math
from typing import List, Tuple
import strictyaml as yaml
from strictyaml import Map, MapPattern, EmptyDict, Str, Seq, Int, Bool, Any, Optional, CommaSeparated, Regex, load
import jinja2 as j2
from jinja2 import Template

from macros import macros

# ==== helpers ====

class MyDict(dict):
    def __missing__(self, key):
        return None

    def __getitem__(self, key):
        val = dict.__getitem__(self, key)
        if isinstance(val, str):
            return val.strip().strip('\n').replace('\n', '\n\n')
        return val

def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)

def flatten(l):
    return [item for sublist in l for item in sublist]



# ==== card definition schema ====

schema = Map({
    'kind': Str(),
    Optional('subname'): Str(),
    # Optional('colors'): Regex(r'[0-9a-fA-F]{6}\s*-\s*[0-9a-fA-F]{6}'),
    Optional('extras'): Str(),

    'cards': Seq(
        MapPattern(
            Str(), Map({
                Optional('cost'): Int(), 
                'text': Str(), 
                Optional('types'): Regex(r'\s*((move|starter|advanced|ascension|inspiration|ruined|permanent|item|augment|conjured|sequence|signature)\s*)*'),

                Optional('invoke name'): Str(), 
                Optional('invoke'): Str(), 
            })
        )
    ),
})



# ==== card & group objects ====

class Card(object):
    def __init__(self, d):
        name, d = d.popitem()
        d = MyDict(d)

        self._name = name
        self.cost = d['cost'] or 0
        self.text = d['text']
        self.types = [t.strip() for t in (d['types'].split(' ') or [])]
        # if '\\sequence' in self.text:
            # self.types.append('sequence')
        self.invoke_name = d['invoke name']
        self.invoke = d['invoke']

    @property
    def name(self):
        if 'signature' in self.types:
            return 'Signature: ' + self._name
        else:
            return self._name

    @property
    def type_line(self):
        def maybe_add(type):
            if type in self.types:
                return (type.title() + ' ')
            else:
                return ''

        line = ''
        line += maybe_add('conjured')
        line += maybe_add('starter')
        line += maybe_add('advanced')
        line += maybe_add('signature')

        line += maybe_add('move')
        line += maybe_add('item')
        line += maybe_add('augment')
        line += maybe_add('inspiration')

        subtypes = ''
        # subtypes += maybe_add('ruined')
        subtypes += maybe_add('ascension')
        subtypes += maybe_add('sequence')
        subtypes += maybe_add('permanent')

        if len(subtypes) > 0:
            line += f'- {subtypes}' 

        return line.strip()

    @property
    def rendered_text(self):
        # print('text:', self.text)
        return render_textbox(self.text)

    @property
    def ruined(self):
        return 'ruined' in self.types

    @property
    def conjured(self):
        return 'conjured' in self.types


class Group(object):
    def __init__(self, kind, cards, subname=None, extras=None):
        self.kind = kind
        self.subname = subname
        self.cards = cards
        self.extras = extras

    @property
    def name(self):
        if self.subname:
            return f"{self.kind}: {self.subname}"
        else:
            return self.kind

    @staticmethod
    def from_string(text):
            # eprint(text)
            config = yaml.load(text, schema)
            data = config.data
            # data = yaml.load(text)
            # print(repr(data))

            data = MyDict(data)

            kind = data['kind']
            subname = data['subname']
            # colors = tuple([c.strip() for c in data.get('colors', '000000 - 000000').split('-')])
            cards = [Card(card) for card in data['cards']]
            extras = data.get('extras', None)

            # print(*cards, sep='\n')
            return Group(kind, cards, subname, extras)

    @staticmethod
    def from_file(filename):
        with open(filename, 'r') as file:
            text = file.read()
            return Group.from_string(text)



# ==== macro expansion ====

# okay, writing a little parser combinator library based on regexes and overloading `or` and such would be really fun

def apply_macro(name: str, arguments: List[str]) -> str:
    # return f'[{name}: {arguments}]'
    func = macros.get(name)
    if not func:
        raise Exception(f"couldn't find macro: {name}")

    return str(func(*arguments))

def read_block(text: str) -> Tuple[str, str]:
    match = re.match(r'\s*\[', text)
    if not match:
        return None

    expanded, remainder = expand(text[match.end():])
    if not remainder.startswith(']'):
        raise Exception('gotta end your block with a \']\'.')

    return expanded, remainder[1:]

def expand_once(text: str) -> Tuple[str, str]:
    # macros start with a '\' followed by a name and optionally arguments between [ and ]
    pattern_macro = r'(\\(?P<macro>\w+))'

    # regular text can't contain '\' or '[' or ']'
    pattern_text = r'[^\\\[\]]*'
    
    # match as much non-macro text as possible
    padding_match = re.match(pattern_text, text)
    consumed = text[: padding_match.end()]
    remainder = text[padding_match.end() :]
    # print((consumed, remainder))

    # if we have no text left it means there's no macro in this text, so just return it unaltered
    if len(remainder) == 0:
        return (consumed, '')

    if remainder.startswith(']'):
        return consumed, remainder

    # parse the macro
    match = re.match(pattern_macro, remainder)
    if not match:
        raise Exception(f'invalid macro call, error at: {remainder}')

    macro_name = match.group('macro')
    # print(match)
    remainder = remainder[match.end() :]

    # parse a variable number of arguments
    arguments = []
    while (block := read_block(remainder)) is not None:
        contents, remainder = block
        arguments.append(contents)

    # run the macro code on the arguments
    expanded = apply_macro(macro_name, arguments)

    # finally, return the expanded text, and what's left to parse
    # print((text, consumed, expanded, remainder))
    return consumed + expanded, remainder
    

def expand(text: str) -> Tuple[str, str]:
    expanded = ''
    remainder = text
    while remainder and not remainder.startswith(']'):
        consumed, remainder = expand_once(remainder)
        expanded += consumed
        # print((expanded, remainder))

    return expanded, remainder


# ==== textbox rendering ====

# https://stackoverflow.com/a/57097762
def split_on_empty_lines(s):
    # greedily match 2 or more new-lines
    blank_line_regex = r"(?:\r?\n *){2,}"
    return re.split(blank_line_regex, s.strip())

def render_textbox(text: str) -> str:
    expanded, remainder = expand(text)
    if len(remainder) > 0:
        raise Exception(f'unexpected text: {remainder}')

    expanded = expanded.strip()
    # print('---', expanded)
    html = '<p>' + str.join('</p><p>', split_on_empty_lines(expanded)) + '</p>'
    # print(split_on_empty_lines(expanded))
    return html

# ==== card rendering ====

card_jinja_env = j2.Environment(
	autoescape = True,
	loader = j2.FileSystemLoader(os.path.abspath('./templates'))
)

files = glob.glob('cards/**.yaml')
groups = [Group.from_file(f) for f in files]

def cleanup(p: str):
    return p.replace(' ', '_').replace('\'', '_').replace(':', '_')

date = datetime.date.today().strftime('%m/%d/%y')

def render_and_save_html(template_name, out_path, filename, **template_vars):
    template = card_jinja_env.get_template(template_name)
    try:
        out = template.render(**template_vars)
    except Exception as e:
        raise Exception(f'error while rendering [{filename}]: {e}')

    dir = "./" + cleanup(out_path) + '/'
    os.makedirs(dir, exist_ok=True) 
    with open(dir + cleanup(filename), 'w') as file:
        file.write(out)



import asyncio
import queue


q = queue.Queue()
for i in range(24):
    q.put(i)

# https://www.delftstack.com/howto/python/parallel-for-loops-python/#use-the-asyncio-module-to-parallelize-the-for-loop-in-python
tasks = []
def background(f):
    def wrapped(*args, **kwargs):
        task = asyncio.get_event_loop().run_in_executor(None, f, *args, **kwargs)
        tasks.append(task)
        return task
    return wrapped

@background
def render_image(html_file, out_file, resolution_x, resolution_y):
    # subprocess.run(f"firefox --no-remote -P glorybound --screenshot '{out_file}' --window-size={resolution_x},{resolution_y} file://'{html_file}'", shell=True)

    # the shenanigans with the profile folders here is to ensure we can run things in parallel
    # since firefox doesn't let you run multiple instances of the same profile
    # then the queue stuff is so we can limit the max number of profiles / instances so we don't blow up my computer
    profile_num = q.get()
    profile_path = f'./.profiles/prof{profile_num}'
    os.makedirs(profile_path, exist_ok=True) 
    subprocess.run(f"firefox --no-remote --profile {profile_path} --screenshot '{out_file}' --window-size={resolution_x},{resolution_y} file://'{html_file}'", shell=True)
    q.put(profile_num)

@background
def make_pdf(group):
    os.makedirs('./rendered/pdfs/', exist_ok=True) 
    subprocess.run(f"convert ./rendered/{cleanup(group.name)}/*.png ./rendered/pdfs/{cleanup(group.name)}.pdf", shell=True)

@background
def add_bleed(group, card):
    os.makedirs(f'./rendered/print/{cleanup(group.name)}/', exist_ok=True) 
    subprocess.run(f"convert ./rendered/{cleanup(group.name)}/{cleanup(card.name)}.png -resize 50% -gravity center -extent 825x1125 ./icons/bleed-overlay.png -composite ./rendered/print/{cleanup(group.name)}/{cleanup(card.name)}.png", shell=True)


# ==== main ====

if __name__ == '__main__':

    errors = []
    # render individual cards
    for group in groups:
        for card in group.cards:
            try:
                render_and_save_html(
                    'card.html', 'build/cards', f"{card.name}.html", 
                    card=card, group=group, date=date
                )
            except Exception as e:
                errors.append(e)
    
    if errors:
        print(*errors, sep='\n')
        exit()

    # render the whole groups
    for group in groups:
        render_and_save_html(
            'group.html', 'build/groups', f"{group.name}.html", 
            group=group, date=date
        )

    if sys.argv.count('--render') > 0:
        dpi = 600
        width, height = 63, 88 # in mm
        resolution_x = int(math.ceil(width / 25.4 * dpi)) # 1489 @ 600dpi
        resolution_y = int(math.ceil(height / 25.4 * dpi)) # 2079 @ 600dpi

        for group in groups:
            for card in group.cards:
                card_name = cleanup(card.name)
                html_file = os.path.abspath(f'./build/cards/{card_name}.html')
                out_file = os.path.abspath(f'./rendered/{cleanup(group.name)}/{card_name}.png')
                print(out_file)
                print(html_file)
                render_image(html_file, out_file, resolution_x, resolution_y)

        
        # wait for all the images to be rendered
        asyncio.get_event_loop().run_until_complete(asyncio.gather(*tasks))

        # make images with bleed for printing
        for group in groups:
            for card in group.cards:
                add_bleed(group, card)
        asyncio.get_event_loop().run_until_complete(asyncio.gather(*tasks))

        # make pdfs per group
        for group in groups:
            make_pdf(group)
        asyncio.get_event_loop().run_until_complete(asyncio.gather(*tasks))
